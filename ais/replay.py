"""Replay the anonymised AIS clip. Pings are sorted by time and served per tick window.

The clip is one day (3 Nov 2026) inside the box. Vessel IDs are salted hashes.
No boat ever receives a global table: world/sim hands each boat only the
pings inside its class-dependent reception range (ais_class_a_m, ais_class_b_m).
"""

import csv
from bisect import bisect_left, bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from contract.geo import dist, to_xy
from contract.mission import Detection, Point

DEFAULT_CLIP = "data/ais-clip-box.csv"
DEFAULT_T0 = "2026-11-03T10:15:00"
KNOT_MM_S = 514.444


@dataclass(frozen=True, slots=True)
class AisPing:
    track: str
    x: int
    y: int
    sog: int
    cog: int
    ship_type: str
    ais_class: str
    t_ms: int
    length_band_m: int | None = None

    @property
    def point(self) -> Point:
        return self.x, self.y

    def detection(self) -> Detection:
        return Detection(self.track, self.x, self.y, self.sog, self.cog, True)


def ais_in_range(
    point: Point, pings: Iterable[AisPing], class_a_m: int, class_b_m: int
) -> tuple[AisPing, ...]:
    """Filter pings to those within the boat's class-dependent AIS reception range."""
    return tuple(
        ping
        for ping in pings
        if dist(point, ping.point) <= (class_a_m if ping.ais_class == "Class A" else class_b_m)
    )


@lru_cache(maxsize=4)
def _load_pings(path_str: str, t0_iso: str) -> tuple[tuple[int, ...], tuple[AisPing, ...]]:
    t0 = datetime.fromisoformat(t0_iso)
    rows: list[tuple[int, AisPing]] = []
    with Path(path_str).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ts = datetime.fromisoformat(row["ts_file"])
            t_ms = round((ts - t0).total_seconds() * 1000)
            x, y = to_xy(float(row["lat"]), float(row["lon"]))
            sog = round(float(row["sog_kn"]) * KNOT_MM_S) if row.get("sog_kn") else 0
            cog = round(float(row["cog_deg"])) % 360 if row.get("cog_deg") else 0
            length_raw = row.get("length_band_m")
            length_band = round(float(length_raw)) if length_raw else None
            ping = AisPing(
                track=row["vessel_hash"],
                x=x,
                y=y,
                sog=sog,
                cog=cog,
                ship_type=row.get("ship_type", ""),
                ais_class=row.get("ais_class", "Class B"),
                t_ms=t_ms,
                length_band_m=length_band,
            )
            rows.append((t_ms, ping))
    rows.sort(key=lambda item: (item[0], item[1].track))
    return tuple(item[0] for item in rows), tuple(item[1] for item in rows)


class AisReplay:
    def __init__(self, path: str | Path | None = None, t0_iso: str = DEFAULT_T0):
        self.t0_iso = t0_iso
        self.t0 = datetime.fromisoformat(t0_iso)
        self.path = Path(path) if path is not None else Path(DEFAULT_CLIP)
        self.available = self.path.is_file()
        if not self.available:
            self.times: tuple[int, ...] = ()
            self.pings: tuple[AisPing, ...] = ()
            return
        self.times, self.pings = _load_pings(str(self.path.resolve()), t0_iso)

    def between(self, t_from_ms: int, t_to_ms: int) -> tuple[AisPing, ...]:
        """Pings with t_from_ms < t <= t_to_ms."""
        if not self.available or t_to_ms <= t_from_ms:
            return ()
        i = bisect_right(self.times, t_from_ms)
        j = bisect_right(self.times, t_to_ms)
        return self.pings[i:j]

    def for_boat(
        self, point: Point, t_from_ms: int, t_to_ms: int, class_a_m: int, class_b_m: int
    ) -> tuple[AisPing, ...]:
        """In-range pings for one boat in (t_from_ms, t_to_ms]."""
        return ais_in_range(point, self.between(t_from_ms, t_to_ms), class_a_m, class_b_m)

    def detections_for_boat(
        self, point: Point, t_from_ms: int, t_to_ms: int, class_a_m: int, class_b_m: int
    ) -> tuple[Detection, ...]:
        """Newest in-range AIS Detection per vessel in (t_from_ms, t_to_ms], sorted by track."""
        latest: dict[str, AisPing] = {}
        for ping in self.for_boat(point, t_from_ms, t_to_ms, class_a_m, class_b_m):
            prev = latest.get(ping.track)
            if prev is None or ping.t_ms >= prev.t_ms:
                latest[ping.track] = ping
        return tuple(latest[track].detection() for track in sorted(latest))

    def count_in_window(self, t_from_ms: int, t_to_ms: int) -> int:
        if not self.available or t_to_ms < t_from_ms:
            return 0
        return bisect_right(self.times, t_to_ms) - bisect_left(self.times, t_from_ms)
