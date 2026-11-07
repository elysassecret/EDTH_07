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

// ---- #88 item 5: alerts grouped by what they are about, each with what the operator can do.
// Alert ids come from server/alerts.py: stale:N, nolink:N, rtb:N, picket:pick:X, overdue:seg:..,
// contact:TRACK, decision:ID, exercise:n.
export interface AlertSubject {
  key: string;
  title: string;
  boat?: number;
  contact?: string; // contact id in the snapshot, e.g. "contact:C-07"
  segment?: string;
  decision?: Decision;
}
const CABLE_NAME: Record<string, string> = { G: "Great Belt 1 fibre", H: "HVDC Storebælt I", M: "60 kV Sprogø–Funen" };

export function alertSubject(a: Alert, snap: Snapshot): AlertSubject {
  const [kind, ...rest] = a.id.split(":");
  const tail = rest.join(":");
  if (kind === "stale" || kind === "nolink" || kind === "rtb") {
    const boat = Number(tail);
    return { key: `boat:${boat}`, title: usv(boat), boat };
  }
  if (kind === "decision") {
    const d = snap.decisions.find((x) => x.id === tail);
    if (d?.boat) return { key: `boat:${d.boat}`, title: usv(d.boat), boat: d.boat, decision: d };
    return { key: `decision:${tail}`, title: "Decision", decision: d };
  }
  if (kind === "contact") {
    const c = snap.contacts.find((x) => x.track === tail || x.id === `contact:${tail}`);
    return { key: `contact:${tail}`, title: `Contact ${tail}`, contact: c?.id };
  }
  if (kind === "overdue") {
    const cable = tail.split(":")[1] ?? "";
    return { key: `cable:${cable}`, title: `Cable: ${CABLE_NAME[cable] ?? cable}`, segment: tail };
  }
  if (kind === "picket") return { key: `picket:${tail}`, title: `Lane picket ${tail.slice(5)}` };
  if (kind === "exercise") return { key: "exercise", title: "Exercise" };
  return { key: a.id, title: "Alert" };
}

/** What the operator can do: answer a held decision, or nothing beyond acknowledging. */
export function alertAction(a: Alert, snap: Snapshot): "answer" | "info" {
  const s = alertSubject(a, snap);
  return s.decision && s.decision.state === "pending" ? "answer" : "info";
}

export interface AlertGroup { subject: AlertSubject; alerts: Alert[] }

/** One group per boat, cable, contact or picket. Groups with an unacknowledged alert come
 * first, then by their most severe level, then newest. Inside a group: newest first. */
export function groupAlerts(alerts: Alert[], snap: Snapshot): AlertGroup[] {
  const rank = { alarm: 0, warning: 1, caution: 2 };
  const groups = new Map<string, AlertGroup>();
  for (const a of sortedAlerts(alerts)) {
    const subject = alertSubject(a, snap);
    const g = groups.get(subject.key) ?? { subject, alerts: [] };
    g.alerts.push(a);
    groups.set(subject.key, g);
  }
  const score = (g: AlertGroup) => {
    const open = g.alerts.filter((a) => !a.ack);
    const pool = open.length ? open : g.alerts;
    return [open.length ? 0 : 1, Math.min(...pool.map((a) => rank[a.level])), -Math.max(...pool.map((a) => a.t))];
  };
  return [...groups.values()]
    .map((g) => ({ ...g, alerts: [...g.alerts].sort((a, b) => Number(!!a.ack) - Number(!!b.ack) || b.t - a.t) }))
    .sort((x, y) => {
      const [a, b] = [score(x), score(y)];
      return a[0] - b[0] || a[1] - b[1] || a[2] - b[2] || x.subject.key.localeCompare(y.subject.key);
    });
}
