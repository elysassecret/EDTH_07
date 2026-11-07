// Owner: C. Features 22 + U1: decisions, the watch officer's main job.
// Two tiers (docs/research/operations_incidents_law.md):
//  - delegated: already running under a standing order; the officer may Confirm or Stop.
//  - held: the boat waits; no answer means no action. Approve or Decline.
// U1 decision dock: the oldest open decision, fixed bottom-right, the loudest thing on screen.
// It shows what, why, which boat, the ghost route, and how long it has waited. The contract
// has no deadline, so no countdown is invented (gap G1); "waiting M:SS" counts from Decision.t.
// Keyboard: the dock's card answers to C/S (delegated) or A/D (held).
import { useEffect, useState } from "react";
import { useStore } from "../store";
import { dur, utc } from "../format";
import { t0Of, type Contact, type Decision, type Snapshot } from "../types";

type Action = "confirm" | "stop" | "approve" | "decline";
const KEY: Record<Action, string> = { confirm: "C", stop: "S", approve: "A", decline: "D" };
const WORD: Record<Action, string> = { confirm: "Confirm", stop: "Stop", approve: "Approve", decline: "Decline" };
const ALARM_AFTER_S = 300; // the same 05:00 as server/alerts.py: unanswered held decision → alarm

const isOpen = (d: Decision) => d.state === "pending";
const tierOf = (d: Decision) => d.tier ?? "held";
export const actionsOf = (d: Decision): Action[] =>
  d.actions?.length ? d.actions : tierOf(d) === "delegated" ? ["confirm", "stop"] : ["approve", "decline"];
const usv = (id: number) => `USV ${String(id).padStart(2, "0")}`;

/** Held decisions first (nothing happens without an answer), then oldest first. */
export function openDecisions(snap: Snapshot | null): Decision[] {
  const rank = (d: Decision) => (tierOf(d) === "held" ? 0 : 1);
  return snap ? snap.decisions.filter(isOpen).sort((a, b) => rank(a) - rank(b) || a.t - b.t) : [];
}

function outcome(d: Decision, t0: string): string {
  const s = d.status ?? d.state;
  const at = d.answered !== null && d.answered !== undefined ? ` ${utc(t0, d.answered)}` : "";
  switch (s) {
    case "confirmed": return `Confirmed by watch officer${at}`;
    case "stopped": return `Stopped by watch officer${at}`;
    case "approved": return `Approved by watch officer${at}`;
    case "declined": return `Declined by watch officer${at}`;
    case "expired": return "Decision expired, not delivered";
    case "withdrawn": return "Withdrawn: no longer needed";
    case "delivered": return "Delivered";
    default: return s;
  }
}

/** "Why" in plain words, from the contact the decision is about (shore data only). */
function why(d: Decision, snap: Snapshot): string | null {
  const c: Contact | undefined = snap.contacts.find((k) => k.id === d.task || `contact:${k.track}` === d.task);
  if (!c) return null;
  const kind = c.ais ? "AIS track" : c.source === "fused" ? "AIS and camera" : "camera only, no AIS match";
  const seen = c.seen_by.length ? `seen by ${c.seen_by.map(usv).join(", ")}` : "no boat sees it now";
  return `${c.track}: ${kind} · ${seen} · last seen ${dur(snap.t - c.last_seen)} ago · a cue for a look`;
}

export function useSend() {
  const send = useStore((s) => s.send);
  const holdAnswer = useStore((s) => s.holdAnswer);
  const lastAck = useStore((s) => s.lastAck);
  const answering = useStore((s) => s.answering);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (lastAck && !lastAck.ok && lastAck.cmd && lastAck.cmd in KEY) setError(lastAck.error ?? "rejected");
  }, [lastAck]);
  const answer = (d: Decision, action: Action) => {
    setError(null);
    const cmd = { cmd: action, id: d.id } as const;
    if (action === "confirm") {
      // confirming what is already running changes nothing, so it goes at once
      if (send(cmd)) useStore.setState({ answering: d.id });
      else setError("Not sent: no connection to the server");
      return;
    }
    // G2: Approve, Decline and Stop wait 5 s with UNDO before they leave the console
    holdAnswer(cmd, `${WORD[action]}: ${d.text}`);
  };
  return { answer, sent: answering, error };
}

