"""Seeded runs repeat exactly (feature 4, BUILD_PLAN D1 and D2). Owner: D.

    uv run python -m eval.repeat                     # seeds 1-5, all modes, to evaluate_s
    uv run python -m eval.repeat --seeds 1 --horizon-s 600

D1: the same case in fresh processes with different PYTHONHASHSEED gives the same digest.
The digest covers the metrics, the world state hash and every agent's view.
D2: a world reset in the middle of a run, then run again, equals a fresh run.
"""

import argparse
import itertools
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from agent.core import Agent
from agent.shore import ShoreNode
from eval.run_batch import POLICIES, digest, run_case, run_config
from world.sim import World

HASH_SEEDS = ("0", "4242")


def digest_in_subprocess(case: tuple, hash_seed: str) -> str:
    code = (
        "import json, sys\n"
        "from eval.run_batch import run_case\n"
        "print(run_case(tuple(json.loads(sys.argv[1])))['digest'])\n"
    )
    root = str(Path(__file__).resolve().parent.parent)
    env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": root}
    out = subprocess.run([sys.executable, "-c", code, json.dumps(list(case))], env=env,
                         capture_output=True, text=True, check=True, cwd=root)
    return out.stdout.strip()


def check_processes(case: tuple) -> dict:
    """D1: one in-process run and one fresh process per hash seed."""
    digests = {"in-process": run_case(case)["digest"]}
    for hash_seed in HASH_SEEDS:
        digests[f"PYTHONHASHSEED={hash_seed}"] = digest_in_subprocess(case, hash_seed)
    return {"check": "D1", "case": list(case[1:]), "ok": len(set(digests.values())) == 1,
            "digests": digests}


def world_digest(sim: World) -> str:
    return digest([sim.state_hash(), [node.view() for _, node in sorted(sim.nodes.items())]])


def check_reset(root: str, seed: int, policy: str, horizon_s: int) -> dict:
    """D2: run halfway, reset, run to the horizon; compare with a fresh world."""
    def fresh():
        sim = World(root, seed=seed, agent_factory=Agent, shore_factory=ShoreNode)
        sim.params = replace(sim.params, policy=policy)
        sim.reset()
        return sim

    def run_to(sim, end_ms):
        while sim.next_tick_ms <= end_ms:
            sim.step()

    end_ms = horizon_s * 1000
    a = fresh()
    run_to(a, end_ms)
    b = fresh()
    run_to(b, end_ms // 2000 * 1000)
    b.reset()
    run_to(b, end_ms)
    da, db = world_digest(a), world_digest(b)
    return {"check": "D2", "case": [seed, policy, horizon_s], "ok": da == db,
            "digests": {"fresh": da, "reset mid-run": db}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--seeds", nargs="+", type=int)
    parser.add_argument("--modes", nargs="+", choices=POLICIES, default=list(POLICIES))
    parser.add_argument("--horizon-s", type=int, help="default: evaluate_s from config/run.toml")
    args = parser.parse_args(argv)
    cfg = run_config(args.root)
    seeds = args.seeds or cfg["seeds"]
    horizon_s = args.horizon_s or cfg["evaluate_ms"] // 1000
    root = str(args.root.resolve())
    results = []
    for seed, policy in itertools.product(seeds, args.modes):
        results.append(check_processes((root, seed, policy, horizon_s)))
        results.append(check_reset(root, seed, policy, horizon_s))
        r = results[-2:]
        print(f"seed {seed} {policy}: D1 {'PASS' if r[0]['ok'] else 'FAIL'}, "
              f"D2 {'PASS' if r[1]['ok'] else 'FAIL'}", flush=True)
    failed = [r for r in results if not r["ok"]]
    if failed:
        print(json.dumps(failed, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
