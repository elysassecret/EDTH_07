"""Three-mode baseline and headline metric (feature 12, BUILD_PLAN M7b). Owner: D.

    uv run python -m eval.run_batch                       # static, off, elysa x seeds 1-5
    uv run python -m eval.run_batch --seeds 1 2 --jobs 4 --out runs/batch.json

Modes differ in one key, `policy` (config/agent.toml): `static` boats hold station from
t = 0 and never bid; `off` stops all bidding at the first scripted failure T; `elysa` keeps
repairing. Headline: cable km overdue at evaluate_s against revisit_target_s, as median and
range over seeds. Exit code 1 when a fairness or gap check fails.
"""

import argparse
import hashlib
import itertools
import json
import statistics
import tomllib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

from agent.core import Agent
from agent.shore import ShoreNode
from eval.gap import GapAudit
from eval.metrics import Window, world_coverage
from world.check import config_hash
from world.sim import World

POLICIES = ("static", "off", "elysa")
CHECK_MS = 60_000  # metrics and gap audit cadence, sim time
MIN_SEEDS = 5  # F5


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run_config(root: Path) -> dict:
    with (root / "config/run.toml").open("rb") as f:
        run = tomllib.load(f)
    with (root / "config/scene.toml").open("rb") as f:
        scene = tomllib.load(f)
    return {
        "evaluate_ms": run["evaluate_s"] * 1000,
        "target_ms": run["revisit_target_s"] * 1000,
        "step_m": scene["sample_step_m"],
        "seeds": run["seeds"],
    }


