import { expect, test } from "@playwright/test";
import type { Snapshot } from "../src/types";

// Real server --demo, no protocol fixtures, clock skipping or truth backfill.
// Manual 60x speed keeps this regression bounded; this is not a recorded full video.
test("real demo supports reviewed keyboard approval, delivered receipt and same-boat restoration", async ({
  page,
}) => {
  test.setTimeout(120000);
  let shore: Snapshot | undefined;
  let resetAcknowledged = false;
  const sent: { cmd: string; id?: string; kind?: string; a?: number }[] = [];
  const sockets: string[] = [];
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("websocket", (socket) => {
    sockets.push(socket.url());
    socket.on("framesent", ({ payload }) =>
      sent.push(JSON.parse(String(payload))),
    );
    socket.on("framereceived", ({ payload }) => {
      const value = JSON.parse(String(payload));
      if (value.type === "ack" && value.cmd === "reset" && value.ok)
        resetAcknowledged = true;
      if (Array.isArray(value.boats) && value.view === "shore")
        shore = value as Snapshot;
    });
  });
  await page.goto("/?feed=ws://127.0.0.1:18870"); // operator screen is the default
  await expect(page.getByText("FEED LIVE", { exact: true })).toBeVisible();

  // Rehearsals share the test server: use the real reviewed reset to start this take.
  await page.getByRole("button", { name: "Exercise controls" }).click();
  await page.getByRole("button", { name: "Review simulation reset" }).click();
  await page
    .getByRole("button", { name: "Reset simulation to seed 1", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Run simulation" }),
  ).toBeVisible({ timeout: 30000 });
  // Resume may still describe the previous take while the real warm-up reset runs.
  await expect
    .poll(() => resetAcknowledged && shore?.t === 6900 && shore.speed === 0, {
      timeout: 30000,
    })
    .toBe(true);
  await page.getByRole("combobox", { name: "Simulation speed" }).click();
  await page.getByRole("option", { name: "60×", exact: true }).click();
  await page.getByRole("button", { name: "Run simulation" }).click();

  const card = page.getByRole("article", {
    name: /Decision close:contact:C-07\./,
  });
  await expect(card).toBeVisible({ timeout: 45000 });
  await page.getByRole("button", { name: "Pause simulation" }).click();
  await expect(
    page.getByRole("button", { name: "Run simulation" }),
  ).toBeVisible();
  expect(shore?.contacts.some((c) => c.track === "C-07" && !c.ais)).toBe(true);

  await card.focus();
  await card.press("a");
  await expect(
    page.getByRole("dialog", { name: "Approve proposed action" }),
  ).toBeVisible();
  expect(sent.filter((command) => command.cmd === "approve")).toHaveLength(0);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(sent.filter((command) => command.cmd === "approve")).toHaveLength(0);

  await card.focus();
  await card.press("a");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Authorize & send" })
    .click();
  await expect(
    page.getByRole("button", { name: "Undo queued answer" }),
  ).toBeVisible();
  await expect
    .poll(() => sent.filter((command) => command.cmd === "approve").length, {
      timeout: 10000,
    })
    .toBe(1);
  await expect(
    page.getByText(/Approved by operator; boat delivery not yet confirmed/),
  ).toBeVisible();
  // The paused world cannot deliver the queued radio command to the acting boat.
  expect(
    shore?.decisions.find((d) => d.id === "close:contact:C-07")?.state,
  ).toBe("approved");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect
    .poll(
      () => shore?.decisions.find((d) => d.id === "close:contact:C-07")?.state,
    )
    .toBe("delivered");
  await expect(
    page.getByText(/Boat acknowledgment delivered; execution is not implied/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Pause simulation" }).click();
  await expect(
    page.getByRole("button", { name: "Run simulation" }),
  ).toBeVisible();

  const before = shore!.boats.find((b) => b.id === 2)!;
  await page.getByRole("button", { name: "Exercise controls" }).click();
  await page.getByRole("group", { name: "Exercise boat" }).getByRole("button", { name: "USV 02", exact: true }).click();
  await page.getByRole("button", { name: "Switch off", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close", exact: true })
    .click();
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect
    .poll(() =>
      shore?.events.some((event) => event.text.includes("USV 02 switched off")),
    )
    .toBe(true);
  await page.getByRole("button", { name: "Pause simulation" }).click();
  await expect(
    page.getByRole("button", { name: "Run simulation" }),
  ).toBeVisible();

  await page.getByRole("button", { name: /Exercise controls, \d+ in effect/ }).click();
  // the switched-off boat is listed as in effect, and its Undo is the same boat_restore
  await page
    .getByRole("region", { name: "Exercise conditions in effect" })
    .getByRole("listitem")
    .filter({ hasText: "USV 02 switched off" })
    .getByRole("button", { name: "Undo", exact: true })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close", exact: true })
    .click();
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect
    .poll(() =>
      shore?.events.some((event) =>
        event.text.includes("USV 02 switched back on"),
      ),
    )
    .toBe(true);
  const restoredAt = shore!.events.find((event) =>
    event.text.includes("USV 02 switched back on"),
  )!.t;
  await expect
    .poll(
      () => shore!.boats.find((b) => b.id === 2)!.last_heard >= restoredAt,
      { timeout: 10000 },
    )
    .toBe(true);
  expect(shore!.boats.find((b) => b.id === 2)!.batt).toBeLessThanOrEqual(
    before.batt,
  );
  expect(sent.filter((command) => command.kind === "boat_restore")).toEqual([
    { cmd: "inject", kind: "boat_restore", a: 2 },
  ]);
  expect(sent.filter((command) => command.cmd === "reset")).toHaveLength(1);
  expect(sockets.every((socket) => socket.endsWith("/shore"))).toBe(true);
  expect("scorecard" in shore!).toBe(false);
  expect("eval" in shore!).toBe(false);
  expect(errors).toEqual([]);
});
