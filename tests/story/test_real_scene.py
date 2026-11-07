"""R1 to R3: the real Great Belt scene."""
import json
import re
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point, shape

from contract.geo import to_xy
from eval.ais_observer import observer_for
from eval.metrics import Metrics
from eval.warm import build_world, warm_up
from tools.scene_check import hops_from_shore
from world.routes import load_scene

ROOT = Path(__file__).resolve().parents[2]
C07 = (55.4505, 10.8706)
STATIONS = {"pick:N": (55.4578, 10.9081), "pick:S": (55.3543, 11.0135), "relay": (55.405, 10.975)}


def test_r1_stations_connect_to_shore_and_boat_4_has_a_direct_link():
    scene = load_scene(ROOT)
    stations = {
        {"pick:N": 3, "pick:S": 4, "relay": 5}[t.id]: t.pts[0]
        for t in scene.mission.tasks
        if t.id in STATIONS
    }
    hops = hops_from_shore(stations, scene.mission.shore, 8000, 14000)
    assert hops == {3: 2, 4: 1, 5: 1}  # the cut on the tape removes a real direct link


def test_r2_stations_and_the_contact_sit_outside_the_lane_band():
    mission = load_scene(ROOT).mission
    lane = LineString(mission.lane)
    for task in mission.tasks:
        if task.id in STATIONS:
            assert lane.distance(Point(task.pts[0])) > mission.lane_half_m, task.id
    assert lane.distance(Point(to_xy(*C07))) > mission.lane_half_m


def test_r2_stations_and_the_contact_are_in_water():
    land_file = ROOT / "web/public/geo/land.geojson"
    features = json.loads(land_file.read_text(encoding="utf-8"))["features"]
    if not features:
        pytest.skip("land.geojson is the placeholder until #49 merges")
    land = [shape(f["geometry"]) for f in features]
    for lat, lon in (*STATIONS.values(), C07):
        assert not any(p.contains(Point(lon, lat)) for p in land), (lat, lon)


def test_r3_ais_stays_with_the_evaluator():
    """Boats have no AIS feed yet (#52): nothing they run may import the observer."""
    for folder in ("agent", "world", "contract"):
        for path in (ROOT / folder).glob("*.py"):
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"^\s*(from|import)\s+eval\b", text, re.MULTILINE), path


def test_r3_a_run_with_the_observer_leaves_boats_knowing_only_their_own_sensors():
    world = build_world(ROOT, "elysa", 1, warm_s=60)
    warm_up(world)
    metrics = Metrics(world, 12_000, t0_ms=world.warm_ms)
    metrics.ais = observer_for(world, ROOT, world.warm_ms, metrics.T, metrics.eval_t)
    for _ in range(120):
        world.step()
        metrics.on_tick()
    assert all(not node.contacts.tracks for node in world.nodes.values())
