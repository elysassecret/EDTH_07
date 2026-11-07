// Owner: C. Feature 25: watchable, honest demo.
// - Warp: what speed the sim runs at, who set it, and a note while auto-warp slows for an event.
// - EXERCISE banner: shown once the run has any exercise failure (scripted or injected).
// - Event log: every event the shore view carries, newest first, with UTC time.
// - Failure injection (BUILD_PLAN step 14): any boat, any link, one way or both; labelled EXERCISE.
import { useEffect, useState } from "react";
import { useStore } from "../store";
import { utc } from "../format";
import { t0Of, type Command } from "../types";

const SPEEDS = [1, 5, 60, 240];

export function WarpControl() {
  const snap = useStore((s) => s.snap);
  const send = useStore((s) => s.send);
  const frozen = useStore((s) => s.conn) !== "live";
  if (!snap) return null;
  const mode = snap.warp_mode ?? "auto";
  const paused = mode === "paused" || snap.speed === 0;
  return (
    <div className="warp">
      <span className="warp-now">
        {paused ? "PAUSED" : `${snap.speed}×`} <span className="muted">{paused ? "" : mode}</span>
        {snap.near_event && !paused && <span className="slow"> · slowing for event</span>}
      </span>
      <button disabled={frozen} onClick={() => send({ cmd: "pause", on: !paused })}>{paused ? "Run" : "Pause"}</button>
      <button disabled={frozen} className={mode === "auto" ? "on" : ""} onClick={() => send({ cmd: "speed", value: "auto" })}>Auto</button>
      {SPEEDS.map((v) => (
        <button key={v} disabled={frozen} className={mode === "manual" && snap.speed === v ? "on" : ""}
          onClick={() => send({ cmd: "speed", value: v })}>{v}×</button>
      ))}
    </div>
  );
}

export function ExerciseBanner() {
  const snap = useStore((s) => s.snap);
  if (!snap) return null;
  const ex = snap.events.filter((e) => e.exercise);
  if (ex.length === 0) return null;
  const last = ex[ex.length - 1];
  return (
    <div className="banner exercise" role="status">
      EXERCISE — failures in this run are injected, not real · latest {utc(t0Of(snap), last.t)}: {last.text.replace(/^EXERCISE: /, "")}
    </div>
  );
}

type Row = { t: number; text: string; exercise?: boolean; key: string };

