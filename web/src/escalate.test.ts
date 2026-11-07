import { describe, expect, it } from "vitest";
import { ddm, escalationOf, reportText } from "./escalate";
import type { Contact, Snapshot } from "./types";

const k = {
  id: "contact:C-07", track: "C-07", x: 0, y: 0, lon: 10.870594, lat: 55.451893, sog: 1029, cog: 87,
  ais: false, first_seen: 7800, last_seen: 8050, seen_by: [2, 3], watcher: 3, state: 1,
  flags: { dwell: true, name: false, anchor: false, cannot_hold: false, capped: false },
} as unknown as Contact;
const snap = { t: 8076, t0_utc: "2026-11-03T10:15:00Z", escalations: [
  { id: "contact:C-07", track: "C-07", t: 8000, note: "a" },
  { id: "contact:C-07", track: "C-07", t: 8070, note: "b" },
] } as unknown as Snapshot;

describe("escalation report", () => {
  it("writes positions as degrees and decimal minutes", () => {
    expect(ddm(55.451893, "N", "S", 2)).toBe("55°27.11'N");
    expect(ddm(10.870594, "E", "W", 3)).toBe("010°52.24'E");
  });
  it("uses only delivered data and never claims intent", () => {
    const text = reportText(k, snap, "2026-11-03T10:15:00Z");
    expect(text).toContain("Contact C-07: no AIS match (camera only).");
    expect(text).toContain("course 087°, speed 2.0 kn");
    expect(text).toContain("Seen by USV 02, USV 03; USV 03 keeps it in view.");
    expect(text).toContain("intent not established");
    expect(text.toLowerCase()).not.toMatch(/threat|hostile|suspicious/);
  });
  it("finds the newest escalation of a contact", () => {
    expect(escalationOf(snap, "contact:C-07")?.note).toBe("b");
    expect(escalationOf(snap, "contact:X")).toBeNull();
  });
});
