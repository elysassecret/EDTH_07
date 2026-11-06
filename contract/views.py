"""Shapes crossing the agent/world and sim/UI boundaries.

Sensors: what one boat is allowed to know each tick (own state, own camera,
own AIS receiver, own radio inbox). Nav: what it asks the hull to do.
Snapshot: the JSON sent over WebSocket on /shore (delivered data only) and
/truth (evaluator panel, labelled).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Observation:
    vid: str          # vessel id as the camera track id (stable per sim vessel)
    x: float
    y: float
    sog_mps: float
    cog_deg: float
    dist_m: float
    ais_match: bool   # an AIS ping within 500 m in the last 60 s


@dataclass(slots=True)
class AisPing:
    track: str
    x: float
    y: float
    sog_kn: float
    cog_deg: float
    ship_type: str
    ais_class: str
    t_ms: int


@dataclass(slots=True)
class Sensors:
    t: int
    x: float
    y: float
    batt_s: int           # seconds of endurance left
    batt_permille: int
    speed_mps: float
    observations: list[Observation] = field(default_factory=list)
    ais: list[AisPing] = field(default_factory=list)
    inbox: list[bytes] = field(default_factory=list)
    forced_return: bool = False   # hull battery monitor says go home


@dataclass(slots=True)
class Nav:
    target: tuple[float, float] | None   # None = hold position
    mode: str


SNAPSHOT_SCHEMA = 1


def empty_snapshot(t: int, speed: int) -> dict:
    return {"schema": SNAPSHOT_SCHEMA, "t": t, "speed": speed, "boats": [], "tasks": {},
            "seg_age": {}, "contacts": [], "events": [], "links": [], "ais": [], "cards": [],
            "metrics": {}, "warnings": []}
