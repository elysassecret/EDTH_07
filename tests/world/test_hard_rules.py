"""Simulator hard rules on the runs we demo (release-gate P0). Owner: C, with A and B.

Every 10 sim-seconds for 12 hours, on the Blue Shadow video run (placed start, scripted tape)
and on the live console run (shore launch, quiet tape), none of these may happen:
- a boat at sea with an empty battery;
- a boat on the map's real land (except at the Korsør quay);
- a boat looping: 10 minutes moving faster than 1 m/s without getting 300 m from where it was;
- a task held by two boats for more than 2 minutes (the tables must agree).
"""

import json
from collections import deque
from pathlib import Path

import pytest
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

from agent.core import Agent
from agent.shore import ShoreNode
from contract.geo import dist, to_xy
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]
QUAY_M = 150


def land():
    feats = json.loads((ROOT / "web/public/geo/land.geojson").read_text(encoding="utf-8"))["features"]
    return prep(unary_union([Polygon([to_xy(lat, lon) for lon, lat in f["geometry"]["coordinates"][0]])
                             for f in feats]))


@pytest.mark.slow
@pytest.mark.parametrize("name,launch,scenario", [
    ("video run", False, "scenarios/fixed.toml"),
    ("live run", True, "scenarios/quiet.toml"),
])
def test_hard_rules_hold_for_twelve_hours(name, launch, scenario):
    shore_land = land()
    w = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode, launch=launch,
              scenario=scenario)
    hist = {b: deque(maxlen=61) for b in w.boats}
    double: dict[str, int] = {}
    broken = []
    while w.t < 12 * 3_600_000:
        w.step()
        if w.t % 10_000:
            continue
        s = w.t // 1000
        owners: dict[str, list[int]] = {}
        for b, st in sorted(w.boats.items()):
            if not st.enabled:
                continue
            away = dist(st.point, w.mission.shore) > QUAY_M
            if away and st.charge_ms == 0:
                broken.append(f"{s}s USV {b:02d} empty battery at sea")
            if away and shore_land.contains(Point(*st.point)):
                broken.append(f"{s}s USV {b:02d} on land at {st.point}")
            hist[b].append((st.point, w.telemetry[b]["sog"], w.actions[b].mode))
            h = hist[b]
            if (len(h) == 61 and all(m in ("PATROL", "RETURNING") for _, _, m in h)
                    and sum(v for _, v, _ in h) > 61_000
                    and max(dist(h[0][0], p) for p, _, _ in h) < 300):
                broken.append(f"{s}s USV {b:02d} looping near {st.point}")
            for task in w.nodes[b].table.held_by(b):
                owners.setdefault(task, []).append(b)
        for task, bs in owners.items():
            if len(bs) > 1:
                double.setdefault(task, s)
                if s - double[task] > 120:
                    broken.append(f"{s}s {task} held by {bs} for over 2 min")
            else:
                double.pop(task, None)
        for task in [k for k in double if k not in owners or len(owners[k]) < 2]:
            double.pop(task)
    assert broken == [], f"{name}: " + "; ".join(broken[:8])
