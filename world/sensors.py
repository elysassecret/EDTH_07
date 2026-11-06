"""Own-sensor views: camera contacts within r_detect per class, AIS within class range.

Visit credit (evaluator) uses r_verify only; detection never reads a name.
"""
from __future__ import annotations

import math

from contract.views import AisPing, Observation

from .motion import Boat, Vessel


def camera(boat: Boat, vessels: list[Vessel], r_detect: dict[str, int], recent_ais: dict[str, tuple[float, float, int]],
           t: int, ais_match_m: float = 500.0, ais_match_ms: int = 60_000) -> list[Observation]:
    out: list[Observation] = []
    for v in sorted(vessels, key=lambda v: v.id):
        d = math.hypot(v.x - boat.x, v.y - boat.y)
        if d > r_detect.get(v.cls, r_detect["dusk"]):
            continue
        match = False
        for _, (ax, ay, at) in sorted(recent_ais.items()):
            if t - at <= ais_match_ms and math.hypot(ax - v.x, ay - v.y) <= ais_match_m:
                match = True
                break
        out.append(Observation(v.id, v.x, v.y, v.sog_mps, v.course_deg, d, match))
    return out


def ais_in_range(boat_xy: tuple[float, float], pings: list[AisPing], class_a_m: float, class_b_m: float) -> list[AisPing]:
    out = []
    for p in pings:
        rng = class_a_m if p.ais_class == "Class A" else class_b_m
        if math.hypot(p.x - boat_xy[0], p.y - boat_xy[1]) <= rng:
            out.append(p)
    return out
