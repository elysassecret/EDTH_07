// Owner: C. Page layout: top bar, banners, chart, fleet panel.
import { useCallback, useState } from "react";
import { Chart } from "./map/Chart";
import { useStore } from "./store";
import { dur, utc } from "./format";
import { FleetPanel } from "./ui/BoatCard";
import { AlertStrip } from "./ui/AlertPanel";
import { t0Of } from "./types";

function TopBar({ sat, satState, onSat }: { sat: boolean; satState: "none" | "ready" | "checking"; onSat: () => void }) {
  const snap = useStore((s) => s.snap);
  const channel = useStore((s) => s.channel);
  const setChannel = useStore((s) => s.setChannel);
  return (
    <header className="topbar">
      <div className="title">Shore console · Great Belt cable watch</div>
      <div className="clock">{snap ? utc(t0Of(snap), snap.t) : "--:--:--Z"}</div>
      <div className="meta">
        {snap ? <>sim {dur(snap.t)} · {snap.speed === 0 ? "PAUSED" : `warp ${snap.speed}×`} · {snap.source === "mock" ? "MOCK FEED" : snap.source}</> : "waiting for feed"}
      </div>
      <div className="controls">
        <button onClick={() => setChannel(channel === "shore" ? "truth" : "shore")} className={channel === "truth" ? "on" : ""}>
          {channel === "shore" ? "View: SHORE (delivered)" : "View: TRUTH (evaluator)"}
        </button>
        <CommsToggle />
        <button onClick={onSat} disabled={satState !== "ready"} className={sat ? "on" : ""}
          title={satState === "none" ? "web/public/geo/s2_box.png not supplied yet" : ""}>
          {satState === "ready" ? (sat ? "Satellite ON" : "Satellite OFF") : satState === "none" ? "No satellite image yet" : "Satellite…"}
        </button>
      </div>
    </header>
  );
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
  return (
    <div className="app">
      <TopBar sat={sat} satState={satState} onSat={() => setSat((v) => !v)} />
      <FeedBanner />
      <TruthBanner />
      <AlertStrip />
      <main>
        <Chart satellite={sat} onSatelliteState={onSatState} />
        <FleetPanel />
      </main>
    </div>
  );
}
