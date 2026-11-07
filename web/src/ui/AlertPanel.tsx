// Owner: C. Feature 23: alerts in three levels, as on a ship's bridge.
// Each level has its own colour, shape and word, so it reads without colour too:
//   ALARM   red triangle    act now; flashes until acknowledged
//   WARNING orange circle   may become a hazard
//   CAUTION yellow square   be aware
// Acknowledge means "I have seen it". It does not answer a decision or fix anything.
// One row per alert id (the server dedups; the console does again, to be safe).
import { useState } from "react";
import { useStore } from "../store";
import { utc } from "../format";
import { t0Of, type Alert } from "../types";

type Level = Alert["level"];
const RANK: Record<Level, number> = { alarm: 0, warning: 1, caution: 2 };
const WORD: Record<Level, string> = { alarm: "ALARM", warning: "WARNING", caution: "CAUTION" };
const SHOW = 6; // rows before "show all"

export function LevelIcon({ level }: { level: Level }) {
  return (
    <svg className={`lvl-icon ${level}`} width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      {level === "alarm" && <path d="M9 1.5 17 16.5H1z" />}
      {level === "warning" && <circle cx="9" cy="9" r="7.5" />}
      {level === "caution" && <rect x="2" y="2" width="14" height="14" />}
      <text x="9" y={level === "alarm" ? 14.5 : 13} textAnchor="middle">!</text>
    </svg>
  );
}

/** Unacknowledged first, then by level, newest first. One per id. */
export function sortedAlerts(alerts: Alert[]): Alert[] {
  const byId = new Map<string, Alert>();
  for (const a of alerts) byId.set(a.id, a);
  return [...byId.values()].sort(
    (a, b) => Number(!!a.ack) - Number(!!b.ack) || RANK[a.level] - RANK[b.level] || b.t - a.t,
  );
}

function useAck() {
  const send = useStore((s) => s.send);
  const frozen = useStore((s) => s.conn) !== "live";
  const setDigest = useStore((s) => s.setDigest);
  // U2: acknowledging is a natural moment to catch up on what changed
  return { ack: (id: string) => { send({ cmd: "ack", id }); setDigest(true); }, frozen };
}

function AlertRow({ a, t0 }: { a: Alert; t0: string }) {
  const { ack, frozen } = useAck();
  return (
    <li className={`alert ${a.level} ${a.ack ? "acked" : ""}`}>
      <LevelIcon level={a.level} />
      <div className="alert-body">
        <div className="alert-head">
          <span className="lvl">{WORD[a.level]}</span>
          <span className="at">{utc(t0, a.t)}</span>
        </div>
        <div className="alert-text">{a.text}</div>
      </div>
      {a.ack ? (
        <span className="acked-word">Seen</span>
      ) : (
        <button className="ack" disabled={frozen} onClick={() => ack(a.id)}>Acknowledge</button>
      )}
    </li>
  );
}

export function AlertPanel() {
  const snap = useStore((s) => s.snap);
  const [all, setAll] = useState(false);
  if (!snap) return null;
  const list = sortedAlerts(snap.alerts);
  const count = (l: Level) => list.filter((a) => a.level === l && !a.ack).length;
  const counts = (["alarm", "warning", "caution"] as Level[])
    .filter((l) => count(l) > 0)
    .map((l) => `${count(l)} ${l}`);
  const t0 = t0Of(snap);
  const shown = all ? list : list.slice(0, SHOW);
  return (
    <section className="alerts">
      <h2>Alerts{counts.length ? ` · ${counts.join(" · ")}` : ""}</h2>
      {list.length === 0 && <p className="muted">None active.</p>}
      <ul>{shown.map((a) => <AlertRow key={a.id} a={a} t0={t0} />)}</ul>
      {list.length > SHOW && (
        <button className="more" onClick={() => setAll((v) => !v)}>
          {all ? "Show fewer" : `Show all ${list.length}`}
        </button>
      )}
    </section>
  );
}

/** One line under the top bar: the most urgent unacknowledged alarm or warning. */
export function AlertStrip() {
  const snap = useStore((s) => s.snap);
  const { ack, frozen } = useAck();
  if (!snap) return null;
  const top = sortedAlerts(snap.alerts).find((a) => !a.ack && a.level !== "caution");
  if (!top) return null;
  const more = snap.alerts.filter((a) => !a.ack && a.level !== "caution").length - 1;
  return (
    <div className={`alert-strip ${top.level}`} role="alert">
      <LevelIcon level={top.level} />
      <span className="lvl">{WORD[top.level]}</span>
      <span className="alert-text">{top.text}</span>
      {more > 0 && <span className="muted">+{more} more</span>}
      <button className="ack" disabled={frozen} onClick={() => ack(top.id)}>Acknowledge</button>
    </div>
  );
}
