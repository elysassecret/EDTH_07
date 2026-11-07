// Owner: C. The watch officer's escalation: a radio-ready report of one contact, written only
// from what the shore was told. The software never calls a contact a threat; reporting it
// onward (Navy / JRCC) is the officer's decision, and the server keeps the exact text sent.
import type { Contact, Snapshot } from "./types";
import { utc } from "./format";
import { usv } from "./console-model";

const MM_S_PER_KN = 514.444;

/** 55.459169 -> "55°27.55'N"; 10.870594 -> "010°52.24'E". */
export function ddm(v: number, pos: string, neg: string, degWidth: number): string {
  const a = Math.abs(v);
  let d = Math.floor(a);
  let m = Math.round((a - d) * 60 * 100) / 100;
  if (m >= 60) { d += 1; m = 0; }
  return `${String(d).padStart(degWidth, "0")}°${m.toFixed(2).padStart(5, "0")}'${v >= 0 ? pos : neg}`;
}

/** t0: the snapshot's UTC origin (types.ts t0Of), passed in so this file stays DOM-free. */
export function reportText(k: Contact, snap: Snapshot, t0: string): string {
  const kn = (k.sog / MM_S_PER_KN).toFixed(1);
  const who = k.ais ? `AIS ${k.name ?? k.track}` : "no AIS match (camera only)";
  const look = [
    k.flags.name ? "a close look read a name" : "",
    k.flags.anchor ? "anchor reported down" : "",
    k.flags.dwell ? "stayed slow near a cable" : "",
  ].filter(Boolean);
  return [
    `EDTH_07 USV watch, Korsør. Watch officer report, ${utc(t0, snap.t)}.`,
    `Contact ${k.track}: ${who}.`,
    `Last reported position ${ddm(k.lat, "N", "S", 2)} ${ddm(k.lon, "E", "W", 3)} at ${utc(t0, k.last_seen)}, course ${String(k.cog).padStart(3, "0")}°, speed ${kn} kn.`,
    `First seen ${utc(t0, k.first_seen)}. Seen by ${k.seen_by.map(usv).join(", ") || "no boat now"}${k.watcher ? `; ${usv(k.watcher)} keeps it in view` : ""}.`,
    look.length ? `Observed: ${look.join("; ")}.` : "No close look yet.",
    "Cue for a look from uncrewed boats; intent not established. Request: a manned asset to identify.",
  ].join("\n");
}

/** The latest escalation of this contact, if the officer made one. */
export function escalationOf(snap: Snapshot, id: string) {
  return [...(snap.escalations ?? [])].reverse().find((e) => e.id === id) ?? null;
}
