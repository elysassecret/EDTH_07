"""Boats route around the real coastline (agent/water.py, agent/land.py). Owner: A."""

import hashlib
import json
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from agent import land, water
from agent.core import Agent
from agent.shore import ShoreNode
from contract.geo import to_xy
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]
LAND_FILE = ROOT / "web/public/geo/land.geojson"
QUAY = (8237, -7605)  # Korsør: boats tie up on the quay point, which the map draws on land


def real_land():
    feats = json.loads(LAND_FILE.read_text(encoding="utf-8"))["features"]
    return unary_union([Polygon([to_xy(lat, lon) for lon, lat in f["geometry"]["coordinates"][0]])
                        for f in feats])


def test_the_coastline_module_matches_the_map():
    assert land.SOURCE_SHA256 == hashlib.sha256(LAND_FILE.read_bytes()).hexdigest(), \
        "land.geojson changed: run `uv run python -m world.make_land`"


def test_routes_between_the_stations_stay_off_land():
    shore = real_land()
    pairs = [
        (QUAY, (797, 8644)),  # Korsør to the north: used to cut straight across Zealand
        ((797, 8644), QUAY),
        ((853, -5081), (-2278, -7893)),
        ((-2278, -7893), (4446, -4976)),
        ((-5528, 6491), (-2278, -7893)),
        ((-8000, -9000), (8000, 8000)),
    ]
    for a, b in pairs:
        pts = water.path(a, b)
        line = LineString(pts)
        # a point on land itself (the quay, a cable landfall) may cross its own coast nearby
        allowed = Point(a).buffer(water.EXIT_M).union(Point(b).buffer(water.EXIT_M))
        assert line.intersection(shore).difference(allowed).length == 0.0, (a, b, pts)
        assert pts == water.path(a, b)  # same answer every time


def test_no_boat_drives_over_land_in_a_four_hour_run():
    shore = real_land()
    quay = Point(QUAY).buffer(150)
    for launch, seed in ((True, 1), (False, 1)):
        w = World(ROOT, seed=seed, agent_factory=Agent, shore_factory=ShoreNode, launch=launch)
        on_land = []
        while w.t < 14_400_000:
            w.step()
            if w.t % 10_000:
                continue
            for b, st in sorted(w.boats.items()):
                p = Point(*st.point)
                if st.enabled and shore.contains(p) and not quay.contains(p):
                    on_land.append((w.t // 1000, b, st.point))
        assert on_land == [], (launch, on_land[:5])


def test_a_landfall_is_reached_at_its_access_point_in_water():
    landfall = (-2278, -7893)  # seg:M:0 lands on Sprogø
    assert water.on_land(landfall)
    a = water.access(landfall)
    assert not water.on_land(a) and water.dist(a, landfall) < 200
    assert water.arrive_m(landfall, 10) == water.dist(a, landfall) + 10
    assert water.access((0, 0)) == (0, 0)  # a point in water is its own access point


def test_no_boat_loops_on_the_coast():
    """For 10 minutes a looping boat moves (> 1 m/s) but never gets 300 m from where it was.
    USV 01 did this near Sprogø for up to 47 min before access points, the 150 m corridor and
    steering up-current."""
    from collections import deque

    from contract.geo import dist

    for launch, seed in ((True, 1), (False, 2)):
        w = World(ROOT, seed=seed, agent_factory=Agent, shore_factory=ShoreNode, launch=launch)
        hist = {b: deque(maxlen=61) for b in w.boats}
        loops = []
        while w.t < 8 * 3_600_000:
            w.step()
            if w.t % 10_000:
                continue
            for b, st in sorted(w.boats.items()):
                hist[b].append((st.point, w.telemetry[b]["sog"], w.actions[b].mode))
                h = hist[b]
                if len(h) == 61 and all(m in ("PATROL", "RETURNING") for _, _, m in h) \
                        and sum(s for _, s, _ in h) > 61_000 \
                        and max(dist(h[0][0], p) for p, _, _ in h) < 300:
                    loops.append((b, w.t // 1000))
        assert loops == [], (launch, seed, loops[:3])
