"""One-click incident report and tamper demo. Owner: C. Feature 28 (second half).

    uv run python -m evidence.report runs/<run>.jsonl [--from 7000 --to 9600]

Builds the evidence log for the run (evidence/build.py), verifies it, and writes a Markdown
report for a sim-time window: run identity, chain check, timeline of what the shore received
and decided, decisions with who answered, last reported boat positions, contacts observed, and
what the report cannot show. Built from shore data only.

tamper_demo() changes one character of one record in a copy of the evidence log and verifies
the copy, so the console can show the check naming the changed record.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from evidence.build import NOTE, build
from evidence.verify import verify
from server.feed import ROOT

DEFAULT_KEY = ROOT / "runs" / "evidence-key.pem"


def _clock(t0: datetime | None, t: int | None) -> str:
    if t is None:
        return "n/a"
    return (t0 + timedelta(seconds=t)).strftime("%H:%M:%SZ") if t0 else f"t+{t} s"


def _records(evidence: Path) -> tuple[dict, list[dict]]:
    lines = [json.loads(ln) for ln in evidence.read_text(encoding="utf-8").splitlines() if ln]
    return lines[0], [r for r in lines[1:] if r.get("type") == "record"]


def _line(r: dict) -> str:
    d, k = r["data"], r["kind"]
    if k == "event":
        what = f"{d.get('kind')} " + " ".join(f"{x}={d[x]}" for x in ("a", "boat", "b") if x in d)
        return f"Exercise failure ({d.get('origin', 'scripted')}): {what.strip()}"
    if k == "command" and d["msg"].get("cmd") == "escalate":
        m = d["msg"]
        note = f" Note: {m['note']}" if m.get("note") else ""
        return (f"Watch officer escalated {m.get('id')} ({'recorded' if d['ok'] else 'rejected'})."
                f"{note} Report sent: {' / '.join(str(m.get('text', '')).splitlines())}")
    if k == "command":
        m = d["msg"]
        args = " ".join(f"{x}={m[x]}" for x in sorted(m) if x != "cmd")
        return f"Watch officer command: {m.get('cmd')} {args} ({'accepted' if d['ok'] else 'rejected'})"
    if k == "decision":
        return f"Decision {d.get('id')}: {d.get('text')} → {d.get('state')}"
    if k == "alert":
        return f"Alert {d.get('level', '').upper()}: {d.get('text')}"
    if k == "observation":
        return (f"Contact {d.get('track', d.get('id'))} reported, seen by {d.get('seen_by', [])}, "
                f"{'AIS' if d.get('ais') else 'no AIS'}")
    return f"{k}: {json.dumps(d, sort_keys=True)}"


def report(run_log: Path, key_path: Path = DEFAULT_KEY, t_from: int | None = None,
           t_to: int | None = None, out_dir: Path | None = None) -> str:
    head_line = json.loads(run_log.read_text(encoding="utf-8").splitlines()[0])
    t0 = datetime.fromisoformat(head_line["t0_utc"]) if head_line.get("t0_utc") else None
    out = (out_dir or run_log.parent) / (run_log.stem + ".evidence.jsonl")
    evidence = build(run_log, key_path, out)
    ok, msgs = verify(evidence)
    head, recs = _records(evidence)
    lo = t_from if t_from is not None else 0
    hi = t_to if t_to is not None else max((r["t_log"] for r in recs), default=0)
    inwin = [r for r in recs if lo <= r["t_log"] <= hi]
    shore = [r for r in inwin if r["chain"] == "shore"]
    boats: dict[str, dict] = {}
    for r in recs:
        if r["chain"] != "shore" and r["t_log"] <= hi:
            boats[r["chain"]] = r

    dirty = " (uncommitted changes)" if head_line.get("git_dirty") else ""
    md = [
        "# Incident report: shore console (simulation)",
        "",
        f"Window: {_clock(t0, lo)} to {_clock(t0, hi)} (sim clock; sim {lo} s to {hi} s)",
        (f"Run log: `{run_log.name}` · seed {head_line.get('seed')} · git "
         f"`{str(head_line.get('git_commit'))[:12]}`{dirty}"
         f" · config hash `{str(head_line.get('config_hash'))[:12]}`"),
        f"Evidence log: `{evidence.name}` · signing key id `{head['key_id']}`",
        f"Chain check: **{'OK' if ok else 'FAILED'}**. " + " ".join(msgs),
        "",
        f"> {NOTE} Time source for every record: simulation clock (no GNSS model).",
        "",
        "## Timeline (what the shore received and decided)",
        "",
        "| Logged (UTC) | Observed (UTC) | Record | What |",
        "|---|---|---|---|",
    ]
    md += [f"| {_clock(t0, r['t_log'])} | {_clock(t0, r['t_obs'])} | shore #{r['seq']} | "
           f"{_line(r)} |" for r in shore] or ["| | | | Nothing in this window. |"]
    decided = [r for r in shore if r["kind"] in ("decision", "command")]
    md += ["", "## Decisions and who answered", ""]
    md += [f"- {_clock(t0, r['t_log'])}: {_line(r)} · by: {r['source']}" for r in decided] or [
        "- None in this window."]
    md += ["", "## Last report from each USV in the window", "",
           "| USV | Reported (UTC) | Position (lat, lon) | Mode | Link | Zone |", "|---|---|---|---|---|---|"]
    for name, r in sorted(boats.items()):
        d = r["data"]
        md.append(f"| {name.replace("usv-", "USV ")} | {_clock(t0, r['t_obs'])} | {d['lat']:.5f}, {d['lon']:.5f} | "
                  f"{d['mode']} | {d['link']} | {'; '.join(r['zone'])} |")
    md += ["", "## What this report cannot show", "",
           ("- Whether a sensor or a report was right: the chain shows only that records were "
            "not changed after they were written."),
           "- Anything the shore did not receive. Boats out of contact appear with their last report.",
           "- Boat-side signatures: boats do not sign their own records yet (needs `agent/`).",
           ("- The watch officer's name: the demo has no login; commands are logged as "
            "\"watch officer\"."),
           "", "No claim on admissibility. A synthetic exercise, not a real incident."]
    return "\n".join(md) + "\n"


def tamper_demo(run_log: Path, key_path: Path = DEFAULT_KEY) -> dict:
    """Build + verify the evidence, then change one character of one report in a copy."""
    with tempfile.TemporaryDirectory() as d:
        evidence = build(run_log, key_path, Path(d) / "evidence.jsonl")
        ok, msgs = verify(evidence)
        lines = evidence.read_text(encoding="utf-8").splitlines()
        reports = [i for i, ln in enumerate(lines) if '"kind": "report"' in ln]
        if not reports:
            return {"ok": False, "error": "no boat reports in the run yet"}
        i = reports[len(reports) // 2]
        rec = json.loads(lines[i])
        before = rec["data"]["batt"]
        rec["data"]["batt"] = before + 1 if before < 1000 else before - 1
        lines[i] = json.dumps(rec, sort_keys=True)
        copy = Path(d) / "tampered.jsonl"
        copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok2, msgs2 = verify(copy)
        return {"ok": True, "original": {"ok": ok, "messages": msgs},
                "changed": f"{rec['chain']} record {rec['seq']}: battery {before} → "
                           f"{rec['data']['batt']} (one character)",
                "tampered": {"ok": ok2, "messages": msgs2}}


def main() -> None:
    ap = argparse.ArgumentParser(description="Incident report (Markdown) for a run log.")
    ap.add_argument("run_log", type=Path)
    ap.add_argument("--from", dest="t_from", type=int, help="window start, sim seconds")
    ap.add_argument("--to", dest="t_to", type=int, help="window end, sim seconds")
    ap.add_argument("--key", type=Path, default=DEFAULT_KEY)
    args = ap.parse_args()
    text = report(args.run_log, args.key, args.t_from, args.t_to)
    out = args.run_log.with_name(args.run_log.stem + ".report.md")
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

