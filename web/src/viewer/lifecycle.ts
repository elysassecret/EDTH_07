import { dur } from "../format";
import type { Boat, Snapshot } from "../types";

/** Labels come only from the current truth frame, never a browser-side launch schedule. */
export function vesselLifecycle(
  boat: Pick<Boat, "id" | "mode">,
  snapshot: Pick<Snapshot, "t" | "t_exact" | "swaps">,
) {
  const readyAt = snapshot.swaps?.[String(boat.id)];
  // A cancelled swap may remain in the server's event-derived extras. An active
  // vessel must not be described as swapping or ready merely because a deadline passed.
  if (boat.mode === "UNAVAILABLE" && readyAt !== undefined && Number.isFinite(readyAt)) {
    const remaining = readyAt - (snapshot.t_exact ?? snapshot.t);
    return {
      label: "Battery swap",
      detail: remaining > 0
        ? `At Korsør · about ${dur(remaining)} sim time remaining`
        : "At Korsør · awaiting swap confirmation",
    };
  }
  if (boat.mode === "RETURNING") {
    return { label: "Returning to Korsør", detail: "Returning under the shared simulation's control" };
  }
  // Truth does not expose an individual boat's pending launch. UNAVAILABLE can
  // also mean switched off, so do not guess that this boat is waiting to launch.
  return { label: boat.mode.replaceAll("_", " "), detail: null };
}
