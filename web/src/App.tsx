// Owner: C. Page layout: top bar, banners, chart, fleet panel.
import { useCallback, useState } from "react";
import { Chart } from "./map/Chart";
import { useStore } from "./store";
import { dur, utc } from "./format";
import { FleetPanel } from "./ui/BoatCard";
import { AlertStrip } from "./ui/AlertPanel";
import { CoverageBox } from "./ui/Coverage";
import { EventLog, ExerciseBanner, InjectPanel, WarpControl } from "./ui/Demo";
import { OPERATOR_MODE, t0Of } from "./types";
import { EvalBanner } from "./ui/EvalPanel";
import { EvidencePanel } from "./ui/Evidence";
import { DecisionDock } from "./ui/DecisionPanel";
import { Digest } from "./ui/Digest";
import { StatusLine } from "./ui/StatusLine";

function TopBar({ sat, satState, onSat, inject, onInject, evidence, onEvidence }: {
  sat: boolean; satState: "none" | "ready" | "checking"; onSat: () => void; inject: boolean; onInject: () => void;
  evidence: boolean; onEvidence: () => void;
}) {
  const snap = useStore((s) => s.snap);
  const channel = useStore((s) => s.channel);
  const setChannel = useStore((s) => s.setChannel);
  const [menu, setMenu] = useState(false);
  return (
    <header className="topbar">
      <div className="title">Shore console · Great Belt cable watch</div>
      <div className="clock">{snap ? utc(t0Of(snap), snap.t) : "--:--:--Z"}</div>
      <div className="meta">
        {snap ? <>sim {dur(snap.t)} · {snap.source === "mock" ? "MOCK FEED" : snap.source}</> : "waiting for feed"}
      </div>
      <WarpControl />
      <div className="controls">
        <button className={menu ? "on" : ""} aria-expanded={menu} onClick={() => setMenu((v) => !v)}>View ▾</button>
        {menu && (
          <div className="viewmenu" role="menu" onClick={() => setMenu(false)}>
            {!OPERATOR_MODE && <EvalToggle />}
            {!OPERATOR_MODE && <button onClick={() => setChannel(channel === "shore" ? "truth" : "shore")} className={channel === "truth" ? "on" : ""}>
              {channel === "shore" ? "Channel: SHORE (delivered)" : "Channel: TRUTH (evaluator)"}
            </button>}
            <CommsToggle />
            <button onClick={onSat} disabled={satState !== "ready"} className={sat ? "on" : ""}
              title={satState === "none" ? "web/public/geo/s2_box.png not supplied yet" : ""}>
              {satState === "ready" ? (sat ? "Satellite ON" : "Satellite OFF") : satState === "none" ? "No satellite image yet" : "Satellite…"}
            </button>
            <DisplayToggle />
            <button onClick={onInject} className={inject ? "on" : ""}>Exercise controls</button>
            <button onClick={onEvidence} className={evidence ? "on" : ""}>Evidence</button>
          </div>
        )}
      </div>
      <StatusLine />
    </header>
  );
}

const NEXT = { dusk: "night", night: "day", day: "dusk" } as const;

function DisplayToggle() {
  const d = useStore((s) => s.display);
  const set = useStore((s) => s.setDisplay);
  return <button onClick={() => set(NEXT[d])} title="Day, dusk and night display (feature 33)">Display: {d.toUpperCase()}</button>;
}

function EvalToggle() {
  const on = useStore((s) => s.evalOn);
  const toggle = useStore((s) => s.toggleEval);
  return <button onClick={toggle} className={on ? "on eval" : ""} title="Truth next to the shore picture, for judges">{on ? "Evaluator ON" : "Evaluator OFF"}</button>;
}

function CommsToggle() {
  const on = useStore((s) => s.showComms);
  const toggle = useStore((s) => s.toggleComms);
  return <button onClick={toggle} className={on ? "on" : ""}>{on ? "Comms ON" : "Comms OFF"}</button>;
}

function FeedBanner() {
  const conn = useStore((s) => s.conn);
  const snap = useStore((s) => s.snap);
  if (conn === "live") return null;
  const frozen = snap ? `display frozen at ${utc(t0Of(snap), snap.t)}` : "no data received yet";
  return (
    <div className="banner lost" role="alert">
      {conn === "lost" ? "FEED LOST" : "CONNECTING"} — {frozen} · reconnecting
    </div>
  );
}

function TruthBanner() {
  const channel = useStore((s) => s.channel);
  if (channel !== "truth") return null;
  return <div className="banner truth">TRUTH VIEW — evaluator only, not what the shore receives</div>;
}

export function App() {
  const [sat, setSat] = useState(false);
  const [satState, setSatState] = useState<"none" | "ready" | "checking">("checking");
  const onSatState = useCallback((s: "none" | "ready") => setSatState(s), []);
  const [inject, setInject] = useState(false);
  const [evidence, setEvidence] = useState(false);
  const display = useStore((st) => st.display);
  return (
    <div className="app" data-display={display}>
      <TopBar sat={sat} satState={satState} onSat={() => setSat((v) => !v)} inject={inject} onInject={() => setInject((v) => !v)}
        evidence={evidence} onEvidence={() => setEvidence((v) => !v)} />
      <FeedBanner />
      <TruthBanner />
      <EvalBanner />
      <ExerciseBanner />
      <AlertStrip />
      <Digest />
      <main>
        <div className="chart-wrap">
          <Chart satellite={sat} onSatelliteState={onSatState} />
          <CoverageBox />
          <EventLog />
          {inject && <InjectPanel onClose={() => setInject(false)} />}
          {evidence && <EvidencePanel onClose={() => setEvidence(false)} />}
        </div>
        <FleetPanel />
      </main>
      <DecisionDock />
    </div>
  );
}
