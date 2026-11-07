import { describe, expect, it } from "vitest";
import { pathLength, responseCost } from "./cost";
import type { Decision, SceneMsg, Snapshot } from "./types";

const scene = {
  type: "scene", schema_version: 1, source: "sim", t0_utc: "2026-11-03T10:15:00Z",
  segments: { "seg:H:0": [], "seg:H:1": [], "seg:G:0": [] }, stations: {}, shore: [11.13, 55.33],
  stale_after_s: 60, horizon_s: 14400, home_m: 300, revisit_target_s: 12000,
  boat_model: { speed_mps: 2, endurance_s: 25200, reserve_s: 1800 },
} as unknown as SceneMsg;
// 0.018 deg of latitude is about 2002 m
const route: [number, number][] = [[11.0, 55.4], [11.0, 55.418]];
const dec = { id: "d1", task: "contact:C-07", dec: "close", text: "", state: "pending", t: 0, boat: 3, route } as unknown as Decision;
const snap = (boat: object, seg_age: Record<string, number> = {}) => ({
  view: "shore", t: 20000, seg_age, tasks: { "contact:C-07": { v: 1, owner: 3, deputy: 0, state: 1, why: "closest" } },
  boats: [{ id: 3, lon: 11, lat: 55.4, mode: "PATROL", endurance_s: 9000, must_return_by: 30000,
    tour: ["seg:H:0", "seg:H:1"], roles: ["seg:H:0", "seg:H:1"], last_heard: 20000, ...boat }],
  contacts: [],
}) as unknown as Snapshot;

describe("response cost (roadmap items 1 + 2)", () => {
  it("measures the route", () => {
    expect(Math.round(pathLength(route))).toBe(2002);
  });
  it("estimates transit, arrival and energy from the model speed", () => {
    const c = responseCost(dec, snap({}), scene)!;
    expect(Math.round(c.transit_s!)).toBe(1001);
    expect(Math.round(c.energy_after_s!)).toBe(7999);
    expect(c.below_reserve).toBe(false);
    expect(c.after_return_by).toBe(false);
    expect(c.leaves).toBe("Cable sweep (HVDC Storebælt I)");
    expect(c.reason).toBe("closest");
  });
  it("stops a close look at the boat's verify radius", () => {
    const c = responseCost({ ...dec, dec: "close" } as Decision, snap({ verify_m: 500 }), scene)!;
    expect(Math.round(c.distance_m!)).toBe(1502);
    expect(c.stop_short_m).toBe(500);
  });
  it("flags the reserve and the return-by time", () => {
    const c = responseCost(dec, snap({ endurance_s: 2500, must_return_by: 20500 }), scene)!;
    expect(c.below_reserve).toBe(true);
    expect(c.after_return_by).toBe(true);
  });
  it("names segments that pass the target before it arrives, and ones already unconfirmed", () => {
    // H:0 age 11500 + ~1001 > 12000: passes; H:1 age 100: fine; H:1 is in tour, G:0 is not
    const c = responseCost(dec, snap({ tour: ["seg:H:0", "seg:H:1", "seg:G:0"] }, { "seg:H:0": 11500, "seg:H:1": 100 }), scene)!;
    expect(c.over_target).toEqual(["HVDC Storebælt I, part 1"]);
    expect(c.unconfirmed).toEqual(["Great Belt 1 fibre, part 1"]);
  });
  it("gives no transit estimate without a route or a model speed", () => {
    expect(responseCost({ ...dec, route: null }, snap({}), scene)!.transit_s).toBeNull();
    expect(responseCost(dec, snap({}), { ...scene, boat_model: undefined })!.transit_s).toBeNull();
    expect(responseCost({ ...dec, boat: 9 }, snap({}), scene)).toBeNull();
  });
});
