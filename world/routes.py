"""Scene loading: cables clipped to the box, split to <= 5 km segments, 100 m samples.

Builds the Mission handed to agents (geometry only) and the Scene used by the
world and evaluator (segments with samples, lane band, stations).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from contract.config import ROOT
from contract.tasks import Mission, TaskGeom

from . import geo


@dataclass(slots=True)
class Segment:
    task: str
    cable: str
    letter: str
    index: int
    points: list[tuple[float, float]]
    length_m: float
    samples: list[tuple[float, float]]
    sample_offset: int = 0   # index of first sample in the global array


@dataclass(slots=True)
class Scene:
    raw: dict
    cables: dict[str, list[list[tuple[float, float]]]]   # all cables, clipped pieces (xy)
    segments: list[Segment]
    samples: list[tuple[float, float]]
    lane: list[tuple[float, float]]
    lane_p5: list[tuple[float, float]]
    lane_p95: list[tuple[float, float]]
    lane_cross: dict[str, tuple[float, float]]
    shore_xy: tuple[float, float]
    relay_xy: tuple[float, float]
    picket_n: tuple[float, float]
    picket_s: tuple[float, float]
    seg_by_task: dict[str, Segment] = field(default_factory=dict)

    def mission(self, boats=(1, 2, 3, 4, 5)) -> Mission:
        tasks: dict[str, TaskGeom] = {}
        for s in self.segments:
            tasks[s.task] = TaskGeom(s.task, "seg", tuple(s.points), s.length_m)
        tasks["pick:N"] = TaskGeom("pick:N", "pick", (self.picket_n,))
        tasks["pick:S"] = TaskGeom("pick:S", "pick", (self.picket_s,))
        tasks["relay"] = TaskGeom("relay", "relay", (self.relay_xy,))
        owners = {"relay": 5, "pick:N": 3, "pick:S": 4}
        for s in self.segments:
            owners[s.task] = 2 if s.letter == "H" else 1
        return Mission(tasks, owners, self.shore_xy, self.relay_xy, tuple(boats),
                       tuple(self.samples), tuple(self.lane))


def load_scene(cfg: dict) -> Scene:
    sc = cfg["scene"]
    p = Path(sc["file"])
    if not p.is_absolute():
        p = ROOT / p
    raw = json.loads(p.read_text(encoding="utf-8"))
    cables: dict[str, list[list[tuple[float, float]]]] = {}
    for name, c in raw["cables"].items():
        pts = [geo.ll_to_xy(lat, lon) for lat, lon in c["lat_lon"]]
        cables[name] = geo.clip_polyline_xy(pts)
    segments: list[Segment] = []
    samples: list[tuple[float, float]] = []
    for name in sc["scenario_lines"]:
        letter = sc["line_letters"][name]
        pieces = cables[name]
        # join pieces (a cable normally yields one piece inside the box)
        pts = [q for piece in pieces for q in piece]
        idx = 0
        for part in geo.split_polyline(pts, float(sc["segment_max_m"])):
            L = geo.polyline_length(part)
            smp = geo.samples_along(part, float(sc["sample_step_m"]))
            seg = Segment(f"seg:{letter}:{idx}", name, letter, idx, part, L, smp, len(samples))
            samples.extend(smp)
            segments.append(seg)
            idx += 1
    lane_raw = raw["lane_measured_from_ais"]["centreline"]
    lane = [geo.ll_to_xy(r["lat"], r["lon"]) for r in lane_raw]
    # p5/p95 band: offset across the box frame (v axis)
    lane_p5, lane_p95 = [], []
    for r in lane_raw:
        u = r["u_km"] * 1000.0
        lane_p5.append(geo.uv_to_xy(u, r["v_p5_km"] * 1000.0))
        lane_p95.append(geo.uv_to_xy(u, r["v_p95_km"] * 1000.0))
    cross = {k: geo.ll_to_xy(*v) for k, v in raw.get("lane_cable_points_lat_lon", {}).items()}
    scene = Scene(raw, cables, segments, samples, lane, lane_p5, lane_p95, cross,
                  geo.ll_to_xy(*sc["shore"]), geo.ll_to_xy(*sc["relay_station"]),
                  geo.ll_to_xy(*sc["picket_n"]), geo.ll_to_xy(*sc["picket_s"]))
    scene.seg_by_task = {s.task: s for s in segments}
    return scene


def lane_offset_m(scene: Scene, p: tuple[float, float]) -> float:
    return geo.point_polyline_dist(p, scene.lane)


def nearest_cable_m(scene: Scene, p: tuple[float, float], cables: list[str] | None = None) -> tuple[float, str]:
    best, name = 1e18, ""
    for n, pieces in sorted(scene.cables.items()):
        if cables and n not in cables:
            continue
        for piece in pieces:
            d = geo.point_polyline_dist(p, piece)
            if d < best:
                best, name = d, n
    return best, name
