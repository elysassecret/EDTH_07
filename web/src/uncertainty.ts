// Owner: C. Roadmap item 4, "represent uncertainty, not just positions".
// An old report is a last known place, not a position. Around each stale boat and stale
// moving contact we draw the area it could have reached since: age x speed.
// - Boats: the model cruise speed from config/boat.toml (scene.boat_model). Current is not
//   included, so the real boat may also have drifted.
// - Contacts: their last reported speed. A contact can change speed; the circle says so.
// Nothing here uses truth; every input is what the shore was told.
import type { Boat, Contact, SceneMsg, Snapshot } from "./types";
import { isDocked } from "./roles";

export interface Spread {
  kind: "boat" | "contact";
  id: string; // "USV 02" or the contact's track name
  lon: number;
  lat: number;
  r_m: number; // radius in metres
  age_s: number;
  basis: string; // the assumption, in words
}

export function spreads(snap: Snapshot, scene: SceneMsg | null, frozen: boolean): Spread[] {
  // When the feed is lost the whole screen is frozen at one time; the banner says so.
  if (frozen || !scene) return [];
  const staleAfter = scene.stale_after_s ?? 60;
  const out: Spread[] = [];
  const v = scene.boat_model?.speed_mps;
  if (v !== undefined && v > 0) {
    for (const b of snap.boats as Boat[]) {
      const age = snap.t - b.last_heard;
      // never heard: no last place at all; docked: at Korsør, not at sea
      if (b.heard === false || age <= staleAfter || isDocked(b, scene)) continue;
      out.push({
        kind: "boat", id: `USV ${String(b.id).padStart(2, "0")}`, lon: b.lon, lat: b.lat,
        r_m: age * v, age_s: age, basis: `model cruise speed ${v} m/s, current not included`,
      });
    }
  }
  for (const k of snap.contacts as Contact[]) {
    const age = snap.t - k.last_seen;
    if (age <= staleAfter || k.sog <= 0) continue;
    out.push({
      kind: "contact", id: k.track, lon: k.lon, lat: k.lat, r_m: (age * k.sog) / 1000, age_s: age,
      basis: "its last reported speed; it may have changed speed",
    });
  }
  return out;
}

/** "4.1 km" / "650 m" for chart labels. */
export function distWords(m: number): string {
  return m < 1000 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1)} km`;
}

/** Words for the Selected panel: "4.1 km (model cruise speed 2.3 m/s, current not included)". */
export function spreadText(snap: Snapshot, scene: SceneMsg | null, kind: Spread["kind"], id: string): string | null {
  const s = spreads(snap, scene, false).find((d) => d.kind === kind && d.id === id);
  return s ? `${distWords(s.r_m)} (${s.basis})` : null;
}

/** One chart label per group of circles that sit on top of each other (same rounded radius,
 * centres closer than half of it): "02, 03 could be within 2.3 km", never two stacked texts. */
export function spreadLabels(sp: Spread[]): { s: Spread; text: string }[] {
  const groups: { s: Spread; ids: string[] }[] = [];
  for (const s of sp) {
    const g = groups.find((x) => x.s.kind === s.kind && distWords(x.s.r_m) === distWords(s.r_m)
      && Math.hypot((x.s.lon - s.lon) * 63_800, (x.s.lat - s.lat) * 111_320) < s.r_m / 2);
    const short = s.kind === "boat" ? s.id.replace("USV ", "") : s.id;
    if (g) g.ids.push(short);
    else groups.push({ s, ids: [short] });
  }
  return groups.map(({ s, ids }) => ({
    s, text: `${s.kind === "boat" ? "USV " : ""}${ids.join(", ")} could be within ${distWords(s.r_m)}`,
  }));
}
