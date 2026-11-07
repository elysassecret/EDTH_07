// Live-data selectors shared by the integrated template and its tests. No demo fixtures.
import type { Alert, Boat, Decision, LogEvent, SceneMsg, Snapshot } from "./types";
import { segAges } from "./coverage";

export type DecisionAction = "confirm" | "stop" | "approve" | "decline";
export type Selection =
  { kind: "boat"; id: number } | { kind: "contact" | "segment"; id: string };
export const usv = (id: number) => `USV ${String(id).padStart(2, "0")}`;
export const endpoint = (id: number) => (id === 0 ? "shore" : usv(id));

export function sortedAlerts(alerts: Alert[]): Alert[] {
  const rank = { alarm: 0, warning: 1, caution: 2 };
  return [...new Map(alerts.map((alert) => [alert.id, alert])).values()].sort(
    (a, b) => Number(!!a.ack) - Number(!!b.ack) || rank[a.level] - rank[b.level] || b.t - a.t,
  );
}

export function canOperate(conn: string, channel: string): boolean {
  return conn === "live" && channel === "shore";
}
export function reportAge(boat: Boat, t: number): number | null {
  return boat.heard === false ? null : Math.max(0, t - boat.last_heard);
}
export function staleBoat(
  boat: Boat,
  snap: Snapshot,
  scene: SceneMsg | null,
  conn: string,
): boolean {
  const age = reportAge(boat, snap.t);
  return conn !== "live" || age === null || age > (scene?.stale_after_s ?? 60);
}
export function linkText(boat: Boat): string {
  if (boat.heard === false) return "Never heard";
  if (boat.link === "direct") return "Direct to shore";
  if (boat.link === "peer")
    return boat.via ? `Via ${usv(boat.via)}` : "Via peer";
  return "NO LINK";
}
export function actionsFor(decision: Decision): DecisionAction[] {
  return decision.actions?.length
    ? decision.actions
    : decision.tier === "delegated"
      ? ["confirm", "stop"]
      : ["approve", "decline"];
}
export function pendingDecisions(snap: Snapshot | null): Decision[] {
  return (snap?.decisions ?? [])
    .filter((d) => d.state === "pending")
    .sort(
      (a, b) =>
        Number(a.tier === "delegated") - Number(b.tier === "delegated") ||
        a.t - b.t ||
        a.id.localeCompare(b.id),
    );
}
export function decisionRevision(d: Decision, snap: Snapshot): string {
  // No fake proposal revision: use the actual task record and action identity.
  return JSON.stringify([
    snap.seed,
    d.id,
    d.task,
    snap.tasks[d.task],
    d.boat,
    d.t,
    d.text,
    d.tier,
    d.actions,
    d.state,
  ]);
}
export function eventCategory(event: LogEvent): string {
  if (event.exercise) return "Exercise";
  if (/decision|command/.test(event.kind)) return "Command";
  if (/contact|observ/.test(event.kind)) return "Observation";
  if (/gap|visit|cover/.test(event.kind)) return "Coverage";
  return "Coordination";
}
export function coverageRows(snap: Snapshot, scene: SceneMsg | null) {
  return segAges(snap, scene);
}