/** Story = narrator lines (server/narrator.py, from /shore frames only); Log = raw events. */
export function EventLog() {
  const snap = useStore((s) => s.snap);
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"story" | "log">("story");
  if (!snap) return null;
  const t0 = t0Of(snap);
  const story: Row[] = [...(snap.narration ?? [])].reverse().map((n, i) => ({ ...n, key: `n${n.t}-${i}` }));
  const log: Row[] = [...snap.events].reverse().map((e, i) => ({
    t: e.t, text: e.text.replace(/^EXERCISE: /, ""), exercise: e.exercise, key: `e${e.t}-${e.kind}-${i}`,
  }));
  const rows = tab === "story" ? story : log;
  const shown = open ? rows : rows.slice(0, tab === "story" ? 2 : 1);
  return (
    <div className={`eventlog ${open ? "open" : ""}`}>
      <div className="tabs">
        <button className={tab === "story" ? "on" : ""} onClick={() => setTab("story")}>What changed · {story.length}</button>
        <button className={tab === "log" ? "on" : ""} onClick={() => setTab("log")}>Event log · {log.length}</button>
        <button className="more" onClick={() => setOpen((v) => !v)}>{open ? "Less" : "More"}</button>
      </div>
      {rows.length === 0 && <div className="muted">{tab === "story" ? "Nothing has changed yet." : "No events yet."}</div>}
      <ol>
        {shown.map((r) => (
          <li key={r.key} className={r.exercise ? "ex" : ""}>
            <span className="at">{utc(t0, r.t)}</span>
            {r.exercise && <span className="chip ex">EXERCISE</span>}
            <span>{r.text}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

type Other = "shore" | number;

export function InjectPanel({ onClose }: { onClose: () => void }) {
  const snap = useStore((s) => s.snap);
  const send = useStore((s) => s.send);
  const lastAck = useStore((s) => s.lastAck);
  const frozen = useStore((s) => s.conn) !== "live";
  const [a, setA] = useState<number | null>(null);
  const [b, setB] = useState<Other>("shore");
  const [both, setBoth] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [result, setResult] = useState<string>("");
  const placing = useStore((s) => s.placing);
  const setPlacing = useStore((s) => s.setPlacing);
  const [ais, setAis] = useState(false);
  useEffect(() => {
    if (lastAck?.cmd !== "inject") return;
    if (lastAck.ok && lastAck.placed) {
      setSent(`Placed ${lastAck.placed} on ${lastAck.on} (snapped to the nearest cable sample)`);
      setResult(" · truth only: the shore sees it only if a boat does");
    } else setResult(lastAck.ok ? " · accepted" : ` · rejected: ${lastAck.error ?? ""}`);
  }, [lastAck]);
  if (!snap) return null;
  const ids = [...new Set(snap.boats.map((x) => x.id))].sort((x, y) => x - y);
  const boat = a ?? ids[0] ?? 1;
  const others: Other[] = ["shore", ...ids.filter((i) => i !== boat)];
  const other = others.includes(b) ? b : "shore";
  const usv = (i: number) => `USV ${String(i).padStart(2, "0")}`;
  const name = (o: Other) => (o === "shore" ? "shore" : usv(o));

  const fire = (label: string, cmds: Command[]) => {
    const ok = cmds.every((c) => send(c));
    setResult("");
    setSent(ok ? label : "Not sent: no connection to the server");
  };
  const link = (kind: "link_off" | "link_on") => {
    // links are directed; the world takes only boat -> X, so shore -> boat stays as it is
    const cmds: Command[] = [{ cmd: "inject", kind, a: boat, b: other }];
    if (both && other !== "shore") cmds.push({ cmd: "inject", kind, a: other, b: boat });
    fire(`${kind === "link_off" ? "Cut" : "Restored"} ${usv(boat)} ${cmds.length > 1 ? "↔" : "→"} ${name(other)}`, cmds);
  };

  return (
    <div className="inject" role="dialog" aria-label="Exercise failure injection">
      <div className="inject-head">
        <span className="chip ex">EXERCISE</span> Failure injection
        <button className="close" onClick={onClose} aria-label="Close">×</button>
      </div>
      <label>Boat{" "}
        <select value={boat} onChange={(e) => setA(Number(e.target.value))}>
          {ids.map((i) => <option key={i} value={i}>{usv(i)}</option>)}
        </select>
      </label>
      <div className="row">
        <button disabled={frozen} onClick={() => fire(`Battery low: ${usv(boat)}`, [{ cmd: "inject", kind: "battery_low", a: boat }])}>Battery low</button>
        <button disabled={frozen} onClick={() => fire(`Switched off: ${usv(boat)}`, [{ cmd: "inject", kind: "boat_off", a: boat }])}>Switch off</button>
      </div>
      <label>Link to{" "}
        <select value={String(other)} onChange={(e) => setB(e.target.value === "shore" ? "shore" : Number(e.target.value))}>
          {others.map((o) => <option key={String(o)} value={String(o)}>{name(o)}</option>)}
        </select>
      </label>
      {other !== "shore" && (
        <label className="check"><input type="checkbox" checked={both} onChange={(e) => setBoth(e.target.checked)} /> both directions</label>
      )}
      <div className="row">
        <button disabled={frozen} onClick={() => link("link_off")}>Cut link</button>
        <button disabled={frozen} onClick={() => link("link_on")}>Restore link</button>
      </div>
      <div className="row">
        <button disabled={frozen} className={placing ? "on" : ""} onClick={() => setPlacing(placing ? null : { ais })}>
          {placing ? "Click on the chart… (cancel)" : "Place synthetic contact"}
        </button>
        <label className="check"><input type="checkbox" checked={ais} onChange={(e) => setAis(e.target.checked)} /> AIS on</label>
      </div>
      <div className="row">
        <button disabled={frozen} onClick={() => fire(`Switched back on: ${usv(boat)}`, [{ cmd: "inject", kind: "boat_restore", a: boat }])}
          title="Same boat and battery as when it was switched off (no recharge)">Switch back on</button>
      </div>
      <div className="muted small">
        {other === "shore" ? `One way: ${usv(boat)} → shore (shore can still reach the boat).` : both ? "Both directions." : `One way: ${usv(boat)} → ${name(other)}.`}
      </div>
      {sent && <div className="small">{sent}{result}</div>}
    </div>
  );
}
