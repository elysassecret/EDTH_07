import { expect, test, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";

// Button census (release-gate P0). Visits every screen state of the console against the real
// server, lists every control, and fails when one:
// - has no accessible name (keyboard and screen-reader users could not find it),
// - is not in tests/census.json (a control nobody has looked at: add it there deliberately),
// - throws a page error or console error when clicked (the Help crash would have failed here).
// Destructive confirms (restart, reset, record, authorize) are listed but not clicked.
// CENSUS_WRITE=1 rewrites tests/census.json from what is on screen (review the diff!).

const MAP = new URL("./census.json", import.meta.url);
const SKIP_CLICK = /^(Restart|Reset simulation|Record escalation|Authorize|Approve|Decline|Stop|Confirm|Undo|Copy text|Download|Tamper|Escalate|Battery low|Switch off|Switch back on|Cut link|Restore link|Place synthetic|Undo all|Review simulation reset|Evidence and incident reports|Since you last looked)/;
// names that change from run to run (ship ids, boat modes, counts, times) are folded
const norm = (s: string) =>
  (/· last seen/.test(s) ? "contact card · last seen" : s)
    .replace(/\b[0-9a-f]{10,}\b/gi, "ID")
    .replace(/· (PATROL|SENTINEL|KEEP IN VIEW|RTB|OFF|RETURNING|UNAVAILABLE|SHADOWING)\b/g, "· MODE")
    .replace(/\d+([.:]\d+)*/g, "#")
    .replace(/\s+/g, " ")
    .trim();

async function controls(page: Page) {
  return page.evaluate(() => {
    const sel = 'button, a[href], input, select, textarea, [role="button"], [role="switch"], [role="slider"], [role="tab"], [role="combobox"], [role="separator"][tabindex]';
    const out: { role: string; name: string; visible: boolean }[] = [];
    for (const el of Array.from(document.querySelectorAll<HTMLElement>(sel))) {
      const r = el.getBoundingClientRect();
      const visible = r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== "hidden";
      if (!visible) continue;
      const labelled = el.getAttribute("aria-labelledby");
      const name =
        el.getAttribute("aria-label") ??
        (labelled ? document.getElementById(labelled)?.textContent : null) ??
        (el.id ? document.querySelector(`label[for="${el.id}"]`)?.textContent : null) ??
        el.closest("label")?.textContent ??
        el.getAttribute("title") ??
        el.textContent ??
        "";
      out.push({ role: el.getAttribute("role") ?? el.tagName.toLowerCase(), name: name.trim(), visible });
    }
    return out;
  });
}

test("every control has a name, is known, and can be clicked without an error", async ({ page }) => {
  test.setTimeout(240_000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error" && !/WebSocket|ERR_CONNECTION|favicon/.test(m.text())) errors.push(`console: ${m.text()}`);
  });
  const seen = new Map<string, string>(); // "role|name" -> state
  const unnamed: string[] = [];
  const record = async (state: string) => {
    for (const c of await controls(page)) {
      if (!c.name) unnamed.push(`${state}: <${c.role}> without a name`);
      seen.set(`${c.role}|${norm(c.name)}`, state);
    }
  };
  const clickAll = async (state: string) => {
    const buttons = page.getByRole("button");
    const n = await buttons.count();
    for (let i = 0; i < n; i++) {
      const b = buttons.nth(i);
      if (!(await b.isVisible()) || !(await b.isEnabled())) continue;
      const name = norm((await b.getAttribute("aria-label")) ?? (await b.innerText()));
      if (!name || SKIP_CLICK.test(name)) continue;
      const before = errors.length;
      await b.click({ timeout: 1500 }).catch(() => undefined); // covered or moved: skip
      await page.waitForTimeout(150);
      if (errors.length > before) errors.push(`  ...after clicking "${name}" in ${state}`);
      await page.keyboard.press("Escape");
      await page.keyboard.press("Escape");
    }
  };

  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto("/?feed=ws://127.0.0.1:18870");
  await expect(page.getByText("FEED LIVE")).toBeVisible({ timeout: 30_000 });
  await record("live");
  for (const dialog of ["Exercise controls", "View settings", "Help", "Restart from the shore"]) {
    await page.getByRole("button", { name: dialog }).first().click();
    await page.waitForTimeout(300);
    await record(`dialog ${dialog}`);
    await page.keyboard.press("Escape");
  }
  await page.getByRole("button", { name: "Details" }).click();
  await record("details open");
  await page.getByRole("button", { name: "Hide details" }).click();
  for (const p of ["Collapse fleet panel", "Collapse attention panel", "Collapse event timeline"]) {
    await page.getByRole("button", { name: p }).click();
  }
  await record("panels collapsed");
  for (const p of ["Expand fleet panel", "Expand attention panel", /Expand event timeline/]) {
    await page.getByRole("button", { name: p }).first().click();
  }
  // replay: run a little so there is history, then jump to the start of the recording
  const run = page.getByRole("button", { name: "Run simulation" });
  if (await run.isVisible()) await run.click();
  await page.waitForTimeout(6000);
  await page.getByRole("button", { name: "Pause simulation" }).click({ timeout: 5000 }).catch(() => undefined);
  const slider = page.getByRole("slider", { name: "Replay position" });
  await slider.focus();
  await page.keyboard.press("Home");
  const goLive = page.getByRole("button", { name: "Go live" }).first();
  await expect(goLive, "replay should open on the run's first recorded state").toBeVisible({ timeout: 10_000 });
  await record("replay");
  await goLive.click();
  await clickAll("live");
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.waitForTimeout(400);
  await record("narrow");
  await page.getByRole("button", { name: "Expand attention panel" }).click();
  await page.waitForTimeout(400);
  await record("narrow drawer");
  await page.keyboard.press("Escape");

  const found = [...seen.keys()].sort();
  if (process.env.CENSUS_WRITE) writeFileSync(MAP, JSON.stringify(found, null, 1) + "\n");
  const known = new Set<string>(JSON.parse(readFileSync(MAP, "utf8")));
  const unknown = found.filter((k) => !known.has(k)).map((k) => `${k}  (in ${seen.get(k)})`);
  expect(unnamed, "controls without an accessible name").toEqual([]);
  expect(unknown, "controls not in tests/census.json: test them, then add them").toEqual([]);
  expect(errors, "errors while clicking through the console").toEqual([]);
});
