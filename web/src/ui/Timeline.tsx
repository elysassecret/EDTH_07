// Owner: C. Replay timeline, like a live video stream: the simulation always keeps running.
// Drag back (or click a mark) to watch the shore picture as it was; press Play to play the
// recording forward at the chosen speed; the far right, or Go live, is now. Playback only shows
// what was recorded (server/feed.py History): it never runs the simulation or makes new data.
import { useEffect, useRef, useState } from "react";
import { Radio } from "lucide-react";
import { Button } from "@/components/ui/button";
import { dur, utc } from "../format";
import { apiUrl, useStore } from "../store";
import { t0Of, type Snapshot } from "../types";

const LIVE_SNAP_S = 45; // released (or played) to within this of now counts as live
const TICK_MS = 100; // playback clock step
interface Mark { t: number; text: string; kind: string; exercise: boolean }

export function ReplayBar() {
  const live = useStore((s) => s.live);
  const replayT = useStore((s) => s.replayT);
  const showReplay = useStore((s) => s.showReplay);
  const playing = useStore((s) => s.replayPlaying);
  const speed = useStore((s) => s.replaySpeed);
  const setPlaying = useStore((s) => s.setReplayPlaying);
  const channel = useStore((s) => s.channel);
  const conn = useStore((s) => s.conn);
  const [from, setFrom] = useState<number | null>(null);
  const [marks, setMarks] = useState<Mark[]>([]);
  const [drag, setDrag] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ticket = useRef(0);
  const pos = useRef<number | null>(null); // playback position, sim s
  const buffer = useRef<Snapshot[]>([]); // recorded frames ahead of pos, oldest first
  const loading = useRef(false);

  // the recording's start and its event marks; refreshed every 10 s and after a reset
  const seed = live?.seed;
  useEffect(() => {
    if (conn !== "live") return;
    const get = () =>
      fetch(apiUrl("/api/history"))
        .then((r) => (r.ok ? r.json() : null))
        .then((h) => {
          setFrom(h?.from ?? 0);
          setMarks(h?.marks ?? []);
        })
        .catch(() => setFrom(0));
    get();
    const id = window.setInterval(get, 10_000);
    return () => window.clearInterval(id);
  }, [conn, seed]);

  // playback: advance a clock at `speed` sim-s per real second and show the newest recorded
  // frame at or before it, fetching frames ahead in batches
  useEffect(() => {
    if (!playing) return;
    pos.current = useStore.getState().replayT;
    buffer.current = [];
    const fill = () => {
      if (loading.current || pos.current === null) return;
      const last = buffer.current.at(-1)?.t ?? pos.current;
      if (last - pos.current > Math.max(30, speed * 5)) return; // enough ahead
      loading.current = true;
      const to = last + Math.max(120, speed * 20);
      fetch(apiUrl(`/api/frames?from=${Math.floor(last)}&to=${Math.ceil(to)}`))
        .then((r) => (r.ok ? (r.json() as Promise<Snapshot[]>) : []))
        .then((frames) => {
          const newer = frames.filter((f) => f.t > (buffer.current.at(-1)?.t ?? -1));
          buffer.current.push(...newer);
        })
        .finally(() => (loading.current = false));
    };
    fill();
    const id = window.setInterval(() => {
      const st = useStore.getState();
      if (pos.current === null || !st.live) return;
      pos.current += (speed * TICK_MS) / 1000;
      if (st.live.t - pos.current <= LIVE_SNAP_S) {
        st.showReplay(null); // caught up with the live run
        return;
      }
      let shown: Snapshot | undefined;
      while (buffer.current.length && buffer.current[0].t <= pos.current) shown = buffer.current.shift();
      if (shown) st.showReplay(shown);
      fill();
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, [playing, speed]);

  if (!live || channel !== "shore") return null;
  const now = live.t;
  const start = Math.min(from ?? 0, now);
  const value = drag ?? replayT ?? now;
  const watchingLive = replayT === null && drag === null;
  const span = Math.max(now - start, 1);

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
      <div className="relative min-w-0 flex-1">
        <input
          type="range"
          aria-label="Replay position"
          aria-valuetext={watchingLive ? "live" : `${utc(t0Of(live), value)}, ${dur(now - value)} behind live`}
          className="relative z-10 h-1.5 w-full cursor-pointer accent-red-500"
          min={start}
          max={Math.max(now, start + 1)}
          step={1}
          value={value}
          onChange={(e) => {
            setPlaying(false);
            setDrag(Number(e.target.value));
          }}
          onPointerUp={(e) => load(Number((e.target as HTMLInputElement).value))}
          onKeyUp={(e) => load(Number((e.target as HTMLInputElement).value))}
        />
        {/* event marks: what happened when; click one to watch from just before it */}
        <div className="pointer-events-none absolute inset-x-0 -bottom-1.5 h-1.5" aria-hidden="false">
          {marks
            .filter((m) => m.t >= start && m.t <= now)
            .map((m, i) => (
              <button
                key={`${m.t}-${i}`}
                type="button"
                aria-label={`Replay from ${utc(t0Of(live), m.t)}: ${m.text}`}
                title={`${utc(t0Of(live), m.t)} · ${m.text}`}
                className={`pointer-events-auto absolute h-1.5 w-1 -translate-x-1/2 rounded-sm ${m.exercise ? "bg-amber-400" : "bg-muted-foreground/60"} hover:scale-150`}
                style={{ left: `${((m.t - start) / span) * 100}%` }}
                onClick={() => {
                  setPlaying(false);
                  load(Math.max(start, m.t - 30));
                }}
              />
            ))}
        </div>
      </div>
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

/** Stepless speed: any value from 0.25x to 999x, typed or dragged (log scale), or Auto (live
 * only). In replay it sets the playback speed; live, it sets the simulation's warp. */
export function SpeedControl({
  value,
  auto,
  disabled,
  onChange,
  allowAuto,
}: {
  value: number;
  auto: boolean;
  disabled?: boolean;
  onChange: (v: number | "auto") => void;
  allowAuto: boolean;
}) {
  const [text, setText] = useState(String(value));
  useEffect(() => setText(auto ? "" : String(value)), [value, auto]);
  const lo = Math.log(0.25), hi = Math.log(999);
  const toSlider = (v: number) => Math.round(((Math.log(v) - lo) / (hi - lo)) * 1000);
  const fromSlider = (s: number) => Math.round(Math.exp(lo + (s / 1000) * (hi - lo)) * 100) / 100;
  const commit = (raw: string) => {
    const v = Number(raw);
    if (!Number.isFinite(v) || v < 0.25 || v > 999) {
      setText(auto ? "" : String(value));
      return;
    }
    onChange(v);
  };
  return (
    <div className="flex items-center gap-1" role="group" aria-label="Simulation speed">
      {allowAuto && (
        <Button
          variant={auto ? "default" : "outline"}
          size="sm"
          disabled={disabled}
          aria-pressed={auto}
          onClick={() => onChange("auto")}
          title="Auto: fast between events, slow around them"
        >
          Auto
        </Button>
      )}
      <input
        type="range"
        aria-label="Speed"
        className="hidden w-24 accent-primary xl:block"
        min={0}
        max={1000}
        disabled={disabled}
        value={toSlider(auto ? value || 1 : value)}
        onChange={(e) => setText(String(fromSlider(Number(e.target.value))))}
        onPointerUp={(e) => commit(String(fromSlider(Number((e.target as HTMLInputElement).value))))}
        onKeyUp={(e) => commit(String(fromSlider(Number((e.target as HTMLInputElement).value))))}
      />
      <label className="flex items-center rounded-md border px-1.5">
        <input
          aria-label="Speed factor"
          inputMode="decimal"
          className="w-14 bg-transparent py-1 text-right text-sm tabular-nums outline-none"
          disabled={disabled}
          placeholder={auto ? `${value}` : ""}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => text !== "" && commit(text)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commit(text);
          }}
        />
        <span className="text-sm text-muted-foreground">×</span>
      </label>
    </div>
  );
}
