// Owner: C. Feature 28: one-click incident report and the tamper demo.
// Both come from the server (evidence/report.py) and need the real sim with its run log.
// The report shows that records were not changed after they were written; it does not show
// that a sensor was right, and it makes no admissibility claim.
import { useState } from "react";
import { apiUrl, useStore } from "../store";

interface Tamper {
  ok: boolean; error?: string; changed?: string;
  original?: { ok: boolean; messages: string[] }; tampered?: { ok: boolean; messages: string[] };
}

export function EvidencePanel({ onClose }: { onClose: () => void }) {
  const snap = useStore((s) => s.snap);
  const [demo, setDemo] = useState<Tamper | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const t = Math.floor(snap?.t ?? 0);
  const lastHalfHour = `/api/report.md?from=${Math.max(0, t - 1800)}&to=${t}`;

  const runDemo = async () => {
    setBusy(true); setErr(null); setDemo(null);
    try {
      const r = await fetch(apiUrl("/api/tamper-demo"));
      if (!r.ok) throw new Error((await r.text()).trim());
      setDemo((await r.json()) as Tamper);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="inject evidence" role="dialog" aria-label="Evidence">
      <div className="inject-head">
        Evidence log
        <button className="close" onClick={onClose} aria-label="Close">×</button>
      </div>
      <div className="row">
        <a className="btn" href={apiUrl(lastHalfHour)} download>Incident report: last 30 min</a>
        <a className="btn" href={apiUrl("/api/report.md")} download>Whole run</a>
      </div>
      <button disabled={busy} onClick={runDemo}>{busy ? "Checking…" : "Tamper demo: change one character"}</button>
      {err && <div className="warn small">{err}</div>}
      {demo && !demo.ok && <div className="warn small">{demo.error}</div>}
      {demo?.ok && (
        <div className="small">
          <div>Original: {demo.original?.messages.join(" ")}</div>
          <div>Changed in a copy: {demo.changed}</div>
          <div className={demo.tampered?.ok ? "" : "warn"}>Check on the copy: {demo.tampered?.messages.join(" ")}</div>
        </div>
      )}
      <div className="muted small">Shows whether a record was changed after it was written, not that a sensor was right. Real sim with run log only.</div>
    </div>
  );
}
