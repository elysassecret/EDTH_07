// Owner: C. Plain words for what a boat is doing, from its task IDs and mode.
// The mock sends role_text itself; the real sim sends raw task IDs (seg:H:0, pick:N, relay).
import type { Boat, SceneMsg } from "./types";

// task letters from world/routes.py CABLE_IDS
export const CABLE: Record<string, string> = { G: "Great Belt 1 fibre", H: "HVDC Storebælt I", M: "60 kV Sprogø–Funen" };

const M_PER_DEG = 111_320;
const ROUNDING_M = 2; // reported x/y are whole metres, so a docked boat can read ~1 m past home_m

/** Back home: mode UNAVAILABLE within the agents' home radius of the shore station. A boat
 * switched off at sea is UNAVAILABLE too (truth view), but far from shore: not docked. */
export function isDocked(b: Boat, scene: SceneMsg | null): boolean {
  if (b.mode !== "UNAVAILABLE" || !scene || scene.home_m === undefined) return false;
  const [lon, lat] = scene.shore;
  const dx = (b.lon - lon) * M_PER_DEG * Math.cos((lat * Math.PI) / 180);
  const dy = (b.lat - lat) * M_PER_DEG;
  return Math.hypot(dx, dy) <= scene.home_m + ROUNDING_M;
}

export function roleText(b: Boat, scene: SceneMsg | null = null): string {
  if (b.role_text) return b.role_text;
  if (b.mode === "RETURNING") return "Return to Korsør";
  if (b.mode === "UNAVAILABLE") return isDocked(b, scene) ? "Docked at Korsør" : "Unavailable";
  const roles = b.roles;
  const contact = roles.find((r) => r.startsWith("contact:"));
  if (contact) return `Keeping ${contact.slice("contact:".length)} in view`;
  const parts: string[] = [];
  const cables = [...new Set(roles.filter((r) => r.startsWith("seg:")).map((r) => r.split(":")[1]))];
  if (cables.length) parts.push(`Cable sweep (${cables.map((c) => CABLE[c] ?? c).join(", ")})`);
  for (const r of roles) if (r.startsWith("pick:")) parts.push(`Lane picket ${r.slice(5)}`);
  if (roles.includes("relay")) parts.push("Relay");
  for (const r of roles) {
    if (!r.startsWith("seg:") && !r.startsWith("pick:") && !r.startsWith("contact:") && r !== "relay") parts.push(r);
  }
  if (parts.length) return parts.join(" + ");
  return b.mode === "SHADOWING" ? "Moving to keep contact in view" : "No task";
}
