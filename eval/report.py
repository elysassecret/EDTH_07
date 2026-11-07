"""Scorecard: median and range over seeds, per mode. Never a single-seed headline. Owner: D.

Every number is evaluator truth, in mission seconds. A value a run did not reach stays None:
it is counted in the row ("reached in k of n seeds"), never replaced by a number.
"""

import json
import statistics
from pathlib import Path

MIN_SEEDS = 5
CONSOLE_ROWS = [
    ("cable_km_overdue", "Cable km overdue at end (truth)", "km"),
    ("never_visited_km", "Cable km never visited (truth)", "km"),
    ("worst_age_s", "Worst sample age at end (truth)", "s"),
]
ROWS = [
    ("cable_km_overdue", "Cable km overdue at end (headline)", "{:.1f}"),
    ("never_visited_km", "Cable km never visited (separate from overdue)", "{:.1f}"),
    ("overdue_or_never_km", "Overdue plus never visited", "{:.1f}"),
    ("mean_km_overdue_post_T", "Mean km overdue from T to end", "{:.1f}"),
    ("worst_age_s", "Worst sample age at end (s)", "{:.0f}"),
    ("worst_age_post_T_s", "Worst sample age, T to end (s)", "{:.0f}"),
    ("crossings_in_view", "Real cargo and tanker crossings in view after T", "{:.0f}"),
    ("crossings_after_T", "Real cargo and tanker crossings after T", "{:.0f}"),
    ("time_to_all_segs_owned_s", "T to all segments owned by a live boat (s)", "{:.0f}"),
    ("segs_unowned_at_end", "Segments with no live owner at end", "{:.0f}"),
    ("repair_claims_after_T", "Claims after T", "{:.0f}"),
    ("unserved_task_s_post_T", "Unserved task-seconds, T to end (no live owner)", "{:.0f}"),
    ("reserve_violation_s", "Reserve violations: boat-seconds at sea under reserve", "{:.0f}"),
    ("operator_actions", "Operator actions (batch has no operator)", "{:.0f}"),
]
PAIRED_ROWS = [
    ("cable_km_overdue", "Cable km overdue at end", "{:.1f}", -1),
    ("mean_km_overdue_post_T", "Mean km overdue, T to end", "{:.1f}", -1),
    ("worst_age_s", "Worst sample age at end (s)", "{:.0f}", -1),
    ("crossings_in_view", "Real cargo and tanker crossings in view after T", "{:.0f}", +1),
    ("unserved_task_s_post_T", "Unserved task-seconds, T to end", "{:.0f}", -1),
    ("reserve_violation_s", "Reserve violation boat-seconds", "{:.0f}", -1),
]
OUTCOMES = ("all tasks", "cables only", "not recovered")
SUMMARY_KEYS = [k for k, _, _ in ROWS] + ["detect_s", "watcher_in_view_s"]
CONTACT_ROWS = [
    ("detect_s", "Contact start to first detection, {c} (s)"),
    ("watcher_in_view_s", "Contact start to watcher in view, {c} (s)"),
    ("contact_in_view_total_s", "Seconds a live boat had {c} in view"),
]


def fmt_stat(values, fmt: str) -> str:
    got = [float(v) for v in values if v is not None]
    if not got:
        return "not reached"
    med = fmt.format(statistics.median(got))
    text = med if len(got) == 1 else f"{med} ({fmt.format(min(got))} to {fmt.format(max(got))})"
    return text if len(got) == len(values) else f"{text}, reached in {len(got)} of {len(values)}"


def table(cards: list[dict]) -> str:
    modes = list(dict.fromkeys(c["mode"] for c in cards))
    per = {m: [c for c in cards if c["mode"] == m] for m in modes}
    lines = ["| Metric (truth) | " + " | ".join(modes) + " |", "|---|" + "---|" * len(modes)]
    for key, label, fmt in ROWS:
        if key.startswith("crossings") and not any(c.get("ais_present") for c in cards):
            lines.append(f"| {label} | " + " | ".join(["AIS clip not present"] * len(modes)) + " |")
            continue
        lines.append(
            f"| {label} | " + " | ".join(fmt_stat([c.get(key) for c in per[m]], fmt) for m in modes)
            + " |"
        )
    lines.append("| Recovery outcome at end (seeds) | "
                 + " | ".join(outcome_text(per[m]) for m in modes) + " |")
    unserved = [", ".join(f"{k} {fmt_stat([c.get('unserved_s_by_kind', {}).get(k, 0) for c in per[m]],
                                               '{:.0f}')}"
                          for k in kinds(cards)) or "none" for m in modes]
    lines.append("| Unserved task-seconds by kind | " + " | ".join(unserved) + " |")
    contacts = sorted({x for c in cards for x in c["contacts"]})
    for cid in contacts:
        for key, label in CONTACT_ROWS:
            cells = [fmt_stat([c[key].get(cid) for c in per[m]], "{:.0f}") for m in modes]
            lines.append(f"| {label.format(c=cid)} | " + " | ".join(cells) + " |")
        watch = [
            ", ".join(f"s{c['seed']}:{c['watchers'].get(cid) or '-'}" for c in per[m]) for m in modes
        ]
        lines.append(f"| Watchers of {cid} by seed | " + " | ".join(watch) + " |")
    if all("gap" in c for c in cards):
        cells = [str(max(c["gap"]["max_hidden_s"] for c in per[m])) for m in modes]
        lines.append("| Console shows a segment fresher than truth, up to (s) | "
                     + " | ".join(cells) + " |")
    lines.append("| Seeds | " + " | ".join(str(len(per[m])) for m in modes) + " |")
    return "\n".join(lines)


