"""Replay a run log: re-run from seed plus the injection list and check every logged state hash.

    python -m server.replay runs/<hash>/elysa_s1.jsonl

It does not play back snapshots: it recomputes the run and proves determinism (D3).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from contract.config import MODES, load
from eval.metrics import Metrics
from world.sim import Sim


def replay(path: Path, quiet: bool = False) -> tuple[bool, str]:
    header = None
    hashes: list[tuple[int, str]] = []
    injections: list[dict] = []
    warm_hash = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if header is None and "seed" in obj and "mode" in obj:
                header = obj
            elif "hash" in obj and "t" in obj and "warm_hash" not in obj:
                hashes.append((obj["t"], obj["hash"]))
            elif "warm_hash" in obj:
                warm_hash = obj["warm_hash"]
            elif "event" in obj and obj["event"].get("kind") in ("boat_fail", "boat_restore", "link_off", "link_on",
                                                                   "battery_low", "cmd", "contact_start",
                                                                   "contact_depart", "contact_remove"):
                ev = obj["event"]
                injections.append(ev)
    if header is None:
        return False, "no header line"
    cfg = load(overrides=MODES[header["mode"]])
    if cfg["_hash"] != header["config_hash"]:
        return False, f"config hash differs: log {header['config_hash']} vs now {cfg['_hash']}"
    sim = Sim(cfg, mode=header["mode"], seed=int(header["seed"]), use_ais=True)
    sim.observers.append(Metrics(sim))
    # scripted events are re-applied by the tape; injected ones (not in the tape) are re-injected at their time
    tape_keys = {(e["t"], e["kind"]) for e in sim.events}
    extra = [e for e in injections if (e.get("t", -1), e["kind"]) not in tape_keys]
    sim.run_warm()
    if warm_hash and sim.warm_hash != warm_hash:
        return False, f"warm hash differs: {warm_hash} vs {sim.warm_hash}"
    pending = sorted(extra, key=lambda e: e["t"])
    checked = 0
    for t_ms, h in hashes:
        while pending and pending[0]["t"] * 1000 <= t_ms:
            ev = pending.pop(0)
            sim.pending.append(ev)
        while sim.t < t_ms:
            sim.step()
        got = sim.state_hash()
        if got != h:
            return False, f"hash mismatch at t={t_ms // 1000}s: log {h} vs replay {got} (after {checked} good)"
        checked += 1
    return True, f"replay OK: {checked} hashes matched, seed {header['seed']}, mode {header['mode']}"


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    ok, msg = replay(Path(argv[0]))
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
