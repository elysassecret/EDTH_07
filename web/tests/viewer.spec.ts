import { expect, test } from "@playwright/test";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import type { SceneMsg, Snapshot } from "../src/types";

test("WebGL viewer shares real simulation data, offline assets and dashboard controls", async ({
  page,
}) => {
  const errors: string[] = [],
    external: string[] = [],
    commands: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("websocket", (socket) =>
    socket.on("framesent", ({ payload }) => commands.push(String(payload))),
  );
  await page.route("**/*", (route) => {
    if (
      route.request().url().startsWith("http://127.0.0.1:18870/") ||
      route.request().url().startsWith("data:")
    )
      return route.continue();
    external.push(route.request().url());
    return route.abort();
  });
  await page.goto("/viewer.html?feed=ws://127.0.0.1:18870/truth");
  await expect(
    page.getByRole("heading", { name: "Great Belt / Maritime 3D" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Follow USV 02", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Live mission minimap" }),
  ).toBeVisible();
  expect(
    await page
      .locator("[data-testid=maritime-webgl] canvas")
      .evaluate((canvas) => {
        const gl = (canvas as HTMLCanvasElement).getContext("webgl2");
        return gl?.getParameter(gl.VERSION);
      }),
  ).toContain("WebGL 2");
  await page.getByRole("button", { name: "Follow USV 04 on minimap" }).click();
  await expect(
    page.getByText("Following USV 04", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Toggle sunset lighting" }).click();
  await page
    .getByRole("button", { name: "Mission overview", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Great Belt, Denmark" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Reset shared simulation" }).click();
  await expect(
    page.getByRole("dialog").getByText(/main dashboard too/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Keep this run" }).click();
  expect(commands).toEqual([]);
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
});

test("a stalled truth feed is visibly frozen, never a synthetic second boat simulation", async ({
  page,
}) => {
  let frozen = false;
  await page.routeWebSocket(/\/truth$/, (socket) => {
    const server = socket.connectToServer();
    server.onMessage((message) => {
      if (!frozen) socket.send(message);
    });
    socket.onMessage((message) => server.send(message));
  });
  await page.goto("/viewer.html?feed=ws://127.0.0.1:18870/truth");
  await expect(
    page.getByRole("button", { name: "Follow USV 02", exact: true }),
  ).toBeVisible();
  frozen = true;
  await expect(
    page.getByRole("alert").filter({ hasText: "Feed lost · view frozen" }),
  ).toBeVisible({ timeout: 2000 });
  await expect(
    page.getByRole("button", { name: /shared simulation$/ }).first(),
  ).toBeDisabled();
  frozen = false;
  await expect(
    page.getByRole("alert").filter({ hasText: "Feed lost · view frozen" }),
  ).toHaveCount(0);
});

test("real launch-cycle snapshots show return, swap, rejoin and reset without a local timer", async ({ page }) => {
  // Generate evidence with the real agents and World, then replay it at controlled
  // intervals so this browser test is independent of wall-clock warp and AI timing.
  const { stdout } = await promisify(execFile)("uv", ["run", "python", "-c", `
import json
from server.bridge import SimSource

source = SimSource(launch=True)
boat = next(b for b, state in source.world.boats.items() if state.enabled)
source.step(1000)
launch = source.snapshot("truth", 0)
source.step(119000)
depart = source.snapshot("truth", 0)
assert source.command({"cmd": "inject", "kind": "battery_low", "a": boat})["ok"]
returning = swapping = rejoined = None
for _ in range(1800):
    source.step(1000)
    mode = next(b for b in source._truth(0).boats if b.id == boat).mode
    if mode == "RETURNING" and returning is None:
        returning = source.snapshot("truth", 0)
    if boat in source.world.swapping and swapping is None:
        swapping = source.snapshot("truth", 0)
    swapped = any(e["kind"] == "battery_swap" and e["boat"] == boat for e in source.world.events)
    if swapped and mode != "UNAVAILABLE":
        rejoined = source.snapshot("truth", 0)
        break
assert returning and swapping and rejoined, "real launch cycle did not complete"
print(json.dumps(dict(boat=boat, scene=source.scene_msg(), launch=launch,
                     depart=depart, returning=returning, swapping=swapping, rejoined=rejoined)))
`], { cwd: fileURLToPath(new URL("../../", import.meta.url)), timeout: 40000 });
  const cycle = JSON.parse(stdout) as {
    boat: number; scene: SceneMsg;
    launch: Snapshot; depart: Snapshot; returning: Snapshot;
    swapping: Snapshot; rejoined: Snapshot;
  };
  let current = cycle.launch;
  let stalled = false;
  let send: (() => void) | undefined;
  const commands: string[] = [];
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.routeWebSocket(/\/truth$/, (socket) => {
    socket.send(JSON.stringify(cycle.scene));
    send = () => socket.send(JSON.stringify(current));
    send();
    const timer = setInterval(() => { if (!stalled) send?.(); }, 100);
    socket.onMessage((message) => commands.push(String(message)));
    socket.onClose(() => clearInterval(timer));
  });
  await page.goto("/viewer.html?feed=ws://127.0.0.1:18870/truth");
  await expect(page.getByText("Shore launch from Korsør · boats choose their assignments"))
    .toBeVisible();
  await page.getByRole("button", {
    name: `Follow USV ${String(cycle.boat).padStart(2, "0")}`, exact: true,
  }).click();
  const state = page.getByTestId("vessel-lifecycle");
  const display = (frame: Snapshot) => { current = frame; send?.(); };
  display(cycle.depart);
  await expect(state).not.toContainText("Battery swap");
  display(cycle.returning);
  await expect(state).toContainText("Returning to Korsør");
  display(cycle.swapping);
  await expect(state).toContainText("Battery swap");
  await expect(state).toContainText("about 10:00 sim time remaining");
  // Continued delivery of a paused snapshot must not advance the swap clock.
  await page.waitForTimeout(1100);
  await expect(state).toContainText("about 10:00 sim time remaining");
  stalled = true;
  await expect(page.getByRole("alert").filter({ hasText: "Feed lost · view frozen" }))
    .toBeVisible({ timeout: 10000 });
  await expect(state).toContainText("Last received state · feed unavailable");
  await expect(state).toContainText("about 10:00 sim time remaining");
  stalled = false;
  display(cycle.rejoined);
  await expect(state).not.toContainText("Battery swap");
  await expect(state).not.toContainText("feed unavailable");
  await expect(state).toContainText(
    cycle.rejoined.boats.find((boat) => boat.id === cycle.boat)!.mode.replaceAll("_", " "),
  );
  display(cycle.launch);
  await expect(state).not.toContainText("Battery swap");
  await expect(state).toContainText(
    cycle.launch.boats.find((boat) => boat.id === cycle.boat)!.mode.replaceAll("_", " "),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Collapse fleet" }).click();
  await expect.poll(async () => {
    const header = await page.locator("header").boundingBox();
    const fleet = await page.getByRole("complementary", { name: "Fleet camera controls" }).boundingBox();
    return !!header && !!fleet && fleet.y >= header.y + header.height;
  }).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(commands).toEqual([]);
  expect(errors).toEqual([]);
});
