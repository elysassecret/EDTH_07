import { describe, expect, it } from "vitest";
import { vesselLifecycle } from "./lifecycle";

describe("feed-driven vessel lifecycle", () => {
  const docked = { id: 2, mode: "UNAVAILABLE" };

  it("does not invent a launch queue from an unavailable boat", () => {
    expect(vesselLifecycle(docked, { t: 0 })).toEqual({
      label: "UNAVAILABLE", detail: null,
    });
  });

  it("labels return-to-base without claiming a swap has started", () => {
    expect(vesselLifecycle({ id: 2, mode: "RETURNING" }, { t: 20 }).label)
      .toBe("Returning to Korsør");
  });

  it("uses simulation time, including fractional time, for the reported swap", () => {
    const frame = { t: 100, t_exact: 100.5, swaps: { "2": 700 } };
    const status = vesselLifecycle(docked, frame);
    expect(status).toEqual({
      label: "Battery swap",
      detail: "At Korsør · about 10:00 sim time remaining",
    });
    // Reading the same paused or stalled snapshot cannot advance its countdown.
    expect(vesselLifecycle(docked, frame)).toEqual(status);
    expect(vesselLifecycle(docked, { ...frame, t_exact: 160 }).detail)
      .toContain("09:00");
  });

  it("waits for confirmation rather than declaring a swap finished on a timer", () => {
    for (const t of [700, 800]) {
      expect(vesselLifecycle(docked, { t, swaps: { "2": 700 } }).detail)
        .toBe("At Korsør · awaiting swap confirmation");
    }
  });

  it("drops old swap metadata when a boat rejoins or a run resets", () => {
    expect(vesselLifecycle({ id: 2, mode: "PATROL" }, {
      t: 701, swaps: { "2": 700 },
    })).toEqual({ label: "PATROL", detail: null });
    expect(vesselLifecycle(docked, { t: 0, swaps: {} }).label)
      .toBe("UNAVAILABLE");
    expect(vesselLifecycle({ id: 3, mode: "UNAVAILABLE" }, {
      t: 100, swaps: { "2": 700 },
    }).label).toBe("UNAVAILABLE");
  });

  it("ignores invalid swap deadlines", () => {
    expect(vesselLifecycle(docked, { t: 100, swaps: { "2": NaN } }).label)
      .toBe("UNAVAILABLE");
  });
});
