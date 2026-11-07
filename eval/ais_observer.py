"""Real cargo and tanker crossings of the patrolled cables, watched from the evaluator. Owner: D.

Reads the private AIS clip (gitignored, one day inside the box). This is eval only: no ping
ever reaches an agent, a sensor or the shore. A crossing is the point where the straight line
between two consecutive pings of one vessel cuts a cable, timed by interpolation. It counts
as in view if a live boat is within `keep_in_view_m` at that moment. Without the clip every
metric says so instead of showing a zero.
"""

import itertools
import tomllib
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from math import hypot
from pathlib import Path

import pandas as pd

from contract.geo import to_xy
from contract.tasks import kind

CLIP = "data/ais-clip-box.csv"
SHIP_TYPES = ("Cargo", "Tanker")
MAX_GAP_MS = 1_800_000  # two pings further apart than this are not one straight track
SAME_CROSSING_MS = 1_800_000  # one vessel, one cable: anchor jitter is not a new crossing


@dataclass(frozen=True, slots=True)
class Crossing:
    t_ms: int  # mission time
    track: str
    cable: str
    x: float
    y: float


def cut(p, q, a, b) -> tuple[float, float, float] | None:
    """Where segment p-q meets segment a-b: (fraction along p-q, x, y), or None."""
    rx, ry = q[0] - p[0], q[1] - p[1]
    sx, sy = b[0] - a[0], b[1] - a[1]
    den = rx * sy - ry * sx
    if den == 0:
        return None
    u = ((a[0] - p[0]) * sy - (a[1] - p[1]) * sx) / den
    v = ((a[0] - p[0]) * ry - (a[1] - p[1]) * rx) / den
    if not (0 <= u <= 1 and 0 <= v <= 1):
        return None
    return u, p[0] + u * rx, p[1] + u * ry


def find_crossings(pings, cables: dict[str, list[tuple]]) -> list[Crossing]:
    """`pings`: (track, t_ms, x, y) sorted by track then time. `cables`: name -> polylines."""
    found: list[Crossing] = []
    last: dict[tuple[str, str], int] = {}
    for prev, ping in itertools.pairwise(pings):
        if prev[0] != ping[0] or ping[1] - prev[1] > MAX_GAP_MS:
            continue
        p, q = prev[2:], ping[2:]
        for name in sorted(cables):
            hit = None
            for line in cables[name]:
                for a, b in itertools.pairwise(line):
                    hit = cut(p, q, a, b)
                    if hit:
                        break
                if hit:
                    break
            if not hit:
                continue
            t = prev[1] + round(hit[0] * (ping[1] - prev[1]))
            key = (ping[0], name)
            if key not in last or t - last[key] > SAME_CROSSING_MS:
                found.append(Crossing(t, ping[0], name, hit[1], hit[2]))
            last[key] = t
    return sorted(found, key=lambda c: (c.t_ms, c.track, c.cable))


@lru_cache(maxsize=2)
def _pings(path: str, t0_iso: str) -> tuple:
    frame = pd.read_csv(path, usecols=["ts_file", "vessel_hash", "lat", "lon", "ship_type"])
    frame = frame[frame["ship_type"].isin(SHIP_TYPES)]
    t0 = datetime.fromisoformat(t0_iso)
    rows = []
    for ts, track, lat, lon in zip(
        frame["ts_file"], frame["vessel_hash"], frame["lat"], frame["lon"], strict=True
    ):
        t_ms = int((datetime.fromisoformat(ts) - t0).total_seconds() * 1000)
        rows.append((track, t_ms, *to_xy(lat, lon)))
    return tuple(sorted(rows))


def ais_t0(root: Path) -> str:
    with (root / "scenarios/fixed.toml").open("rb") as f:
        return next(e["ais_t0"] for e in tomllib.load(f)["event"] if e["kind"] == "reset")


def cable_lines(mission) -> dict[str, list[tuple]]:
    """Cable letter -> its segment polylines ('seg:H:0' is on cable H)."""
    out: dict[str, list[tuple]] = {}
    for task in mission.tasks:
        if kind(task.id) == "seg":
            out.setdefault(task.id.split(":")[1], []).append(task.pts)
    return out


class AisObserver:
    """Scores each crossing in [T, end] once, as mission time reaches it."""

    def __init__(self, crossings, keep_m: int, start_ms: int, end_ms: int, present: bool = True):
        self.present = present
        self.keep_m = keep_m
        self.crossings = [c for c in crossings if start_ms <= c.t_ms <= end_ms]
        self.i = 0
        self.in_view: list[Crossing] = []

    def on_tick(self, t_ms: int, live_points) -> None:
        while self.i < len(self.crossings) and self.crossings[self.i].t_ms <= t_ms:
            c = self.crossings[self.i]
            self.i += 1
            if any(hypot(x - c.x, y - c.y) <= self.keep_m for x, y in live_points):
                self.in_view.append(c)

    def summary(self) -> dict:
        if not self.present:
            return {"ais_present": False}
        return {
            "ais_present": True,
            "crossings_after_T": self.i,
            "crossings_in_view": len(self.in_view),
        }


def observer_for(world, root: Path, t0_ms: int, T_ms: int, eval_ms: int) -> AisObserver:
    """T_ms and eval_ms are world time; the observer works in mission time."""
    path = root / CLIP
    start, end = T_ms - t0_ms, eval_ms - t0_ms
    if not path.exists():
        return AisObserver([], world.params.keep_in_view_m, start, end, present=False)
    crossings = find_crossings(_pings(str(path), ais_t0(root)), cable_lines(world.mission))
    return AisObserver(crossings, world.params.keep_in_view_m, start, end)
