"""Geometry and mission checks against the committed public scene."""

import json
import os
import subprocess
import sys
from dataclasses import asdict
from itertools import pairwise
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point, Polygon

from contract.mission import TaskSpec
from world.routes import load_mission, load_scene, sample_route, split_route

ROOT = Path(__file__).resolve().parents[2]


def test_scene_geometry_and_roles():
    scene = load_scene(ROOT)
    mission = scene.mission
    box = Polygon(scene.boundary)
    segments = [task for task in mission.tasks if task.id.startswith("seg:")]
    assert mission.boats == (1, 2, 3, 4, 5)
    assert len({task.id for task in mission.tasks}) == len(mission.tasks)
    assert dict(mission.initial).keys() == {task.id for task in mission.tasks}
    for task in segments:
        line = LineString(task.pts)
        assert 0 < line.length <= 5000
        # Integer rounding can displace a boundary intersection by less than a metre.
        assert box.buffer(1).covers(line)
        assert dict(mission.initial)[task.id] == (2 if task.id.startswith("seg:H:") else 1)
    for task in mission.tasks:
        for point in task.pts:
            assert all(isinstance(value, int) for value in point)
        if not task.id.startswith("seg:"):
            assert LineString(mission.lane).distance(Point(task.pts[0])) > mission.lane_half_m
    assert dict(mission.initial)["pick:N"] == 3
    assert dict(mission.initial)["pick:S"] == 4
    assert dict(mission.initial)["relay"] == 5
    assert load_mission(ROOT) == mission


def test_clipping_preserves_selected_cable_lengths():
    from contract.geo import to_xy

    scene = load_scene(ROOT)
    with (ROOT / "data/scene-coordinates.json").open() as handle:
        data = json.load(handle)
    for cable, short_id in (
        ("HVDC_Storebaelt_I", "H"),
        ("Great_Belt_1_fibre", "G"),
        ("MV_60kV_Sprogo_Funen", "M"),
    ):
        source = LineString(to_xy(*point) for point in data["cables"][cable]["lat_lon"])
        expected = source.intersection(Polygon(scene.boundary)).length
        tasks = [t for t in scene.mission.tasks if t.id.startswith(f"seg:{short_id}:")]
        assert abs(sum(LineString(t.pts).length for t in tasks) - expected) < 3
        for a, b in pairwise(tasks):
            assert a.pts[-1] == b.pts[0]


def test_split_preserves_bends_and_direction():
    line = LineString([(0, 0), (2000, 0), (2000, 4000)])
    pieces = split_route(line, 5000)
    assert pieces == (((0, 0), (2000, 0), (2000, 1000)), ((2000, 1000), (2000, 4000)))
    assert split_route(LineString([(0, 0), (5000, 0)]), 5000) == (((0, 0), (5000, 0)),)


def test_samples_use_regular_offsets_without_duplicate_terminal_sample():
    task = TaskSpec("seg:test:0", ((0, 0), (250, 0)))
    samples = sample_route(task, 100)
    assert [s.offset_m for s in samples] == [0, 100, 200]
    assert [s.point for s in samples] == [(0, 0), (100, 0), (200, 0)]
    scene = load_scene(ROOT)
    assert all(s.offset_m % 100 == 0 for s in scene.samples)
    assert {s.task for s in scene.samples} == {
        t.id for t in scene.mission.tasks if t.id.startswith("seg:")
    }


@pytest.mark.parametrize("limit", [0, -1, 1])
def test_invalid_segment_limit(limit):
    with pytest.raises(ValueError):
        split_route(LineString([(0, 0), (10, 0)]), limit)


def test_invalid_sample_step():
    with pytest.raises(ValueError):
        sample_route(TaskSpec("seg:test:0", ((0, 0), (10, 0))), 0)


def test_load_is_independent_of_hash_seed():
    code = "import json; from dataclasses import asdict; from world.routes import load_scene; print(json.dumps(asdict(load_scene()), sort_keys=True))"
    results = [
        subprocess.check_output(
            [sys.executable, "-c", code], cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": seed}
        )
        for seed in ("1", "42")
    ]
    assert results[0] == results[1]
    assert json.loads(results[0]) == json.loads(json.dumps(asdict(load_scene(ROOT))))
