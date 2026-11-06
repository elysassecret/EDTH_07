"""Reproducible integration audit, NOT the final eval/ benchmark or scorecard.

Runs the real nodes without private AIS. Starts cold at the fixed initial phase;
pre-event comparisons diagnose elysa/off physical equality, not full fairness.
"""

import argparse
import hashlib
import itertools
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import CLAIMED
from world.sim import World

CONFIG_FILES = (
    "config/agent.toml",
    "config/boat.toml",
    "config/energy.toml",
    "config/radio.toml",
    "config/run.toml",
    "config/scene.toml",
    "scenarios/fixed.toml",
    "data/scene-coordinates.json",
)


def config_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for name in sorted(CONFIG_FILES):
        digest.update(name.encode() + b"\0" + (root / name).read_bytes() + b"\0")
    return digest.hexdigest()


def run_case(case: tuple[str, int, str, int, int]) -> dict:
    root, seed, policy, speed, horizon_s = case
    if policy not in ("static", "off", "elysa") or speed <= 0 or horizon_s < 0:
        raise ValueError("invalid policy, speed or horizon")
    sim = World(root, seed=seed, agent_factory=Agent, shore_factory=ShoreNode)
    sim.params = replace(sim.params, policy=policy, speed_mm_s=speed)
    sim.reset()
    horizon_ms = horizon_s * 1000
    if horizon_ms % sim.tick_ms:
        raise ValueError("horizon must be a tick boundary")
    comparison_ms = min(horizon_ms, max(0, sim.params.repair_off_after_ms - sim.tick_ms))
    pre_event_hash = None
    local_detect_ms = None
    first_claim_ms = None
    watcher_ids = set()
    flags = set()
    while sim.next_tick_ms <= horizon_ms:
        sim.step()
        if sim.t_ms == comparison_ms:
            pre_event_hash = sim.state_hash()
        for _, node in sorted(sim.nodes.items()):
            if local_detect_ms is None and any(
                obs["track"] == "C-07" for obs in node.contacts.own_obs
            ):
                local_detect_ms = sim.t_ms
            record = node.table.recs.get("contact:C-07")
            if record is not None and record.state == CLAIMED:
                if first_claim_ms is None:
                    first_claim_ms = sim.t_ms
                watcher_ids.add(record.owner)
            flags.update(
                flag
                for flag, value in node.contacts.flags.get("contact:C-07", {}).items()
                if value is True
            )
    return {
        "seed": seed,
        "policy": policy,
        "speed_mm_s": speed,
        "horizon_ms": horizon_ms,
        "config_sha256": config_hash(Path(root)),
        "initial_phase": "cold-fixed",
        "comparison_ms": comparison_ms,
        "pre_event_physical_hash": pre_event_hash,
        "final_physical_hash": sim.state_hash(),
        "contact": {
            "first_local_detection_ms": local_detect_ms,
            "first_claim_ms": first_claim_ms,
            "watcher_ids": sorted(watcher_ids),
            "flags": sorted(flags),
        },
        "boats": [
            {
                "id": boat,
                "mode": sim.actions[boat].mode,
                "batt": state.own().batt,
                "held": sim.nodes[boat].table.held_by(boat),
            }
            for boat, state in sorted(sim.boats.items())
        ],
        "applied_event_kinds": [event["kind"] for event in sim.events],
        "shore_contact_count": len(sim.shore.picture(sim.t_ms).contacts),
    }


def comparisons(results: list[dict]) -> list[dict]:
    groups = {}
    for row in results:
        key = (row["seed"], row["speed_mm_s"], row["horizon_ms"])
        groups.setdefault(key, {})[row["policy"]] = row
    checks = []
    for (seed, speed, horizon), modes in sorted(groups.items()):
        a, b = modes.get("elysa"), modes.get("off")
        equal = None
        if a is not None and b is not None:
            equal = (
                a["config_sha256"] == b["config_sha256"]
                and a["comparison_ms"] == b["comparison_ms"]
                and a["pre_event_physical_hash"] == b["pre_event_physical_hash"]
            )
        checks.append(
            {
                "seed": seed,
                "speed_mm_s": speed,
                "horizon_ms": horizon,
                "elysa_off_pre_event_physical_equal": equal,
            }
        )
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--speeds", nargs="+", type=int, default=[2300, 3000])
    parser.add_argument(
        "--policies",
        nargs="+",
        choices=("static", "off", "elysa"),
        default=["static", "off", "elysa"],
    )
    parser.add_argument("--horizon-s", type=int, default=14000)
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    if args.jobs < 1 or args.horizon_s < 0 or any(speed <= 0 for speed in args.speeds):
        parser.error("jobs/speeds must be positive and horizon nonnegative")
    cases = [
        (str(args.root.resolve()), seed, policy, speed, args.horizon_s)
        for seed, speed, policy in itertools.product(args.seeds, args.speeds, args.policies)
    ]
    if args.jobs == 1:
        results = [run_case(case) for case in cases]
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(run_case, cases))
    checks = comparisons(results)
    print(
        json.dumps(
            {
                "label": "integration audit, NOT final benchmark/scorecard",
                "limitations": [
                    "cold fixed phase, not varied warm-up",
                    "physical hashes exclude full agent replay state",
                    "channel fairness still requires eval acceptance",
                    "no private AIS replay or metric claims",
                    "shore contact presentation depends on A's implementation",
                ],
                "checks": checks,
                "runs": results,
            },
            sort_keys=True,
        )
    )
    return 1 if any(check["elysa_off_pre_event_physical_equal"] is False for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
