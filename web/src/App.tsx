// Owner: C. Page layout: top bar, banners, chart, fleet panel.
import { useCallback, useState } from "react";
import { Chart } from "./map/Chart";
import { useStore } from "./store";
import { dur, hm, utc } from "./format";
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
        {snap ? <>sim {dur(snap.t)} · warp {snap.speed}× · {snap.source === "mock" ? "MOCK FEED" : snap.source}</> : "waiting for feed"}
      </div>
      <div className="controls">
        <button onClick={() => setChannel(channel === "shore" ? "truth" : "shore")} className={channel === "truth" ? "on" : ""}>
          {channel === "shore" ? "View: SHORE (delivered)" : "View: TRUTH (evaluator)"}
        </button>
        <button onClick={onSat} disabled={satState !== "ready"} className={sat ? "on" : ""}
          title={satState === "none" ? "web/public/geo/s2_box.png not supplied yet" : ""}>
          {satState === "ready" ? (sat ? "Satellite ON" : "Satellite OFF") : satState === "none" ? "No satellite image yet" : "Satellite…"}
        </button>
      </div>
    </header>
  );
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

function FleetPanel() {
  const snap = useStore((s) => s.snap);
  if (!snap) return <aside className="panel" />;
  return (
    <aside className="panel">
      <h2>Fleet</h2>
      {snap.boats.map((b) => (
        <div key={b.id} className="row">
          <span className="id">USV {String(b.id).padStart(2, "0")}</span>
          <span className={`chip mode-${b.mode}`}>{b.mode}</span>
          <span className="role">{b.role_text ?? b.roles.join(", ")}</span>
          <span className="small">
            {hm(b.endurance_s)} · link {b.link}
            {b.heard === false ? " · NEVER HEARD" : snap.t - b.last_heard > 1 ? ` · LAST SEEN ${dur(snap.t - b.last_heard)} AGO` : ""}
          </span>
        </div>
      ))}
    </aside>
  );
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
      <main>
        <Chart satellite={sat} onSatelliteState={onSatState} />
        <FleetPanel />
      </main>
    </div>
  );
}