/** U1: fixed bottom-right. Hidden behind a small "none waiting" pill when nothing is open. */
export function DecisionDock() {
  const snap = useStore((s) => s.snap);
  const frozen = useStore((s) => s.conn) !== "live";
  const hover = useStore((s) => s.setHoverDecision);
  const { answer, sent, error } = useSend();
  const held = useStore((s) => s.held);
  const undo = useStore((s) => s.undoAnswer);
  const [nowMs, setNowMs] = useState(Date.now());
  useEffect(() => {
    if (!held) return;
    const id = window.setInterval(() => setNowMs(Date.now()), 200);
    return () => window.clearInterval(id);
  }, [held]);
  const open = openDecisions(snap);
  const d = open[0];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || ["INPUT", "SELECT", "TEXTAREA"].includes((e.target as HTMLElement)?.tagName)) return;
      if (!d || sent === d.id || useStore.getState().held) return;
      const a = actionsOf(d).find((x) => KEY[x] === e.key.toUpperCase());
      if (a && useStore.getState().conn === "live") {
        e.preventDefault();
        answer(d, a);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!snap) return null;
  if (!d) return <div className="dock-idle" aria-live="polite">No decisions waiting</div>;
  const isHeld = tierOf(d) === "held";
  const waited = snap.t - d.t;
  const late = isHeld && waited >= ALARM_AFTER_S;
  const reason = why(d, snap);
  return (
    <section
      className={`dock ${isHeld ? "held" : "delegated"} ${late ? "late" : ""}`}
      role="region" aria-label="Decision waiting for the watch officer"
      onMouseEnter={() => hover(d.id)} onMouseLeave={() => hover(null)}
    >
      <div className="dock-head">
        <span className="dock-tier">{isHeld ? "NEEDS YOUR YES" : "RUNNING · YOU MAY STOP IT"}</span>
        {open.length > 1 && <span className="dock-badge">+{open.length - 1} queued</span>}
        <span className="dock-wait">waiting {dur(waited)}</span>
      </div>
      <div className="dock-what">{d.text}</div>
      {reason && <div className="dock-why">{reason}</div>}
      <div className="dock-sub">
        {d.boat ? `${usv(d.boat)} · ` : ""}
        {isHeld ? "The boat holds and keeps watching. No answer means no action." : "Already started under the standing order."}
        {d.route ? " Route dashed on the chart." : ""}
      </div>
      {held ? (
        <div className="undo" role="status">
          <span>Sending in {Math.max(0, Math.ceil((held.until - nowMs) / 1000))} s · {held.label}</span>
          <button className="act act-undo" onClick={() => { undo(); }}>UNDO<kbd>Esc</kbd></button>
        </div>
      ) : (
        <div className="buttons">
          {actionsOf(d).map((a) => (
            <button key={a} className={`act act-${a}`} disabled={frozen || sent === d.id} onClick={() => answer(d, a)} title={`Key ${KEY[a]}`}>
              {WORD[a]}<kbd>{KEY[a]}</kbd>
            </button>
          ))}
        </div>
      )}
      {frozen && <div className="dock-sub warn">Feed lost: answers cannot be sent</div>}
      {sent === d.id && !held && <div className="dock-sub">Sent, waiting for the server</div>}
      {error && <div className="dock-sub warn">{error}</div>}
      {open.length > 1 && (
        <ol className="dock-queue">
          {open.slice(1, 4).map((q) => <li key={q.id}>{q.text} · waiting {dur(snap.t - q.t)}</li>)}
        </ol>
      )}
    </section>
  );
}

/** Right panel: what was decided (the dock shows what is open). */
export function DecisionPanel() {
  const snap = useStore((s) => s.snap);
  if (!snap) return null;
  const open = openDecisions(snap).length;
  const done = snap.decisions.filter((d) => !isOpen(d)).slice(-4).reverse();
  const t0 = t0Of(snap);
  return (
    <section className="decisions">
      <h2>Decisions{open ? ` · ${open} open (bottom right)` : ""}</h2>
      {done.length === 0 ? <p className="muted">None answered yet.</p> : (
        <ul className="done">
          {done.map((d) => (
            <li key={d.id}><span className="did">{d.id}</span> {d.text} — {outcome(d, t0)}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
