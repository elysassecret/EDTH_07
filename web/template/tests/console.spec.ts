import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
async function scenario(page: Page, name: string) {
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: new RegExp(`^${name}`) })
    .click();
  await expect(page.locator('[data-slot="dialog-content"]')).toHaveCount(0);
}
async function approve(page: Page) {
  await page.getByRole("button", { name: /Review & approve/ }).click();
  await expect(
    page.getByRole("dialog", { name: "Approve proposed action" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Authorize & send" }).click();
}
test.beforeEach(async ({ page }) => {
  await page.goto("/");
});
test("one-scan fleet, synchronized map selection and offline runtime", async ({
  page,
}) => {
  const external: string[] = [];
  page.on("request", (req) => {
    if (
      !req.url().startsWith("http://127.0.0.1:5174") &&
      !req.url().startsWith("data:")
    )
      external.push(req.url());
  });
  await page.reload();
  await expect(page.locator(".fleet-card")).toHaveCount(5);
  for (const card of await page.locator(".fleet-card").all())
    await expect(card).toBeInViewport({ ratio: 1 });
  await page
    .getByRole("button", { name: "Select USV-03", exact: true })
    .click();
  await expect(page.locator('.fleet-card[data-selected="true"]')).toContainText(
    "USV-03",
  );
  await expect(page.locator(".context-content")).toContainText(
    "USV-03 → USV-04 → Korsør",
  );
  expect(external).toEqual([]);
});
test("installed shadcn registry components power the actual controls", async ({
  page,
}) => {
  await expect(page.locator('[data-slot="button"]').first()).toBeVisible();
  await expect(page.locator('[data-slot="badge"]').first()).toBeVisible();
  await expect(
    page.locator('[data-slot="tabs-trigger"]').first(),
  ).toBeVisible();
  await expect(page.locator('[data-slot="card"]')).toHaveCount(7);
  await page.getByRole("combobox", { name: "Simulation speed" }).click();
  await page.getByRole("option", { name: "5×", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Simulation speed" }),
  ).toContainText("5×");
  await page.getByRole("button", { name: "Map layers", exact: true }).click();
  await expect(
    page.getByRole("switch", { name: "Cable infrastructure" }),
  ).toBeChecked();
  await page.getByRole("switch", { name: "Cable infrastructure" }).click();
  await expect(
    page.getByRole("switch", { name: "Cable infrastructure" }),
  ).not.toBeChecked();
});
test("all five assets fit at 1440 by 900", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const card of await page.locator(".fleet-card").all())
    await expect(card).toBeInViewport({ ratio: 1 });
  expect(
    await page
      .locator(".fleet-panel")
      .evaluate((e) => e.scrollHeight <= e.clientHeight),
  ).toBe(true);
});
test("rejection requires reviewing the actual fresh revision", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Next synthetic command response" })
    .click();
  await page
    .getByRole("option", { name: "Rejected · revision changed" })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close", exact: true })
    .click();
  await approve(page);
  await expect(
    page.getByRole("button", { name: /Review again/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Review again/ }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "04 · latest synthetic snapshot",
  );
});
test("approval is not delivery and duplicate submission is blocked", async ({
  page,
}) => {
  await approve(page);
  await expect(page.getByText("COMMAND PENDING · CMD-031")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Review & approve/ }),
  ).toHaveCount(0);
  await expect(
    page.getByText("ACCEPTED BY ASSET", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Route accepted. Observation not yet completed."),
  ).toBeVisible();
});
test("coverage gap stays open until delivered re-observation", async ({
  page,
}) => {
  await scenario(page, "Coverage gap");
  await approve(page);
  await expect(
    page.getByText("ACCEPTED BY ASSET", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".alert-item").getByText("P-04 · GAP OPEN", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Demo: deliver new observation" })
    .click();
  await expect(
    page.getByText("P-04 re-observed. Gap closed by a new observation."),
  ).toBeVisible();
  await expect(page.getByText("P-04 · GAP OPEN", { exact: true })).toHaveCount(
    0,
  );
});
test("feed loss freezes controls; recovery requires explicit reconciliation", async ({
  page,
}) => {
  await scenario(page, "Feed lost");
  await expect(
    page.getByText("FEED LOST — display frozen at 14:32:18Z"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Review & approve/ }),
  ).toBeDisabled();
  await page.getByRole("button", { name: /Simulate reconnect/ }).click();
  await expect(
    page.getByText("FEED RESTORED · RECONCILIATION REQUIRED"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Review & approve/ }),
  ).toBeDisabled();
  await page.getByRole("button", { name: /Review & reconcile/ }).click();
  await expect(
    page.getByRole("button", { name: /Review & approve/ }),
  ).toBeEnabled();
});
test("lost acknowledgment never permits a blind retry", async ({ page }) => {
  await page.getByRole("button", { name: "Scenarios", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Next synthetic command response" })
    .click();
  await page
    .getByRole("option", { name: "Unconfirmed · no acknowledgment" })
    .click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Close", exact: true })
    .click();
  await approve(page);
  await expect(
    page.getByText("DELIVERY UNCONFIRMED", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Review & approve/ }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Query asset command status" })
    .click();
  await expect(
    page.getByRole("button", { name: /Review again/ }),
  ).toBeEnabled();
});
test("delegated stop requires acknowledgment and later task termination", async ({
  page,
}) => {
  await scenario(page, "Link-cut exercise");
  await page.getByRole("button", { name: /^Stop/ }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Stop task" })
    .click();
  await expect(page.getByText("COMMAND PENDING · CMD-031")).toBeVisible();
  await expect(
    page.getByText("Stop request accepted. Task termination not yet reported."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Demo: deliver task termination" })
    .click();
  await expect(page.getByText("TASK STOPPED · ASSET REPORT")).toBeVisible();
});
test("truth annotations do not leak into shore view", async ({ page }) => {
  await page.getByLabel("TRUTH", { exact: true }).click();
  await expect(
    page.getByText("EVALUATOR / TRUTH VIEW", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("TRUTH ONLY · synthetic target")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Review & approve/ }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Return to SHORE" }).click();
  await expect(page.getByText("TRUTH ONLY · synthetic target")).toHaveCount(0);
});
test("asset stale is not a fleet-wide feed loss; acknowledgment is not resolution", async ({
  page,
}) => {
  await scenario(page, "Single-USV stale");
  await expect(page.locator('.fleet-card[data-stale="true"]')).toHaveCount(1);
  await expect(
    page.getByText("FEED LOST — display frozen at 14:32:18Z"),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Acknowledge", exact: true }).click();
  await expect(
    page.getByText("USV-04 · observation stale", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Acknowledged · active" }),
  ).toBeDisabled();
});
test("keyboard shortcuts are scoped to the explicitly focused decision", async ({
  page,
}) => {
  await page.locator("body").press("a");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.locator(".decision-card").focus();
  await page.keyboard.press("a");
  await expect(
    page.getByRole("dialog", { name: "Approve proposed action" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".decision-card")).toBeFocused();
});
test("laptop drawers keep attention accessible without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.getByRole("button", { name: /Attention · 1 decision/ }).click();
  await expect(
    page.getByRole("dialog", { name: "Operator attention" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Review & approve/ }).click();
  await expect(
    page.getByRole("dialog", { name: "Approve proposed action" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
for (const name of [
  "Normal monitoring",
  "Feed lost",
  "Camera-only contact",
  "Coverage gap",
  "Single-USV stale",
  "Link-cut exercise",
  "Evaluator / truth",
]) {
  test(`AA automated checks: ${name}`, async ({ page }) => {
    await scenario(page, name);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(result.violations).toEqual([]);
  });
}