def kinds(cards: list[dict]) -> list[str]:
    return sorted({k for c in cards for k in c.get("unserved_s_by_kind", {})})


def outcomes(cards: list[dict]) -> dict[str, int]:
    return {o: sum(c.get("recovery_outcome") == o for c in cards) for o in OUTCOMES}


def outcome_text(cards: list[dict]) -> str:
    n = outcomes(cards)
    return ", ".join(f"{o} {k}" for o, k in n.items() if k) or "not measured"


def paired(cards: list[dict], a: str = "off", b: str = "elysa") -> list[dict]:
    """Seed by seed, b against a, on the seeds both modes ran. `sign` says which way is better:
    -1 lower is better (km, ages), +1 higher is better (crossings in view). A seed where either
    value is None is left out and counted. Median gain is the median of the per-seed differences,
    signed so that a positive gain is good for b."""
    by = {(c["mode"], c["seed"]): c for c in cards}
    seeds = sorted(s for m, s in by if m == a and (b, s) in by)
    rows = []
    for key, label, fmt, sign in PAIRED_ROWS:
        if key.startswith("crossings") and not any(c.get("ais_present") for c in cards):
            continue
        pairs = [(by[(a, s)].get(key), by[(b, s)].get(key)) for s in seeds]
        got = [(x, y) for x, y in pairs if x is not None and y is not None]
        diffs = [sign * (y - x) for x, y in got]
        rows.append({
            "key": key, "label": label, "fmt": fmt, "seeds": len(seeds), "compared": len(got),
            "better": sum(d > 0 for d in diffs), "equal": sum(d == 0 for d in diffs),
            "worse": sum(d < 0 for d in diffs),
            "median_gain": statistics.median(diffs) if diffs else None,
        })
    return rows


def paired_table(cards: list[dict], a: str = "off", b: str = "elysa") -> str:
    rows = paired(cards, a, b)
    if not rows or rows[0]["seeds"] == 0:
        return ""
    n = rows[0]["seeds"]
    lines = [f"## Paired, seed by seed: {b} against {a} on {n} shared seed(s)", "",
             f"| Truth | {b} better | equal | worse | median gain for {b} |", "|---|---|---|---|---|"]
    for r in rows:
        gain = "not reached" if r["median_gain"] is None else r["fmt"].format(r["median_gain"])
        note = "" if r["compared"] == n else f" (compared on {r['compared']} of {n})"
        lines.append(f"| {r['label']} | {r['better']} | {r['equal']} | {r['worse']} | {gain}{note} |")
    lines.append("")
    lines.append("Crossings in view are the evaluator's reading of the private AIS clip: the boats "
                 "never receive AIS, so a crossing 'in view' means a live boat was within camera "
                 "range at that moment, nothing more.")
    return "\n".join(lines)


def fairness(cards: list[dict]) -> list[dict]:
    """F1 warm state, F2 ages and physics at T-1, F3 off makes no claims, F4 one key differs,
    F5 enough seeds, and seeds that actually give different runs."""
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    seeds = sorted({c["seed"] for c in cards})
    for seed in seeds:
        rows = {c["mode"]: c for c in cards if c["seed"] == seed}
        check("F1", len({c["warm_hash"] for c in rows.values()}) == 1,
              f"seed {seed}: warm hash equal across {sorted(rows)}")
        if "off" in rows and "elysa" in rows:
            a, b = rows["off"], rows["elysa"]
            check("F2", a["ages_hash_T1"] == b["ages_hash_T1"]
                  and a["state_hash_T1"] == b["state_hash_T1"],
                  f"seed {seed}: ages and physical hash at T-1 equal, off vs elysa")
        if "off" in rows:
            n = rows["off"]["repair_claims_after_T"]
            check("F3", n == 0, f"seed {seed}: off made {n} claims after T")
        base = next(iter(rows.values()))["params"]
        keys = sorted({k for c in rows.values() for k in base if c["params"][k] != base[k]})
        check("F4", set(keys) <= {"policy"}, f"seed {seed}: params differing: {keys or 'none'}")
    check("F5", len(seeds) >= MIN_SEEDS, f"{len(seeds)} seeds (a headline needs {MIN_SEEDS})")
    for mode in sorted({c["mode"] for c in cards}):
        outcomes = {str(c.get("seg_age_s")) for c in cards if c["mode"] == mode}
        check("F5", len(outcomes) > 1 or len(seeds) < 2,
              f"{mode}: {len(outcomes)} distinct coverage outcome(s) over {len(seeds)} seeds")
    return checks


