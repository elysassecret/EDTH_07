"""Scorecard table: median and range over seeds, per mode. Never a single-seed headline.

python -m eval.report runs/<hash>/scorecards.json
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROWS = [
    ("cable_km_overdue", "Cable km overdue at end (headline)", "{:.1f}"),
    ("lane_crossings_in_view", "Lane crossings in view after T (cost)", "{:.0f}"),
    ("lane_crossings_post_event", "Lane crossings after T (total)", "{:.0f}"),
    ("worst_age_s", "Worst revisit age at end (s)", "{:.0f}"),
    ("worst_age_post_event_s", "Worst revisit age after T (s)", "{:.0f}"),
    ("time_to_all_segs_owned_s", "Event to all cable segments owned (s)", "{:.0f}"),
    ("operator_actions", "Operator actions", "{:.0f}"),
    ("repair_claims_after_T", "Repair claims after T", "{:.0f}"),
    ("claims", "Claims total", "{:.0f}"),
]


def _vals(results, mode, key):
    out = []
    for r in results:
        if r["mode"] != mode:
            continue
        v = r.get(key)
        if isinstance(v, dict):
            v = min(v.values()) if v else None
        if v is not None:
            out.append(float(v))
    return out


def fmt_stat(vals, fmt):
    if not vals:
        return "n/a"
    med = statistics.median(vals)
    if len(vals) == 1:
        return fmt.format(med)
    return f"{fmt.format(med)} ({fmt.format(min(vals))} to {fmt.format(max(vals))})"


def table(results) -> str:
    modes = []
    for r in results:
        if r["mode"] not in modes:
            modes.append(r["mode"])
    lines = ["| Metric | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
    for key, label, fmt in ROWS:
        lines.append(f"| {label} | " + " | ".join(fmt_stat(_vals(results, m, key), fmt) for m in modes) + " |")
    det = {}
    for r in results:
        for cid, v in r.get("detect_s", {}).items():
            det.setdefault((r["mode"], cid), []).append(v)
    for (m, cid), vals in sorted(det.items()):
        lines.append(f"| Loiter start to detection, {cid}, {m} (s) | " + fmt_stat(vals, "{:.0f}") + " |")
    iv = {}
    for r in results:
        for cid, v in r.get("in_view_s", {}).items():
            iv.setdefault((r["mode"], cid), []).append(v)
    for (m, cid), vals in sorted(iv.items()):
        lines.append(f"| Loiter start to shadow in view, {cid}, {m} (s) | " + fmt_stat(vals, "{:.0f}") + " |")
    n = {m: sum(1 for r in results if r["mode"] == m) for m in modes}
    lines.append("| Seeds | " + " | ".join(str(n[m]) for m in modes) + " |")
    return "\n".join(lines)


def print_report(results, out_dir: Path | None = None) -> None:
    txt = table(results)
    print(txt)
    if out_dir is not None:
        (out_dir / "scorecard.md").write_text(
            "# Scorecard\n\nMedian (min to max) over seeds. Same warm state, event tape and channel tape per seed.\n\n"
            + txt + "\n", encoding="utf-8")


def main(argv=None):
    argv = argv or sys.argv[1:]
    p = Path(argv[0]) if argv else None
    results = json.loads(p.read_text(encoding="utf-8"))
    print_report(results, p.parent)


if __name__ == "__main__":
    main()
