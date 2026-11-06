"""Replay a run log and check its hashes (acceptance test D3). Owner: C.

    uv run python -m server.replay runs/<file>.jsonl

Rebuilds the run from the header's seed plus the logged console commands, each applied right
after the tick it arrived at, and compares the replay digest at every logged hash line.
Prints the first mismatch, or how many hashes matched. Exit code 0 only if all match.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from server.runlog import config_hash, read, replay_digest


@dataclass
class Result:
    ok: bool
    checked: int
    message: str


def replay(path: Path) -> Result:
    from server.bridge import SimSource

    lines = read(path)
    if not lines or lines[0].get("type") != "header":
        return Result(False, 0, "not a run log: first line is not a header")
    head = lines[0]
    notes = []
    if head.get("config_hash") != config_hash():
        notes.append("config files differ from the ones this run used")
    cmds: dict[int, list[dict]] = {}
    for rec in lines:
        if rec["type"] == "cmd":
            cmds.setdefault(int(rec["t_ms"]), []).append(rec)
    hashes = [(int(r["t_ms"]), r["hash"]) for r in lines if r["type"] == "hash"]
    if not hashes:
        return Result(False, 0, "no hash lines to check")

    src = SimSource(int(head["seed"]))  # no log of its own
    world = src.world
    checked = 0
    for t_ms, want in hashes:
        while world.t_ms < t_ms:
            for rec in cmds.pop(world.t_ms, []):
                _apply(src, rec, notes)
            world.step()
            src._after_tick()
        got = replay_digest(world)
        if got != want:
            return Result(False, checked, f"hash differs at t = {t_ms // 1000} s "
                          f"(first bad check, {checked} earlier ones matched)"
                          + (f"; note: {'; '.join(notes)}" if notes else ""))
        checked += 1
    end = hashes[-1][0] // 1000
    return Result(True, checked, f"replay OK: {checked} hashes match, t = 0 to {end} s"
                  + (f"; note: {'; '.join(notes)}" if notes else ""))


def _apply(src, rec: dict, notes: list[str]) -> None:
    res = src.command(rec["msg"])
    if res["ok"] != rec["ok"]:
        notes.append(f"command at t = {rec['t_ms'] // 1000} s gave ok={res['ok']}, "
                     f"logged ok={rec['ok']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay a runs/*.jsonl file and check its hashes.")
    ap.add_argument("log", type=Path)
    r = replay(ap.parse_args().log)
    print(r.message)
    sys.exit(0 if r.ok else 1)


if __name__ == "__main__":
    main()
