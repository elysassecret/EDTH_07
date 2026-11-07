import { describe, expect, it } from "vitest";
import { keepNonOverlapping, textBox } from "./declutter";

const at = (x: number, y: number, text = "AIS-01", p = 20) => ({ box: textBox(x, y, text, 14, [0, 0]), p });

describe("label declutter", () => {
  it("keeps labels that do not touch", () => {
    expect(keepNonOverlapping([at(0, 0), at(200, 0), at(0, 100)])).toEqual([true, true, true]);
  });
  it("drops the less important of two overlapping labels", () => {
    expect(keepNonOverlapping([at(0, 0, "AIS-01", 20), at(10, 2, "03", 100)])).toEqual([false, true]);
  });
  it("gives a tie to the earlier label, so the picture does not flicker", () => {
    expect(keepNonOverlapping([at(0, 0), at(5, 0), at(10, 0)])).toEqual([true, false, false]);
  });
  it("brings a label back when zooming in moves the two apart", () => {
    const close = keepNonOverlapping([at(0, 0), at(30, 0)]);
    const zoomed = keepNonOverlapping([at(0, 0), at(120, 0)]); // same two, twice as far on screen
    expect(close).toEqual([true, false]);
    expect(zoomed).toEqual([true, true]);
  });
  it("sizes the box from the text and the pixel offset", () => {
    expect(textBox(100, 100, "abcd", 10, [0, -20]).y).toBeLessThan(100 - 20 + 0.1);
    expect(textBox(0, 0, "abcdefgh", 10, [0, 0]).w).toBeGreaterThan(textBox(0, 0, "ab", 10, [0, 0]).w);
  });
});
