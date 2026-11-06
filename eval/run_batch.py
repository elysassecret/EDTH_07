"""Headless runner: python -m eval.run_batch --modes static,off,elysa --seeds 1,2,3,4,5

Writes runs/<config-hash>/<mode>_s<seed>.jsonl plus a scorecard JSON, then prints the table.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from contract.config import MODES, ROOT, load, load_scenario
from world.sim import Sim

from .metrics import Metrics


def run_one(mode: str, seed: int, overrides: dict | None = None, log_dir: Path | None = None,
            use_ais: bool = True, until_s: int | None = None, scenario: list[dict] | None = None,
            quiet: bool = False) -> tuple[Sim, Metrics]:
    ov = dict(MODES[mode])
    ov.update(overrides or {})
    cfg = load(overrides=ov)
    log_path = None
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{mode}_s{seed}.jsonl"
    sim = Sim(cfg, mode=mode, seed=seed, scenario=scenario, use_ais=use_ais, log_path=log_path)
    m = Metrics(sim)
    sim.observers.append(m)
    t0 = time.perf_counter()
    sim.run_warm()
    end = until_s if until_s is not None else int(cfg["run"]["horizon_s"])
    sim.run_until(end)
    dt = time.perf_counter() - t0
    if m.evaluated is None:
        m.evaluated = m.scorecard(sim.t)
    m.evaluated["wall_s"] = round(dt, 1)
    m.evaluated["warm_hash"] = sim.warm_hash
    m.evaluated["ages_T_minus_1"] = None if m.ages_at_T_minus_1 is None else __import__("hashlib").sha256(m.ages_at_T_minus_1).hexdigest()[:16]
    m.evaluated["final_hash"] = sim.state_hash()
    m.evaluated["tape_hash"] = sim.tape.hash()
    m.evaluated["config_hash"] = cfg["_hash"]
    if log_dir is not None:
        sim.log.write({"scorecard": m.evaluated})
        (log_dir / f"{mode}_s{seed}_evidence.json").write_text(json.dumps(sim.evidence_bundle()), encoding="utf-8")
    sim.log.close()
    if not quiet:
        print(f"{mode:7s} seed {seed}: km overdue {m.evaluated['cable_km_overdue']:5.1f}  worst {m.evaluated['worst_age_s']:6d}s "
              f"in-view {m.evaluated['lane_crossings_in_view']}/{m.evaluated['lane_crossings_post_event']}  "
              f"ops {m.evaluated['operator_actions']}  {dt:.1f}s", file=sys.stderr)
    return sim, m


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="static,off,elysa")
    ap.add_argument("--seeds", default="1,2,3,4,5")
    ap.add_argument("--speed", type=float, default=None, help="override boat speed (sensitivity run)")
    ap.add_argument("--radio", type=float, default=None, help="override boat-to-boat radio range (sensitivity run)")
    ap.add_argument("--no-ais", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    overrides = {}
    if args.speed:
        overrides["boat.speed_mps"] = args.speed
    if args.radio:
        overrides["radio.boat_m"] = args.radio
    cfg = load(overrides=overrides)
    out = Path(args.out) if args.out else ROOT / "runs" / cfg["_hash"]
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for mode in args.modes.split(","):
        for seed in [int(s) for s in args.seeds.split(",")]:
            _, m = run_one(mode, seed, overrides, out, use_ais=not args.no_ais)
            results.append(m.evaluated)
    (out / "scorecards.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    from .report import print_report
    print_report(results, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
