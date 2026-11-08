import { expect, test } from "@playwright/test";

// Replay works like a live video stream: drag back to watch, the simulation keeps running,
// Go live returns to now. Real demo server (playwright.config.ts webServer).
test("replay timeline: watch the past while the run goes on, then go live", async ({ page, request }) => {
  await page.goto("/?feed=ws://127.0.0.1:18870");
  await expect(page.getByText("FEED LIVE")).toBeVisible({ timeout: 30000 });
  const run = page.getByRole("button", { name: "Run simulation" });
  if (await run.isVisible()) await run.click();
  // wait until the server has recorded a few frames (every 30 sim-s)
  await expect
    .poll(async () => (await (await request.get("http://127.0.0.1:18870/api/history")).json()).frames, {
      timeout: 60000,
    })
    .toBeGreaterThan(3);
  const bar = page.getByRole("group", { name: "Replay timeline" });
  await expect(bar.getByRole("button", { name: "Watching live" })).toBeVisible();
  // jump to the start of the recording
  const slider = bar.getByRole("slider", { name: "Replay position" });
  await slider.focus();
  await page.keyboard.press("Home");
  await expect(page.getByText(/^REPLAY \d\d:\d\d:\d\dZ: what the shore knew then/)).toBeVisible();
  await expect(page.getByText("Sim time · REPLAY")).toBeVisible();
  const replayed = await page.locator("header time").last().innerText();
  // the run keeps going underneath: the timeline's live end moves on
  const liveEnd = async () => Number(await slider.getAttribute("max"));
  const before = await liveEnd();
  await expect.poll(liveEnd, { timeout: 30000 }).toBeGreaterThan(before);
  expect(await page.locator("header time").last().innerText()).toBe(replayed); // screen stays put
  // back to now
  await bar.getByRole("button", { name: "Go live" }).click();
  await expect(bar.getByRole("button", { name: "Watching live" })).toBeVisible();
  await expect(page.getByText(/^REPLAY /)).toHaveCount(0);
  await page.getByRole("button", { name: "Pause simulation" }).click();
});

test("stepless speed: 0.25x and 999x are accepted, out of range is refused", async ({ page }) => {
  await page.goto("/?feed=ws://127.0.0.1:18870");
  await expect(page.getByText("FEED LIVE")).toBeVisible({ timeout: 30000 });
  const factor = page.getByRole("group", { name: "Simulation speed" }).getByRole("textbox", { name: "Speed factor" });
  for (const v of ["0.25", "999", "37.5"]) {
    await factor.fill(v);
    await factor.press("Enter");
    await expect(page.getByText(new RegExp(`Sim time · (paused|${v.replace(".", "\\.")}×)`))).toBeVisible();
  }
  await factor.fill("5000"); // out of range: not sent, field returns to the last value
  await factor.press("Enter");
  await expect(factor).toHaveValue("37.5");
  await page.getByRole("button", { name: "Auto", exact: true }).click();
});

test("replay playback: Play plays the recording forward and stops at live", async ({ page, request }) => {
  await page.goto("/?feed=ws://127.0.0.1:18870");
  await expect(page.getByText("FEED LIVE")).toBeVisible({ timeout: 30000 });
  const run = page.getByRole("button", { name: "Run simulation" });
  if (await run.isVisible()) await run.click();
  await expect
    .poll(async () => (await (await request.get("http://127.0.0.1:18870/api/history")).json()).frames, {
      timeout: 60000,
    })
    .toBeGreaterThan(12);
  await page.getByRole("button", { name: "Pause simulation" }).click();
  const slider = page.getByRole("slider", { name: "Replay position" });
  await slider.focus();
  await page.keyboard.press("Home");
  await expect(page.getByRole("button", { name: "Play replay" })).toBeVisible();
  const t0 = await page.locator("header time").last().innerText();
  const factor = page.getByRole("group", { name: "Simulation speed" }).getByRole("textbox", { name: "Speed factor" });
  await factor.fill("200");
  await factor.press("Enter");
  await page.getByRole("button", { name: "Play replay" }).click();
  // the replayed clock moves forward on recorded frames only
  await expect.poll(() => page.locator("header time").last().innerText(), { timeout: 20000 }).not.toBe(t0);
  // the live run is paused: playback catches up and returns to live by itself
  await expect(page.getByRole("button", { name: "Watching live" })).toBeVisible({ timeout: 60000 });
  await expect(page.getByRole("button", { name: "Run simulation" })).toBeVisible();
});
