// Owner: C. Feature 24: revisit age per cable segment, against the team's revisit target.
// Segments come from the scene message (the real sim has seven, H:0..2 included), never a
// fixed list. Ages are what the snapshot says: shore-reported on /shore, physical on /truth.
// Wording rule: say how old the oldest visit is; never say "coverage restored".
import type { SceneMsg, Snapshot } from "./types";
import { CABLE } from "./roles";
import { hhmm } from "./format";

export type Band = "recent" | "due" | "over" | "none";

export interface SegAge {
  id: string;
  age: number | null; // seconds since the last visit; null = no visit reported
  band: Band;
}

/** Band words, shown next to the colour (never colour alone). */
export const BAND_WORD: Record<Band, string> = {
  recent: "within half the target",
  due: "due: over half the target",
  over: "over target",
  none: "no visit reported",
};

export function segName(id: string): string {
  const [, cable, part] = id.split(":");
  return `${CABLE[cable] ?? cable}, part ${Number(part) + 1}`;
}

export function segAges(snap: Snapshot, scene: SceneMsg | null): SegAge[] {
  const target = scene?.revisit_target_s;
  const ids = scene ? Object.keys(scene.segments) : Object.keys(snap.seg_age);
  return ids.sort().map((id) => {
    const v = snap.seg_age[id];
    // Shore encodes missing sample history as age t. Treat that ambiguous value
    // conservatively as unconfirmed, including the initial t=0 frame.
    const age = v === undefined || v === null || (snap.view === "shore" && v >= snap.t) ? null : v;
    let band: Band = "none";
    if (age !== null) band = !target ? "recent" : age > target ? "over" : age > target / 2 ? "due" : "recent";
    return { id, age, band };
  });
}

/** The oldest segment: one with no visit report counts as oldest. */
export function worst(ages: SegAge[]): SegAge | null {
  let w: SegAge | null = null;
  for (const a of ages) {
    if (!w) w = a;
    else if (w.age !== null && (a.age === null || a.age > w.age)) w = a;
  }
  return w;
}

/** #88: the one coverage headline in words. Shore-reported ages only; never "restored". */
export function coverageWords(ages: SegAge[], target: number | undefined, t: number, t0: string): string {
  const n = ages.length;
  if (n === 0) return "No cable segments in the picture";
  const none = ages.filter((a) => a.age === null);
  if (target === undefined) return `${n - none.length} of ${n} cable segments visited · no revisit target set`;
  const over = ages.filter((a) => a.age !== null && a.age > target);
  if (over.length === 0 && none.length === 0) return `All ${n} cable segments within the revisit target`;
  const parts = [`${n - over.length - none.length} of ${n} cable segments within target`];
  if (over.length) {
    const oldest = Math.max(...over.map((a) => a.age as number));
    const which = over.length === 1 ? over[0].id : `${over.length} segments`;
    parts.push(`${which} overdue since ${hhmm(t0, t - (oldest - target))}`);
  }
  if (none.length) parts.push(`${none.length === 1 ? none[0].id : `${none.length} segments`}: no visit confirmed`);
  return parts.join(" · ");
}