def run_case(case: tuple[str, int, str, int | None]) -> dict:
    """One seeded run. `horizon_s` None runs to evaluate_s. Only sim time is recorded, so
    the result, and its digest, must be identical whenever the case is repeated."""
    root_s, seed, policy, horizon_s = case
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    root = Path(root_s)
    cfg = run_config(root)
    sim = World(root, seed=seed, agent_factory=Agent, shore_factory=ShoreNode)
    sim.params = replace(sim.params, policy=policy)
    sim.reset()
    end_ms = cfg["evaluate_ms"] if horizon_s is None else horizon_s * 1000
    if end_ms % sim.tick_ms or end_ms < 0:
        raise ValueError("horizon must be a non-negative tick boundary")
    t_fail = sim.params.repair_off_after_ms
    before_fail = max(0, t_fail - sim.tick_ms)
    window = Window(t_fail, end_ms)
    gap = GapAudit()
    ages_before_fail = None
    held: dict[int, set[str]] = {}
    claims_after_fail: list[list] = []
    cov = None
    while sim.next_tick_ms <= end_ms:
        sim.step()
        t = sim.t_ms
        if t == before_fail:
            ages_before_fail = digest(sim.sample_visit_ms)
        if t >= before_fail:
            for boat, node in sorted(sim.nodes.items()):
                now = set(node.table.held_by(boat))
                if t > before_fail:
                    claims_after_fail.extend([t // 1000, boat, k] for k in sorted(now - held[boat]))
                held[boat] = held.get(boat, set()) | now
        if t % CHECK_MS == 0 or t == end_ms:
            cov = world_coverage(sim, cfg["target_ms"], cfg["step_m"])
            window.add(cov)
            gap.add(sim.shore.picture(t).seg_age, cov)
    result = {
        "seed": seed,
        "policy": policy,
        "end_s": end_ms // 1000,
        "config_sha256": config_hash(root),
        "params": asdict(sim.params),
        "repair_off_after_s": t_fail // 1000,
        "ages_before_fail_sha256": ages_before_fail,
        "claims_after_fail": claims_after_fail,
        "coverage": cov.row(),
        "mean_km_overdue_after_fail": window.mean_km,
        "gap": gap.row(),
        "final_state_sha256": sim.state_hash(),
        "agents_sha256": digest([node.view() for _, node in sorted(sim.nodes.items())]),
    }
    result["digest"] = digest(result)
    return result


def fairness(runs: list[dict]) -> list[dict]:
    """F1-F5 from BUILD_PLAN. F2 compares off with elysa only: static holds station from
    t = 0, so its pre-failure ages differ by design."""
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    by_seed: dict[int, dict[str, dict]] = {}
    for r in runs:
        by_seed.setdefault(r["seed"], {})[r["policy"]] = r
    for seed, modes in sorted(by_seed.items()):
        rows = list(modes.values())
        check("F1", len({r["config_sha256"] for r in rows}) == 1,
              f"seed {seed}: config, event tape and scene hash equal across modes "
              "(the channel tape is drawn from the seed)")
        if "off" in modes and "elysa" in modes and modes["off"]["ages_before_fail_sha256"]:
            check("F2", modes["off"]["ages_before_fail_sha256"]
                  == modes["elysa"]["ages_before_fail_sha256"],
                  f"seed {seed}: sample ages at T-1 equal for off and elysa")
        if "off" in modes and modes["off"]["end_s"] > modes["off"]["repair_off_after_s"]:
            n = len(modes["off"]["claims_after_fail"])
            check("F3", n == 0, f"seed {seed}: off made {n} claims after T")
        keys = set()
        base = rows[0]["params"]
        for r in rows[1:]:
            keys |= {k for k in base if base[k] != r["params"][k]}
        check("F4", keys <= {"policy"}, f"seed {seed}: params differing across modes: "
              f"{sorted(keys) or 'none'}")
    n_seeds = len(by_seed)
    check("F5", n_seeds >= MIN_SEEDS, f"{n_seeds} seeds (need {MIN_SEEDS} for a headline)")
    # Seeds that all give the same coverage are one sample, not a range (BUILD_PLAN: the
    # seeds must vary the start phase as well as the radio tape).
    for policy in POLICIES:
        outcomes = {json.dumps(r["coverage"], sort_keys=True) for r in runs if r["policy"] == policy}
        if n_seeds > 1 and outcomes:
            check("F5", len(outcomes) > 1,
                  f"{policy}: {len(outcomes)} distinct coverage outcome(s) over {n_seeds} seeds")
    return checks


def summary(runs: list[dict]) -> dict:
    out = {}
    for policy in POLICIES:
        rows = [r for r in runs if r["policy"] == policy]
        if not rows:
            continue

        def spread(values):
            values = [v for v in values if v is not None]
            if not values:
                return None
            return {"median": statistics.median(values), "min": min(values), "max": max(values)}

        out[policy] = {
            "seeds": sorted(r["seed"] for r in rows),
            "km_overdue": spread([r["coverage"]["km_overdue"] for r in rows]),
            "mean_km_overdue_after_fail": spread([r["mean_km_overdue_after_fail"] for r in rows]),
            "worst_age_s": spread([r["coverage"]["worst_age_s"] for r in rows]),
            "km_never_visited": spread([r["coverage"]["km_never_visited"] for r in rows]),
            "gap_max_hidden_s": max(r["gap"]["max_hidden_s"] for r in rows),
            "gap_ok": all(r["gap"]["ok"] for r in rows),
        }
    return out


def table(report: dict) -> str:
    def fmt(s):
        if s is None:
            return "n/a"
        return f"{s['median']:g} ({s['min']:g}-{s['max']:g})"

    lines = [
        (f"Cable km overdue at t = {report['end_s']} s, target {report['target_s']} s. "
        "Median (min-max) over seeds."),
        "",
        ("| mode | seeds | km overdue | mean km overdue after T | worst age s | km never visited "
        "| console hides up to s |"),
        "|---|---|---|---|---|---|---|",
    ]
    for policy, s in report["summary"].items():
        lines.append(
            f"| {policy} | {len(s['seeds'])} | {fmt(s['km_overdue'])} "
            f"| {fmt(s['mean_km_overdue_after_fail'])} | {fmt(s['worst_age_s'])} "
            f"| {fmt(s['km_never_visited'])} | {s['gap_max_hidden_s']} |"
        )
    lines.append("")
    for c in report["checks"]:
        lines.append(f"{'PASS' if c['ok'] else 'FAIL'} {c['check']}: {c['detail']}")
    for policy, s in report["summary"].items():
        lines.append(f"{'PASS' if s['gap_ok'] else 'FAIL'} gap visible ({policy}): console "
                     f"shows segments up to {s['gap_max_hidden_s']} s fresher than truth")
    if not report["headline_ok"]:
        lines.append("PRELIMINARY: not a headline number until every check passes.")
    return "\n".join(lines)


def batch(root: Path, seeds: list[int], policies: list[str], horizon_s: int | None,
          jobs: int = 1) -> dict:
    cases = [(str(root.resolve()), seed, policy, horizon_s)
             for seed, policy in itertools.product(seeds, policies)]
    if jobs == 1:
        runs = [run_case(c) for c in cases]
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            runs = list(pool.map(run_case, cases))
    cfg = run_config(root)
    checks = fairness(runs)
    summ = summary(runs)
    return {
        "end_s": runs[0]["end_s"] if runs else None,
        "target_s": cfg["target_ms"] // 1000,
        "limitations": [
            "cold start: every sample is aged from t = 0; no warm_state.json yet",
            "World.reset does not vary the start phase by seed; seeds vary the radio channel only",
            "lane crossings in view (second headline number) needs the private AIS replay",
        ],
        "checks": checks,
        "summary": summ,
        "headline_ok": all(c["ok"] for c in checks) and all(s["gap_ok"] for s in summ.values()),
        "runs": runs,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--seeds", nargs="+", type=int)
    parser.add_argument("--modes", nargs="+", choices=POLICIES, default=list(POLICIES))
    parser.add_argument("--horizon-s", type=int, help="default: evaluate_s from config/run.toml")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--out", type=Path, help="write the full JSON report here (runs/ is gitignored)")
    args = parser.parse_args(argv)
    seeds = args.seeds or run_config(args.root)["seeds"]
    report = batch(args.root, seeds, args.modes, args.horizon_s, args.jobs)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1, sort_keys=True))
    print(table(report))
    return 0 if report["headline_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
