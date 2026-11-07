import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
const baseURL = process.env.TEMPLATE_URL || "http://127.0.0.1:5174";
await mkdir("previews", { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const page = await context.newPage();
const scenarios = [
  "Normal monitoring",
  "Route approval",
  "Feed lost",
  "Feed recovery",
  "Camera-only contact",
  "Coverage gap",
  "Single-USV stale",
  "Link-cut exercise",
  "Evaluator / truth",
];
try {
  for (const [index, name] of scenarios.entries()) {
    await page.goto(baseURL);
    await page.getByRole("button", { name: "Scenarios", exact: true }).click();
    await page
      .getByRole("dialog")
      .getByRole("button", { name: new RegExp(`^${name}`) })
      .click();
    await page.evaluate(() => document.fonts.ready);
    const filename = `${String(index + 1).padStart(2, "0")}-${name.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}.png`;
    await page.screenshot({ path: `previews/${filename}`, fullPage: true });
    console.log(`previews/${filename}`);
  }
  await page.goto(baseURL);
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.getByRole("button", { name: /Attention · 1 decision/ }).click();
  await page.screenshot({ path: "previews/10-laptop-attention.png" });
} finally {
  await browser.close();
}
