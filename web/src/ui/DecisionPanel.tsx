// Owner: C. Feature 22: decision cards, the watch officer's main job.
// Two tiers (docs/research/operations_incidents_law.md):
//  - delegated: already running under a standing order; the officer may Confirm or Stop.
//  - held: the boat waits; no answer means no action. Approve or Decline.
// Keyboard: the oldest open card answers to C/S (delegated) or A/D (held).
import { useEffect, useState } from "react";
import { useStore } from "../store";
import { dur, utc } from "../format";
import { t0Of, type Decision, type Snapshot } from "../types";

type Action = "confirm" | "stop" | "approve" | "decline";
const KEY: Record<Action, string> = { confirm: "C", stop: "S", approve: "A", decline: "D" };
const WORD: Record<Action, string> = { confirm: "Confirm", stop: "Stop", approve: "Approve", decline: "Decline" };
const ALARM_AFTER_S = 300; // the mock raises an alarm on a held card after 05:00

const isOpen = (d: Decision) => d.state === "pending";
const tierOf = (d: Decision) => d.tier ?? "held";
const actionsOf = (d: Decision): Action[] =>
  d.actions?.length ? d.actions : tierOf(d) === "delegated" ? ["confirm", "stop"] : ["approve", "decline"];
const usv = (id: number) => `USV ${String(id).padStart(2, "0")}`;

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

function useSend() {
  const send = useStore((s) => s.send);
  const lastAck = useStore((s) => s.lastAck);
  const [sent, setSent] = useState<{ id: string; action: Action } | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (sent && lastAck && lastAck.id === sent.id) {
      if (!lastAck.ok) setError(lastAck.error ?? "rejected");
      setSent(null);
    }
  }, [lastAck, sent]);
  const answer = (d: Decision, action: Action) => {
    setError(null);
    if (send({ cmd: action, id: d.id })) setSent({ id: d.id, action });
    else setError("Not sent: no connection to the server");
  };
  return { answer, sent, error };
}

function DecisionCard({ d, snap, first, onAnswer, sending }: {
  d: Decision; snap: Snapshot; first: boolean; onAnswer: (d: Decision, a: Action) => void; sending: boolean;
}) {
  const hover = useStore((s) => s.setHoverDecision);
  const frozen = useStore((s) => s.conn) !== "live";
  const held = tierOf(d) === "held";
  const open = snap.t - d.t;
  return (
    <div
      className={`decision ${held ? "held" : "delegated"} ${open >= ALARM_AFTER_S && held ? "late" : ""}`}
      onMouseEnter={() => hover(d.id)}
      onMouseLeave={() => hover(null)}
    >
      <div className="tier">
        {held ? "WAITING FOR WATCH OFFICER" : "RUNNING UNDER STANDING ORDER"}
        <span className="open-for">open {dur(open)}</span>
      </div>
      <div className="text">{d.text}</div>
      <div className="sub">
        {held ? "Boat holds and keeps watching. No answer means no action." : "Already started. You may Confirm or Stop."}
        {d.boat ? ` · ${usv(d.boat)}` : ""}
        {d.route ? " · route shown dashed on chart" : ""}
      </div>
      <div className="buttons">
        {actionsOf(d).map((a) => (
          <button
            key={a}
            className={`act act-${a}`}
            disabled={frozen || sending}
            onClick={() => onAnswer(d, a)}
            title={first ? `Key ${KEY[a]}` : undefined}
          >
            {WORD[a]}{first && <kbd>{KEY[a]}</kbd>}
          </button>
        ))}
      </div>
      {frozen && <div className="sub warn">Feed lost: answers cannot be sent</div>}
      {sending && <div className="sub">Sent, waiting for the server</div>}
    </div>
  );
}

export function DecisionPanel() {
  const snap = useStore((s) => s.snap);
  const { answer, sent, error } = useSend();
  const open = snap ? snap.decisions.filter(isOpen).sort((a, b) => a.t - b.t) : [];
  const done = snap ? snap.decisions.filter((d) => !isOpen(d)).slice(-4).reverse() : [];

  // keyboard shortcuts act on the oldest open decision only
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || (e.target as HTMLElement)?.tagName === "INPUT") return;
      const d = open[0];
      if (!d || sent) return;
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
  const t0 = t0Of(snap);
  return (
    <section className="decisions">
      <h2>Decisions for the watch officer{open.length ? ` · ${open.length} open` : ""}</h2>
      {open.length === 0 && <p className="muted">None open.</p>}
      {open.map((d, i) => (
        <DecisionCard key={d.id} d={d} snap={snap} first={i === 0} onAnswer={answer} sending={sent?.id === d.id} />
      ))}
      {error && <p className="warn">{error}</p>}
      {done.length > 0 && (
        <ul className="done">
          {done.map((d) => (
            <li key={d.id}><span className="did">{d.id}</span> {d.text} — {outcome(d, t0)}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