def headline_ok(cards: list[dict]) -> bool:
    """Numbers stay off slides until every fairness check and the console gap check pass."""
    gap = all(c.get("gap", {"ok": True})["ok"] for c in cards)
    return gap and all(c["ok"] for c in fairness(cards))


def console_scorecard(cards: list[dict], source: str = "eval/run_batch.py") -> dict:
    """The `Scorecard` shape in web/src/types.ts, for the /truth hook. Truth, never on /shore."""
    rows = []
    for mode in dict.fromkeys(c["mode"] for c in cards):
        for key, metric, unit in CONSOLE_ROWS:
            got = [c[key] for c in cards if c["mode"] == mode and c.get(key) is not None]
            if got:
                rows.append({"mode": mode, "metric": metric, "unit": unit,
                             "median": statistics.median(got), "min": min(got), "max": max(got)})
    return {
        "source": source,
        "seeds": sorted({c["seed"] for c in cards}),
        "rows": rows,
        "preliminary": not headline_ok(cards),
    }


def summary(cards: list[dict], source: str = "eval/run_batch.py") -> dict:
    """scorecard.json: per mode, median and range of every table row, the recovery outcome
    count and the seeds behind them. Truth. `preliminary` follows the same checks as the slide."""
    modes = list(dict.fromkeys(c["mode"] for c in cards))
    out = {"source": source, "label": "truth", "seeds": sorted({c["seed"] for c in cards}),
           "preliminary": not headline_ok(cards), "modes": {}}
    for m in modes:
        per = [c for c in cards if c["mode"] == m]
        stats = {}
        for key in SUMMARY_KEYS:
            vals = [c.get(key) for c in per]
            if vals and isinstance(vals[0], dict):
                continue
            got = [v for v in vals if v is not None]
            stats[key] = ({"median": statistics.median(got), "min": min(got), "max": max(got),
                           "reached": len(got), "of": len(vals)} if got else
                          {"median": None, "reached": 0, "of": len(vals)})
        out["modes"][m] = {
            "seeds": sorted(c["seed"] for c in per),
            "metrics": stats,
            "recovery_outcome": outcomes(per),
            "recovery_outcome_by_seed": {c["seed"]: c.get("recovery_outcome") for c in per},
            "reserve_violation_boats_by_seed": {c["seed"]: c.get("reserve_violation_boats")
                                                for c in per},
            "unserved_s_by_kind": {k: statistics.median(
                [c.get("unserved_s_by_kind", {}).get(k, 0) for c in per]) for k in kinds(per)},
        }
    out["paired_off_vs_elysa"] = [
        {k: r[k] for k in ("key", "seeds", "compared", "better", "equal", "worse", "median_gain")}
        for r in paired(cards)
    ]
    return out


def print_report(cards: list[dict], out: Path | None = None) -> None:
    head = (
        "# Scorecard (truth)\n\nMedian (min to max) over seeds. Mission seconds: T is the first "
        f"failure. Target {cards[0]['target_s']} s, speed {cards[0]['speed_mm_s']} mm/s, boat "
        f"radio {cards[0]['radio_boat_m']} m, evaluated at {cards[0]['t_s']} s.\n\n"
    )
    checks = "\n".join(
        f"- {'PASS' if c['ok'] else 'FAIL'} {c['check']}: {c['detail']}" for c in fairness(cards)
    )
    verdict = (
        "" if headline_ok(cards) else "\n**PRELIMINARY: not a headline until every check passes "
        "(a FAIL above, or the console gap check, issue #29).**\n"
    )
    pair = paired_table(cards)
    pair = f"\n\n{pair}" if pair else ""
    text = f"{head}{table(cards)}{pair}\n\n## Fairness\n\n{checks}\n{verdict}"
    print(text)
    if out is not None:
        (Path(out) / "scorecard.md").write_text(text, encoding="utf-8")
        (Path(out) / "scorecard.json").write_text(
            json.dumps(summary(cards), indent=1), encoding="utf-8"
        )
        (Path(out) / "scorecard_console.json").write_text(
            json.dumps(console_scorecard(cards), indent=1), encoding="utf-8"
        )
