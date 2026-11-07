"""Three-mode batch on the team world, with warm-up. Owner: D. Features 3, 12; issue #19.

    uv run python -m eval.run_batch
    uv run python -m eval.run_batch --speed 3000
    uv run python -m eval.run_batch --radio 4000
    uv run python -m eval.run_batch --modes elysa --seeds 1 --out runs/one

Writes one JSONL per run (metric row every 60 s, events, hashes, scorecard) and `scorecard.md`
into runs/<config hash>. Every number is evaluator truth. Modes differ in one key, `policy`.
Exit code 1 and the word PRELIMINARY until every fairness and console gap check passes.
"""

import argparse
import hashlib
import json
import os
import tomllib
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

from eval.ais_observer import observer_for
from eval.gap import GapAudit
from eval.metrics import Metrics
from eval.report import headline_ok, print_report
from eval.warm import WARM_S, build_world, warm_up
from world.check import config_hash

ROOT = Path(__file__).resolve().parent.parent
POLICIES = ("static", "off", "elysa")


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def run_config(root: Path) -> dict:
    with (Path(root) / "config/run.toml").open("rb") as f:
        run = tomllib.load(f)
    return {**run, "evaluate_ms": run["evaluate_s"] * 1000, "horizon_ms": run["horizon_s"] * 1000}


def batch_hash(root: Path, speed, radio, warm_s: int) -> str:
    """All config and the tape, plus anything the command line changed."""
    extra = json.dumps({"speed": speed, "radio": radio, "warm_s": warm_s}, sort_keys=True)
    return hashlib.sha256((config_hash(root) + extra).encode()).hexdigest()[:12]


def run_case(case) -> dict:
    """One seeded run: (root, seed, policy, horizon_s[, speed, radio, warm_s, out, use_ais]).

    horizon_s None runs to horizon_s from config/run.toml. Only sim time is recorded, so the
    result and its digest are identical whenever the case is repeated."""
    root_s, seed, policy, horizon_s, *rest = case
    speed, radio, warm_s, out, use_ais = (*rest, *(None, None, WARM_S, None, True)[len(rest):])
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy!r}")
    root = Path(root_s)
    cfg = run_config(root)
    world = build_world(root, policy, seed, speed, radio, warm_s)
    warm_hash = warm_up(world)
    rows: list[dict] = []
    metrics = Metrics(
        world, cfg["revisit_target_s"], t0_ms=world.warm_ms, log=rows.append, gap=GapAudit()
    )
    if use_ais:
        metrics.ais = observer_for(world, root, world.warm_ms, metrics.T, metrics.eval_t)
    end = world.warm_ms + (cfg["horizon_ms"] if horizon_s is None else horizon_s * 1000)
    while world.next_tick_ms <= end:
        world.step()
        metrics.on_tick()
    card = metrics.evaluated or metrics.scorecard()
    card["warm_hash"] = warm_hash
    card["final_hash"] = world.state_hash()
    card["agents_sha256"] = digest([node.view() for _, node in sorted(world.nodes.items())])
    card["params"] = asdict(world.final_params)
    card["config_sha256"] = digest([batch_hash(root, speed, radio, warm_s), seed])[:16]
    card["digest"] = digest(card)
    if out:
        with (Path(out) / f"{policy}_s{seed}.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps({"type": "metric", **row}, sort_keys=True) + "\n")
            f.write(json.dumps({"type": "events", "events": world.events}) + "\n")
            f.write(json.dumps({"type": "scorecard", **card}, sort_keys=True) + "\n")
    return card


def run_all(cases: list[tuple], jobs: int = 1) -> list[dict]:
    if jobs == 1:
        return [run_case(c) for c in cases]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(run_case, cases))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--modes", default=",".join(POLICIES))
    parser.add_argument("--seeds", help="comma list; default config/run.toml")
    parser.add_argument("--speed", type=int, help="boat speed in mm/s, e.g. 3000")
    parser.add_argument("--radio", type=int, help="boat radio range in m, e.g. 4000")
    parser.add_argument("--warm-s", type=int, default=WARM_S)
    parser.add_argument("--horizon-s", type=int, help="default: config/run.toml")
    parser.add_argument("--no-ais", action="store_true")
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    modes = args.modes.split(",")
    if any(m not in POLICIES for m in modes):
        parser.error(f"modes must be among {POLICIES}")
    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else run_config(root)["seeds"]
    out = args.out or root / "runs" / batch_hash(root, args.speed, args.radio, args.warm_s)
    out.mkdir(parents=True, exist_ok=True)
    cases = [
        (str(root), s, m, args.horizon_s, args.speed, args.radio, args.warm_s, str(out),
         not args.no_ais)
        for m in modes
        for s in seeds
    ]
    cards = run_all(cases, args.jobs)
    (out / "scorecards.json").write_text(json.dumps(cards, indent=1), encoding="utf-8")
    print_report(cards, out)
    print(f"\nwritten to {out}")
    return 0 if headline_ok(cards) else 1


if __name__ == "__main__":
    raise SystemExit(main())
