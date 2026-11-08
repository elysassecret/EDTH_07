import { expect, test, type Page } from "@playwright/test";

// User flows end to end against the real simulator (release-gate P0). The shared test server
// runs the demo preset (placed start, scripted tape, --no-log). Each flow restarts the run first,
// so flows do not depend on each other.

const URL = "/?feed=ws://127.0.0.1:18870";

async function fresh(page: Page) {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto(URL);
  await expect(page.getByText("FEED LIVE")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Restart from the shore" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Restart", exact: true }).click();
  await expect(page.getByRole("button", { name: "Run simulation" })).toBeVisible({ timeout: 30_000 });
  await expect.poll(() => page.locator("header time").last().innerText(), { timeout: 30_000 }).toBe("12:10:00Z");
  await expect(page.getByText(/FEED LOST/)).toHaveCount(0);
}

async function speed(page: Page, v: string) {
  const f = page.getByRole("group", { name: "Simulation speed" }).getByRole("textbox", { name: "Speed factor" });
  await f.fill(v);
  await f.press("Enter");
}

const exercise = (page: Page) => page.getByRole("dialog", { name: "Exercise controls" });
const inEffect = (page: Page) => exercise(page).getByRole("region", { name: "Exercise conditions in effect" });

test("exercises: switch off, cut a link both ways, see them in effect, undo all", async ({ page }) => {
  test.setTimeout(120_000);
  await fresh(page);
  await page.getByRole("button", { name: /Exercise controls/ }).click();
  const d = exercise(page);
  await d.getByRole("group", { name: "Exercise boat" }).getByRole("button", { name: "USV 02", exact: true }).click();
  await d.getByRole("button", { name: "Switch off", exact: true }).click();
  await d.getByRole("combobox", { name: "Link destination" }).click();
  await page.getByRole("option", { name: "USV 03", exact: true }).click();
  await d.getByRole("switch", { name: "Both directions" }).click();
  await d.getByRole("button", { name: "Cut link", exact: true }).click();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByRole("button", { name: /Exercise controls, 3 in effect/ })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Pause simulation" }).click();
  await page.getByRole("button", { name: /Exercise controls/ }).click();
  await expect(inEffect(page).getByRole("listitem")).toHaveCount(3);
  await inEffect(page).getByRole("button", { name: /Undo all 3/ }).click();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByRole("button", { name: "Exercise controls", exact: true })).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Pause simulation" }).click();
});

test("battery low: the boat goes home, gets a battery swap, and returns to work", async ({ page }) => {
  test.setTimeout(180_000);
  await fresh(page);
  await page.getByRole("button", { name: /Exercise controls/ }).click();
  const d = exercise(page);
  await d.getByRole("group", { name: "Exercise boat" }).getByRole("button", { name: "USV 04", exact: true }).click();
  await d.getByRole("button", { name: "Battery low", exact: true }).click();
  await page.keyboard.press("Escape");
  await speed(page, "999");
  await page.getByRole("button", { name: "Run simulation" }).click();
  const card = page.getByTestId("fleet-4");
  await expect(card.getByText("RTB", { exact: true })).toBeVisible({ timeout: 30_000 });
  // at 999x the 10-minute swap lasts 0.6 s on screen: check the timeline, which keeps it
  const timeline = page.getByRole("region", { name: "Event timeline" });
  await timeline.getByRole("button", { name: "Expand", exact: true }).click().catch(() => undefined);
  await expect(timeline.getByText("USV 04 battery swapped at Korsør: full")).toBeVisible({ timeout: 120_000 });
  await expect(timeline.getByText(/USV 04 docked at Korsør: battery swap started/)).toBeVisible();
  await expect(card.getByText(/^(RTB|OFF)$/)).toHaveCount(0, { timeout: 60_000 }); // back at work
  await page.getByRole("button", { name: "Pause simulation" }).click();
  await page.getByRole("button", { name: "Auto", exact: true }).click();
});

