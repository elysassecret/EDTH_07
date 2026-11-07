// Owner: C. U2 "Since you last looked": after an Acknowledge, or after 2 minutes with no
// mouse or key input, one strip shows up to five narrator lines (server/narrator.py, shore data
// only) newer than the officer's last look. "Got it" marks now as the last look.
import { useEffect, useRef } from "react";
import { useStore } from "../store";
import { utc } from "../format";
import { t0Of } from "../types";

const IDLE_MS = 120_000; // wall-clock idle before the digest opens (UI timing only)
const MAX_LINES = 5;

export function Digest() {
  const snap = useStore((s) => s.snap);
  const open = useStore((s) => s.digestOpen);
  const since = useStore((s) => s.lastLookT);
  const setDigest = useStore((s) => s.setDigest);
  const idleTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    const arm = () => {
      window.clearTimeout(idleTimer.current);
      idleTimer.current = window.setTimeout(() => setDigest(true), IDLE_MS);
    };
    const events = ["mousemove", "keydown", "pointerdown", "wheel"];
    for (const e of events) window.addEventListener(e, arm, { passive: true });
    arm();
    return () => {
      window.clearTimeout(idleTimer.current);
      for (const e of events) window.removeEventListener(e, arm);
    };
  }, [setDigest]);

  if (!snap || !open) return null;
  const lines = (snap.narration ?? []).filter((n) => since === null || n.t > since);
  const shown = lines.slice(-MAX_LINES).reverse();
  const t0 = t0Of(snap);
  return (
    <div className="digest" role="status">
      <span className="digest-head">
        Since you last looked{since !== null ? ` (${utc(t0, since)})` : ""}:
      </span>
      {shown.length === 0 ? <span className="muted">nothing has changed.</span> : (
        <ul>{shown.map((n, i) => <li key={`${n.t}-${i}`}><span className="at">{utc(t0, n.t)}</span> {n.text}</li>)}</ul>
      )}
      {lines.length > MAX_LINES && <span className="muted">+{lines.length - MAX_LINES} more under "What changed"</span>}
      <button onClick={() => setDigest(false, snap.t)}>Got it</button>
    </div>
  );
}
