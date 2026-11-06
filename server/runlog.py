"""JSONL run log for the real sim. Owner: C. BUILD_PLAN step 13 (run log format, line 238).

One file per run in runs/ (gitignored). Lines, in order of sim time:

    {"type": "header", "seed", "config_hash", "git_commit", "git_dirty", "schema_version", ...}
    {"type": "event", "t_ms", "event"}        every world event (scripted and injected)
    {"type": "cmd", "t_ms", "msg", "ok"}      every console command the sim received
    {"type": "snapshot", "t_ms", "shore", "truth"}   both channels, every SNAPSHOT_MS sim time
    {"type": "hash", "t_ms", "hash"}          replay digest, every HASH_MS sim time

`cmd.t_ms` is the last processed tick when the command arrived; replay applies it right after
that tick, so the run can be rebuilt from the seed and the command lines (server/replay.py).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import IO

from server.feed import ROOT

SNAPSHOT_MS = 10_000
HASH_MS = 60_000
# every input file that shapes a run; a different hash means a replay is not comparable
CONFIG_GLOBS = ("config/*.toml", "config/ui.json", "scenarios/*.toml", "data/scene-coordinates.json")


def config_hash(root: Path = ROOT) -> str:
    h = hashlib.sha256()
    for pattern in CONFIG_GLOBS:
        for p in sorted(root.glob(pattern)):
            h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def git_state(root: Path = ROOT) -> tuple[str, bool]:
    """(commit, dirty). 'unknown' when git is not available (e.g. a zip copy)."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                text=True, check=True, timeout=5).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root,
                                capture_output=True, text=True, check=True, timeout=5).stdout
        return commit, bool(status.strip())
    except (OSError, subprocess.SubprocessError):
        return "unknown", False


def replay_digest(world) -> str:
    """World physics and queues, every agent's own view and the shore picture, in one hash."""
    shore = world.shore.picture(world.t_ms, 1).model_dump(mode="json") if world.shore else None
    state = {
        "world": world.state_hash(),
        "agents": [world.nodes[b].view() for b in sorted(world.nodes)],
        "shore": shore,
    }
    blob = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


class RunLog:
    def __init__(self, path: Path, header: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._f: IO[str] | None = path.open("w", encoding="utf-8")
        self.write({"type": "header", **header})

    @classmethod
    def open_new(cls, runs_dir: Path, seed: int, schema_version: int, t0_utc: str) -> RunLog:
        started = datetime.now(UTC)  # wall clock for the file name only, never for sim data
        commit, dirty = git_state()
        name = f"sim-seed{seed}-{started.strftime('%Y%m%dT%H%M%SZ')}-{started.microsecond:06d}.jsonl"
        return cls(runs_dir / name, {
            "source": "sim", "seed": seed, "schema_version": schema_version, "t0_utc": t0_utc,
            "config_hash": config_hash(), "git_commit": commit, "git_dirty": dirty,
            "started_utc": started.isoformat(timespec="seconds"),
            "snapshot_ms": SNAPSHOT_MS, "hash_ms": HASH_MS,
        })

    def write(self, rec: dict) -> None:
        if self._f is not None:
            self._f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

    def flush(self) -> None:
        if self._f is not None:
            self._f.flush()

    def close(self) -> None:
        if self._f is not None:
            self._f.close()
            self._f = None


def read(path: Path) -> list[dict]:
    """All records. A last line cut short (the server still writing it) is skipped."""
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    out = []
    for i, line in enumerate(lines):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            if i != len(lines) - 1:
                raise
    return out
