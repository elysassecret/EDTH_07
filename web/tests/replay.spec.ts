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
