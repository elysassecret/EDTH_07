// Owner: C. Roadmap items 1 and 2: before approving, show what sending this boat costs.
// Everything here is a MODEL ESTIMATE from what the shore was told:
// - distance: the proposed route (straight line to the contact's last delivered position)
// - speed: the model cruise speed from config/boat.toml (scene.boat_model), no current
// - energy: the boat's last reported energy budget minus the transit at cruise
// - coverage: its cable segments' shore-reported ages plus the transit time
// The boat's own reason (why) is shown as the boat said it. Nothing is read from truth.
import type { Decision, SceneMsg, Snapshot } from "./types";
import { roleText } from "./roles";
import { segName } from "./coverage";
import { segAges } from "./coverage";

const R_EARTH_M = 6_371_000;

/** Great-circle length of a [lon, lat] path, metres. */
export function pathLength(path: [number, number][]): number {
  let m = 0;
  for (let i = 1; i < path.length; i++) {
    const [lon1, lat1] = path[i - 1].map((v) => (v * Math.PI) / 180);
    const [lon2, lat2] = path[i].map((v) => (v * Math.PI) / 180);
    const a = Math.sin((lat2 - lat1) / 2) ** 2
      + Math.cos(lat1) * Math.cos(lat2) * Math.sin((lon2 - lon1) / 2) ** 2;
    m += 2 * R_EARTH_M * Math.asin(Math.sqrt(a));
  }
  return m;
}

export interface ResponseCost {
  distance_m: number | null; // null = no route reported; a close look stops at verify_m
  stop_short_m: number; // how far short of the route's end the trip stops
  transit_s: number | null; // at model cruise speed
  arrive_t: number | null; // sim s
  energy_after_s: number | null; // reported budget minus transit
  below_reserve: boolean; // energy after the trip out is under the model reserve
  after_return_by: boolean; // arrives after the boat's own return-by time
  leaves: string; // what it is doing now, in words
  over_target: string[]; // its segments that pass the revisit target before it arrives
  unconfirmed: string[]; // its segments with no visit confirmed already
  reason: string; // the boat's own reason for the task it holds, if delivered
}

export function responseCost(d: Decision, snap: Snapshot, scene: SceneMsg | null): ResponseCost | null {
  const boat = snap.boats.find((b) => b.id === d.boat);
  if (!boat) return null;
  const v = scene?.boat_model?.speed_mps;
  // a "close" look ends at the boat's verify radius from the contact, not on top of it
  const stopShort = d.dec === "close" ? (boat.verify_m ?? 0) : 0;
  const distance = d.route && d.route.length > 1 ? Math.max(0, pathLength(d.route) - stopShort) : null;
  const transit = distance !== null && v ? distance / v : null;
  const energyAfter = transit !== null ? boat.endurance_s - transit : null;
  const reserve = scene?.boat_model?.reserve_s;
  const target = scene?.revisit_target_s;
  const mine = new Set(boat.tour.filter((s) => s.startsWith("seg:")));
  const ages = segAges(snap, scene).filter((a) => mine.has(a.id));
  const overTarget = transit === null || !target ? [] : ages
    .filter((a) => a.age !== null && a.age <= target && a.age + transit > target)
    .map((a) => segName(a.id));
  return {
    distance_m: distance,
    stop_short_m: stopShort,
    transit_s: transit,
    arrive_t: transit !== null ? snap.t + transit : null,
    energy_after_s: energyAfter,
    below_reserve: energyAfter !== null && reserve !== undefined && energyAfter < reserve,
    after_return_by: transit !== null && boat.must_return_by != null && snap.t + transit > boat.must_return_by,
    leaves: roleText(boat, scene),
    over_target: overTarget,
    unconfirmed: ages.filter((a) => a.age === null).map((a) => segName(a.id)),
    reason: snap.tasks[d.task]?.why ?? "",
  };
}