test("escalation: report a contact onward; the badge and the timeline show it", async ({ page }) => {
  test.setTimeout(120_000);
  await fresh(page);
  const card = page.getByRole("button", { name: /· last seen/ }).first();
  await expect(card).toBeVisible({ timeout: 30_000 });
  await card.click();
  await page.getByRole("button", { name: "Escalate: report onward…" }).click();
  const d = page.getByRole("dialog", { name: /^Report .* onward$/ });
  await expect(d.getByRole("textbox", { name: "Report text" })).toHaveValue(/intent not established/);
  await d.getByRole("textbox", { name: "Officer note" }).fill("gate test");
  await d.getByRole("button", { name: "Record escalation" }).click();
  await expect(d.getByRole("status")).toContainText("Recorded at");
  await d.getByRole("button", { name: "Close", exact: true }).first().click(); // Esc would also deselect
  await expect(page.getByText(/ESCALATED BY WATCH OFFICER/)).toBeVisible();
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect(page.getByRole("region", { name: "Event timeline" }).getByText(/Watch officer escalated/)).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Pause simulation" }).click();
});

test("settings and keys: display modes, overlays, boat keys, help and escape", async ({ page }) => {
  await fresh(page);
  await page.getByRole("button", { name: "View settings" }).click();
  for (const mode of ["DAY", "NIGHT", "DUSK"]) {
    await page.getByRole("combobox", { name: "Display mode" }).click();
    await page.getByRole("option", { name: mode }).click();
    expect(await page.evaluate(() => document.documentElement.dataset.display)).toBe(mode.toLowerCase());
  }
  for (const name of ["Communications overlay", "Sensor rings (model ranges)"]) {
    const sw = page.getByRole("switch", { name });
    const before = await sw.getAttribute("aria-checked");
    await sw.click();
    await expect(sw).not.toHaveAttribute("aria-checked", before ?? "");
    await sw.click();
  }
  await page.getByRole("dialog", { name: "View settings" }).getByRole("button", { name: "Close" }).click();
  await expect(page.getByRole("dialog", { name: "View settings" })).toHaveCount(0);
  // the feed is live (no FEED LOST) right after a restart: commands and keys work
  await expect(page.getByText(/FEED LOST/)).toHaveCount(0);
  await page.keyboard.press("3");
  await expect(page.getByTestId("fleet-3").getByRole("button").first()).toHaveAttribute("aria-pressed", "true");
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("fleet-3").getByRole("button").first()).toHaveAttribute("aria-pressed", "false");
  await page.keyboard.press("?");
  await expect(page.getByRole("dialog", { name: "Watch guide" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Watch guide" })).toHaveCount(0);
});

test("evidence: without a run log the console says so instead of failing", async ({ page }) => {
  await fresh(page);
  await page.getByRole("button", { name: "View settings" }).click();
  await page.getByRole("button", { name: "Evidence and incident reports" }).click();
  const d = page.getByRole("dialog", { name: /Evidence/ });
  await expect(d).toBeVisible();
  await d.getByRole("button", { name: /Tamper demo/ }).click();
  await expect(d.getByText(/run log|No run log|not available|Could not/i).first()).toBeVisible({ timeout: 15_000 });
});

test("restart brings back the first state: clock, no exercise, nothing escalated", async ({ page }) => {
  test.setTimeout(120_000);
  await fresh(page);
  const clock = page.locator("header time").last();
  const start = await clock.innerText();
  await speed(page, "240");
  await page.getByRole("button", { name: "Run simulation" }).click();
  await expect.poll(() => clock.innerText(), { timeout: 30_000 }).not.toBe(start);
  await page.getByRole("button", { name: "Restart from the shore" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Restart", exact: true }).click();
  await expect(clock).toHaveText(start, { timeout: 30_000 });
  await expect(page.getByRole("button", { name: "Exercise controls", exact: true })).toBeVisible();
  await expect(page.getByText(/ESCALATED BY WATCH OFFICER/)).toHaveCount(0);
  await page.getByRole("button", { name: "Auto", exact: true }).click();
});
