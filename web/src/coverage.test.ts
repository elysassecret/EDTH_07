import { describe, expect, it } from "vitest";
import { coverageWords, type SegAge } from "./coverage";

const T0 = "2026-11-03T10:15:00Z";
const seg = (id: string, age: number | null): SegAge => ({ id, age, band: age === null ? "none" : "recent" });

describe("coverage headline (#88)", () => {
  it("says all within target only when every segment has a visit inside the target", () => {
    expect(coverageWords([seg("seg:G:0", 100), seg("seg:H:0", 200)], 1000, 5000, T0)).toBe(
      "All 2 cable segments within the revisit target",
    );
  });
  it("names an overdue segment and when it went over target", () => {
    // age 1600 at t=5000 with target 1000: over target since t=4400 -> 10:15Z + 4400 s = 11:28Z
    expect(coverageWords([seg("seg:G:0", 1600), seg("seg:H:0", 200)], 1000, 5000, T0)).toBe(
      "1 of 2 cable segments within target · seg:G:0 overdue since 11:28Z",
    );
  });
  it("keeps a segment with no reported visit unknown, never counted as fresh", () => {
    expect(coverageWords([seg("seg:M:0", null), seg("seg:H:0", 200)], 1000, 5000, T0)).toBe(
      "1 of 2 cable segments within target · seg:M:0: no visit confirmed",
    );
  });
  it("does not invent a target", () => {
    expect(coverageWords([seg("seg:M:0", null), seg("seg:H:0", 200)], undefined, 5000, T0)).toBe(
      "1 of 2 cable segments visited · no revisit target set",
    );
  });
});
