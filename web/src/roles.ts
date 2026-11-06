// Owner: C. Plain words for what a boat is doing, from its task IDs and mode.
// The mock sends role_text itself; the real sim sends raw task IDs (seg:H:0, pick:N, relay).
import type { Boat } from "./types";

// task letters from world/routes.py CABLE_IDS
export const CABLE: Record<string, string> = { G: "Great Belt 1 fibre", H: "HVDC Storebælt I", M: "60 kV Sprogø–Funen" };

export function roleText(b: Boat): string {
  if (b.role_text) return b.role_text;
  if (b.mode === "RETURNING") return "Return to Korsør";
  if (b.mode === "UNAVAILABLE") return "Unavailable";
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
