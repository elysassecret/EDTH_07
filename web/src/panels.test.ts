import { describe, expect, it } from "vitest";
import { CHART_MIN_W, CLOSE_PX, DEFAULT_LAYOUT, LIMITS, dragTo, fit, maxSize, parseLayout } from "./panels";

describe("dragTo", () => {
  const { min, max } = LIMITS.fleet;
  it("follows the drag between the limits", () => {
    expect(dragTo("fleet", 300, 5000, 280)).toEqual({ size: 300, open: true });
  });
  it("stops at the maximum", () => {
    expect(dragTo("fleet", max + 400, 5000, 280)).toEqual({ size: max, open: true });
  });
  it("stops where the chart would get too small", () => {
    expect(dragTo("fleet", 500, 300, 280)).toEqual({ size: 300, open: true });
  });
  it("holds at the minimum just below it", () => {
    expect(dragTo("fleet", min - CLOSE_PX + 1, 5000, 280)).toEqual({ size: min, open: true });
  });
  it("closes when pushed past the minimum, keeping the size it had", () => {
    expect(dragTo("fleet", min - CLOSE_PX - 1, 5000, 333)).toEqual({ size: 333, open: false });
  });
  it("never reports a size below the minimum", () => {
    expect(maxSize("attention", 10)).toBe(LIMITS.attention.min);
  });
});

describe("fit", () => {
  it("draws the stored sizes on a wide screen", () => {
    expect(fit(DEFAULT_LAYOUT, 1920, 1080)).toEqual({
      fleet: LIMITS.fleet.def, attention: LIMITS.attention.def, timeline: LIMITS.timeline.def,
    });
  });
  it("gives a closed panel's space to the chart", () => {
    const l = { ...DEFAULT_LAYOUT, fleet: { size: 300, open: false } };
    expect(fit(l, 1920, 1080).fleet).toBe(0);
  });
  it("hides side panels where the console uses drawers", () => {
    expect(fit(DEFAULT_LAYOUT, 1300, 900)).toMatchObject({ fleet: 0, attention: LIMITS.attention.def });
    expect(fit(DEFAULT_LAYOUT, 1000, 900)).toMatchObject({ fleet: 0, attention: 0 });
  });
  it("shrinks big panels so the chart keeps its minimum width", () => {
    const l = { ...DEFAULT_LAYOUT, fleet: { size: 520, open: true }, attention: { size: 720, open: true } };
    const d = fit(l, 1440, 900);
    expect(1440 - d.fleet - d.attention).toBeGreaterThanOrEqual(CHART_MIN_W);
    expect(d.fleet).toBeGreaterThanOrEqual(LIMITS.fleet.min);
  });
  it("keeps the timeline to half the window height", () => {
    const l = { ...DEFAULT_LAYOUT, timeline: { size: 480, open: true } };
    expect(fit(l, 1920, 600).timeline).toBe(300);
  });
});

describe("parseLayout", () => {
  it("falls back to defaults on bad input", () => {
    expect(parseLayout(null)).toEqual(DEFAULT_LAYOUT);
    expect(parseLayout("{oops")).toEqual(DEFAULT_LAYOUT);
    expect(parseLayout('{"fleet":{"size":"x","open":true}}')).toEqual(DEFAULT_LAYOUT);
  });
  it("keeps valid values and clamps sizes to the limits", () => {
    const l = parseLayout('{"fleet":{"size":9999,"open":false},"timeline":{"size":10,"open":true}}');
    expect(l.fleet).toEqual({ size: LIMITS.fleet.max, open: false });
    expect(l.timeline).toEqual({ size: LIMITS.timeline.min, open: true });
    expect(l.attention).toEqual(DEFAULT_LAYOUT.attention);
  });
});
