// Owner: C. Replay timeline, like a live video stream: the simulation always keeps running.
// Drag back to watch the shore picture as it was (frames the server recorded every 30 sim-s);
// the far right, or Live, is now. Replay only looks: commands are off while you watch it.
import { useEffect, useRef, useState } from "react";
import { Radio } from "lucide-react";
import { Button } from "@/components/ui/button";
import { dur, utc } from "../format";
import { apiUrl, useStore } from "../store";
import { t0Of, type Snapshot } from "../types";

const LIVE_SNAP_S = 45; // released within this of now counts as live

export function ReplayBar() {
  const live = useStore((s) => s.live);
  const replayT = useStore((s) => s.replayT);
  const showReplay = useStore((s) => s.showReplay);
  const channel = useStore((s) => s.channel);
  const conn = useStore((s) => s.conn);
  const [from, setFrom] = useState<number | null>(null);
  const [drag, setDrag] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ticket = useRef(0);

  // the recording starts at the run's first state; learn it again after a reset (new seed or t)
  const seed = live?.seed;
  useEffect(() => {
    if (conn !== "live") return;
    fetch(apiUrl("/api/history"))
      .then((r) => (r.ok ? r.json() : null))
      .then((h) => setFrom(h?.from ?? 0))
      .catch(() => setFrom(0));
  }, [conn, seed]);

  if (!live || channel !== "shore") return null;
  const now = live.t;
  const start = Math.min(from ?? 0, now);
  const value = drag ?? replayT ?? now;
  const watchingLive = replayT === null && drag === null;

  const load = (t: number) => {
    setDrag(null);
    if (now - t <= LIVE_SNAP_S) {
      showReplay(null);
      return;
    }
    const mine = ++ticket.current;
    fetch(apiUrl(`/api/frame?t=${Math.round(t)}`))
      .then((r) => (r.ok ? (r.json() as Promise<Snapshot>) : Promise.reject(new Error(String(r.status)))))
      .then((frame) => {
        if (mine !== ticket.current) return; // a newer drag won
        setError(null);
        showReplay(frame);
      })
      .catch(() => setError("No recording for that moment"));
  };

  return (
    <div className="flex shrink-0 items-center gap-3 border-b px-3 py-1.5 text-sm" role="group" aria-label="Replay timeline">
      <span className="shrink-0 tabular-nums text-muted-foreground" title="Start of this run">
        {utc(t0Of(live), start)}
      </span>
      <input
        type="range"
        aria-label="Replay position"
        aria-valuetext={watchingLive ? "live" : `${utc(t0Of(live), value)}, ${dur(now - value)} behind live`}
        className="h-1.5 min-w-0 flex-1 cursor-pointer accent-red-500"
        min={start}
        max={Math.max(now, start + 1)}
        step={1}
        value={value}
        onChange={(e) => setDrag(Number(e.target.value))}
        onPointerUp={(e) => load(Number((e.target as HTMLInputElement).value))}
        onKeyUp={(e) => load(Number((e.target as HTMLInputElement).value))}
      />
      <span className="shrink-0 tabular-nums">
        {watchingLive ? (
          <span className="text-muted-foreground">{utc(t0Of(live), now)}</span>
        ) : (
          <span>
            {utc(t0Of(live), value)} · <span className="text-muted-foreground">{dur(now - value)} behind live</span>
          </span>
        )}
      </span>
      {error && <span role="alert" className="text-destructive">{error}</span>}
      <Button
        variant={watchingLive ? "outline" : "default"}
        size="sm"
        aria-pressed={watchingLive}
        aria-label={watchingLive ? "Watching live" : "Go live"}
        title={watchingLive ? "You are watching the live picture" : "Back to the live picture"}
        onClick={() => {
          setDrag(null);
          ticket.current++;
          showReplay(null);
        }}
        className={watchingLive ? "border-red-500/60" : "bg-red-600 text-white hover:bg-red-700"}
      >
        <Radio className={watchingLive ? "text-red-500" : ""} />
        {watchingLive ? "LIVE" : "Go live"}
      </Button>
    </div>
  );
}
