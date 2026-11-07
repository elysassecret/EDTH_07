import { describe, expect, it } from "vitest";
import { distWords, spreadLabels, spreads, spreadText } from "./uncertainty";
import type { SceneMsg, Snapshot } from "./types";

const scene = {
  type: "scene", schema_version: 1, source: "sim", t0_utc: "2026-11-03T10:15:00Z", segments: {},
  stations: {}, shore: [11.13, 55.33], stale_after_s: 60, horizon_s: 14400, home_m: 300,
  boat_model: { speed_mps: 2, endurance_s: 25200, reserve_s: 1800 },
} as unknown as SceneMsg;
const boat = (id: number, last_heard: number, extra = {}) => ({
  id, x: 0, y: 0, lon: 11.0, lat: 55.4, mode: "PATROL", batt: 900, endurance_s: 20000, link: "none",
  tour: [], roles: [], last_heard, ...extra,
});
const snap = (boats: unknown[], contacts: unknown[] = []) =>
  ({ view: "shore", t: 1000, boats, contacts }) as unknown as Snapshot;

describe("uncertainty circles (roadmap item 4)", () => {
  it("grows a stale boat's circle with age x model speed", () => {
    const s = spreads(snap([boat(2, 400)]), scene, false);
    expect(s).toHaveLength(1);
    expect(s[0].r_m).toBe(1200); // 600 s x 2 m/s
    expect(s[0].id).toBe("USV 02");
  });
  it("draws nothing for live, never-heard or docked boats, or when frozen", () => {
    expect(spreads(snap([boat(1, 990)]), scene, false)).toHaveLength(0);
    expect(spreads(snap([boat(1, 0, { heard: false })]), scene, false)).toHaveLength(0);
    expect(spreads(snap([boat(1, 0, { mode: "UNAVAILABLE", lon: 11.13, lat: 55.33 })]), scene, false)).toHaveLength(0);
    expect(spreads(snap([boat(2, 400)]), scene, true)).toHaveLength(0);
  });
  it("does not invent a speed when the server sends none", () => {
    const bare = { ...scene, boat_model: undefined } as SceneMsg;
    expect(spreads(snap([boat(2, 400)]), bare, false)).toHaveLength(0);
  });
  it("uses a stale contact's last reported speed and skips stopped ones", () => {
    const k = (sog: number) => ({ id: "contact:C-07", track: "C-07", lon: 11, lat: 55.4, sog, last_seen: 700 });
    expect(spreads(snap([], [k(1500)]), scene, false)[0].r_m).toBe(450); // 300 s x 1.5 m/s
    expect(spreads(snap([], [k(0)]), scene, false)).toHaveLength(0);
  });
  it("says the assumption in words", () => {
    expect(spreadText(snap([boat(2, 400)]), scene, "boat", "USV 02")).toBe(
      "1.2 km (model cruise speed 2 m/s, current not included)",
    );
    expect(distWords(654)).toBe("650 m");
  });
});

describe("uncertainty labels", () => {
  it("merges circles that sit on top of each other into one label", () => {
    const sp = spreads(snap([boat(2, 400), boat(3, 400, { lon: 11.001 }), boat(5, 400, { lat: 55.3 })]), scene, false);
    expect(spreadLabels(sp).map((l) => l.text)).toEqual([
      "USV 02, 03 could be within 1.2 km",
      "USV 05 could be within 1.2 km",
    ]);
  });
});
