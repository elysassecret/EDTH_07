import { describe, expect, it } from "vitest";
import {
  actionsFor,
  canOperate,
  coverageRows,
  decisionRevision,
  endpoint,
  linkText,
  pendingDecisions,
  reportAge,
  staleBoat,
} from "./console-model";
import type { Boat, Decision, SceneMsg, Snapshot } from "./types";

function snapshot(extra: Partial<Snapshot> = {}): Snapshot {
  return {
    view: "shore",
    t: 100,
    speed: 240,
    boats: [],
    tasks: {},
    contacts: [],
    decisions: [],
    alerts: [],
    events: [],
    links: [],
    seg_age: {},
    ...extra,
  };
}
const boat: Boat = {
  id: 4,
  mode: "PATROL",
  x: 0,
  y: 0,
  lon: 11,
  lat: 55,
  batt: 500,
  endurance_s: 12600,
  link: "peer",
  via: 5,
  roles: [],
  tour: [],
  last_heard: 90,
};
const held: Decision = {
  id: "close:contact:C-07",
  task: "contact:C-07",
  text: "Close for a look",
  dec: "close",
  state: "pending",
  t: 50,
  tier: "held",
  boat: 3,
  actions: ["approve", "decline"],
};

describe("live template selectors", () => {
  it("only allows operator actions on a fresh shore feed", () => {
    expect(canOperate("live", "shore")).toBe(true);
    for (const conn of ["lost", "connecting"])
      expect(canOperate(conn, "shore")).toBe(false);
    expect(canOperate("live", "truth")).toBe(false);
  });
  it("uses report timestamps and never converts never-heard to live", () => {
    expect(reportAge(boat, 100)).toBe(10);
    expect(reportAge({ ...boat, heard: false }, 100)).toBeNull();
    expect(staleBoat(boat, snapshot(), null, "lost")).toBe(true);
    expect(staleBoat(boat, snapshot(), null, "live")).toBe(false);
    expect(staleBoat(boat, snapshot({ t: 200 }), null, "live")).toBe(true);
  });
  it("keeps docked peers distinct from shore and never calls a peer direct", () => {
    expect(endpoint(0)).toBe("shore");
    expect(endpoint(1)).toBe("USV 01");
    expect(linkText(boat)).toBe("Via USV 05");
    expect(linkText({ ...boat, via: 0 })).toBe("Via peer");
  });
  it("derives actual pending decisions and respects backend actions", () => {
    const delegated: Decision = {
      ...held,
      id: "contact:C-07",
      tier: "delegated",
      actions: ["confirm", "stop"],
      t: 1,
    };
    expect(
      pendingDecisions(
        snapshot({
          decisions: [delegated, { ...held, state: "expired" }, held],
        }),
      ).map((d) => d.id),
    ).toEqual([held.id, delegated.id]);
    expect(actionsFor(delegated)).toEqual(["confirm", "stop"]);
    expect(pendingDecisions(null)).toEqual([]);
  });
  it("invalidates review when task ownership changes, not on a mere clock tick", () => {
    const snap = snapshot({
      tasks: { [held.task]: { v: 2, owner: 3, deputy: 2, state: 1 } },
    });
    const key = decisionRevision(held, snap);
    expect(decisionRevision(held, { ...snap, t: 101 })).toBe(key);
    expect(
      decisionRevision(held, {
        ...snap,
        tasks: { [held.task]: { v: 3, owner: 2, deputy: 3, state: 1 } },
      }),
    ).not.toBe(key);
    expect(decisionRevision({ ...held, state: "expired" }, snap)).not.toBe(key);
  });
  it("keeps missing coverage unknown and uses dynamic segment IDs", () => {
    const scene: SceneMsg = {
      type: "scene",
      schema_version: 1,
      source: "sim",
      t0_utc: "2026-11-03T10:15:00Z",
      stations: {},
      shore: [11, 55],
      stale_after_s: 60,
      horizon_s: 14400,
      segments: {
        "seg:H:2": [
          [11, 55],
          [11, 56],
        ],
        "seg:M:0": [
          [11, 55],
          [12, 55],
        ],
      },
    };
    expect(
      coverageRows(snapshot({ seg_age: { "seg:H:2": 10 } }), scene).map((r) => [
        r.id,
        r.age,
      ]),
    ).toEqual([
      ["seg:H:2", 10],
      ["seg:M:0", null],
    ]);
    expect(
      coverageRows(snapshot({ t: 0, seg_age: { "seg:H:2": 0 } }), scene)[0].age,
    ).toBeNull();
    expect(
      coverageRows(snapshot({ seg_age: { "seg:H:2": 100 } }), scene)[0].age,
    ).toBeNull();
    expect(
      coverageRows(
        snapshot({ view: "truth", seg_age: { "seg:H:2": 100 } }),
        scene,
      )[0].age,
    ).toBe(100);
  });
});
