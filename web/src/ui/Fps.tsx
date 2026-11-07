// Owner: C. G4 / N4: a small frame-rate readout, shown only in the evaluator view.
// "screen" = browser frames per second (requestAnimationFrame); "feed" = snapshots per second
// received from the server. Measured live, nothing assumed.
import { useEffect, useRef, useState } from "react";
import { useStore } from "../store";

export function Fps() {
  const [fps, setFps] = useState<{ screen: number; feed: number } | null>(null);
  const raf = useRef(0);
  const feed = useRef(0);
  useEffect(() => {
    let frames = 0;
    let last = performance.now();
    let id = 0;
    const loop = () => {
      frames += 1;
      id = requestAnimationFrame(loop);
    };
    id = requestAnimationFrame(loop);
    const unsub = useStore.subscribe((s, prev) => { if (s.snap !== prev.snap) feed.current += 1; });
    const timer = window.setInterval(() => {
      const now = performance.now();
      const dt = (now - last) / 1000;
      setFps({ screen: Math.round(frames / dt), feed: Math.round((feed.current / dt) * 10) / 10 });
      frames = 0;
      feed.current = 0;
      last = now;
    }, 2000);
    raf.current = id;
    return () => { cancelAnimationFrame(id); window.clearInterval(timer); unsub(); };
  }, []);
  if (!fps) return <span className="fps muted">measuring…</span>;
  const n = useStore.getState().snap?.contacts.length ?? 0;
  return <span className="fps">screen {fps.screen} fps · feed {fps.feed} frames/s · {n} contacts</span>;
}
