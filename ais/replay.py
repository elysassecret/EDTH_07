"""Replay the anonymised AIS clip. Pings are sorted by time and served per sim second.

The clip is one day (3 Nov 2026) inside the box. Vessel ids are salted hashes.
No boat ever receives a global table: world/sim hands each boat only the
pings inside its class-dependent reception range.
"""
from __future__ import annotations

import csv
from bisect import bisect_left, bisect_right
from datetime import datetime
from pathlib import Path

from contract.config import ROOT
from contract.views import AisPing
from world import geo


class AisReplay:
    def __init__(self, path: str | Path | None, t0_iso: str):
        self.t0 = datetime.fromisoformat(t0_iso)
        self.times: list[int] = []     # ms relative to t0
        self.pings: list[AisPing] = []
        p = Path(path) if path else ROOT / "data" / "ais-clip-box.csv"
        self.available = p.exists()
        if not self.available:
            return
        rows = []
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ts = datetime.fromisoformat(r["ts_file"])
                t_ms = int((ts - self.t0).total_seconds() * 1000)
                x, y = geo.ll_to_xy(float(r["lat"]), float(r["lon"]))
                sog = float(r["sog_kn"]) if r["sog_kn"] else 0.0
                cog = float(r["cog_deg"]) if r["cog_deg"] else 0.0
                rows.append((t_ms, AisPing(r["vessel_hash"], x, y, sog, cog, r["ship_type"], r["ais_class"], t_ms)))
        rows.sort(key=lambda z: (z[0], z[1].track))
        self.times = [z[0] for z in rows]
        self.pings = [z[1] for z in rows]

    def between(self, t_from_ms: int, t_to_ms: int) -> list[AisPing]:
        """Pings with t_from < t <= t_to."""
        if not self.available:
            return []
        i = bisect_right(self.times, t_from_ms)
        j = bisect_right(self.times, t_to_ms)
        return self.pings[i:j]

    def count_in_window(self, t_from_ms: int, t_to_ms: int) -> int:
        return bisect_right(self.times, t_to_ms) - bisect_left(self.times, t_from_ms)
