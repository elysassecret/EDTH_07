"""Public approximate cable geometry; integer-metre mission for the agents.

Shapely is used only while building the scene. Rounded contract coordinates are
shared by the mission, samples and subsequent world state.
"""

import json
import math
import tomllib
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.geometry import Point as GeometryPoint
from shapely.ops import substring

from contract.geo import to_xy
from contract.mission import Mission, Point, TaskSpec

CABLE_IDS = {
    "HVDC_Storebaelt_I": "H",
    "Great_Belt_1_fibre": "G",
    "MV_60kV_Sprogo_Funen": "M",
}


@dataclass(frozen=True, slots=True)
class RouteSample:
    task: str
    offset_m: int
    point: Point


@dataclass(frozen=True, slots=True)
class Scene:
    mission: Mission
    boundary: tuple[Point, ...]
    samples: tuple[RouteSample, ...]


def _points(line: LineString) -> tuple[Point, ...]:
    points = []
    for x, y in line.coords:
        point = (round(x), round(y))
        if not points or points[-1] != point:
            points.append(point)
    if len(points) < 2:
        raise ValueError("route collapses after rounding to metres")
    return tuple(points)


def split_route(line: LineString, max_m: int) -> tuple[tuple[Point, ...], ...]:
    """Equal-length pieces in source direction, preserving intermediate vertices."""
    if max_m < 2 or line.is_empty or line.length == 0:
        raise ValueError("route must have length and segment limit must be at least 2 m")
    count = math.ceil(line.length / max_m)
    while True:
        pieces = tuple(
            _points(substring(line, line.length * i / count, line.length * (i + 1) / count))
            for i in range(count)
        )
        # Rounding can lengthen a piece: check the geometry actually handed to agents.
        if all(LineString(points).length <= max_m for points in pieces):
            return pieces
        count += 1


def sample_route(task: TaskSpec, step_m: int) -> tuple[RouteSample, ...]:
    """Sample from offset zero every step; the terminal remainder is not a full sample."""
    if step_m <= 0:
        raise ValueError("sample step must be positive")
    line = LineString(task.pts)
    samples = []
    for offset in range(0, math.ceil(line.length), step_m):
        point = line.interpolate(offset)
        samples.append(RouteSample(task.id, offset, (round(point.x), round(point.y))))
    return tuple(samples)


def load_scene(root: str | Path = ".") -> Scene:
    """Load B's scene config and build a fixed-order Mission; no AIS file needed."""
    root = Path(root)
    with (root / "config/scene.toml").open("rb") as handle:
        config = tomllib.load(handle)
    with (root / config["file"]).open(encoding="utf-8") as handle:
        data = json.load(handle)

    corners = data["box"]["corners_wgs84"]
    boundary = tuple(to_xy(corners[k]["lat"], corners[k]["lon"]) for k in ("NE", "NW", "SW", "SE"))
    box = Polygon(boundary)
    tasks = []
    for cable in config["scenario_lines"]:
        line = LineString(to_xy(lat, lon) for lat, lon in data["cables"][cable]["lat_lon"])
        clipped = line.intersection(box)
        # Multiple disconnected pieces need an explicit task-ID policy, not an implicit join.
        if not isinstance(clipped, LineString) or clipped.is_empty:
            raise ValueError(f"{cable}: expected one connected cable inside the box")
        for index, points in enumerate(split_route(clipped, config["segment_max_m"])):
            tasks.append(TaskSpec(f"seg:{CABLE_IDS[cable]}:{index}", points))
    tasks.sort(key=lambda task: task.id)
    samples = tuple(
        sample for task in tasks for sample in sample_route(task, config["sample_step_m"])
    )
    initial = [(task.id, 2 if task.id.startswith("seg:H:") else 1) for task in tasks]
    for task_id, station, owner in (
        ("pick:N", "picket_n", 3),
        ("pick:S", "picket_s", 4),
        ("relay", "relay_station", 5),
    ):
        tasks.append(TaskSpec(task_id, (to_xy(*config[station]),)))
        initial.append((task_id, owner))

    bins = data["lane_measured_from_ais"]["centreline"]
    lane = tuple(to_xy(entry["lat"], entry["lon"]) for entry in bins)
    lane_half_m = config["lane_half_m"]
    if lane_half_m <= 0:
        raise ValueError("lane half-width must be positive")
    lane_line = LineString(lane)
    for task in tasks:
        if (
            not task.id.startswith("seg:")
            and lane_line.distance(GeometryPoint(task.pts[0])) <= lane_half_m
        ):
            raise ValueError(f"{task.id}: station lies in the lane band")
    return Scene(
        Mission(
            (1, 2, 3, 4, 5),
            tuple(tasks),
            tuple(initial),
            to_xy(*config["shore"]),
            lane,
            lane_half_m,
        ),
        boundary,
        samples,
    )


def load_mission(root: str | Path = ".") -> Mission:
    """Convenience entry point for agent/server integration."""
    return load_scene(root).mission
