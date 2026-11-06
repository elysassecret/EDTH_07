"""Missions for agent tests. Test data only; world/routes.py (B) builds the real Mission.

The scene-like mission uses segment ends from the scratch model in agent/PLAN.md section 8.1
(three scenario cables clipped to the box, split into <= 5 km pieces, straight lines).
"""
import json
from pathlib import Path

from contract.geo import to_xy
from contract.mission import Mission, TaskSpec

SEGS = {
    "seg:H:0": ((-8682, 5417), (-3947, 7029)),
    "seg:H:1": ((-3947, 7029), (788, 8641)),
    "seg:G:0": ((-5709, -5687), (-2381, -5197)),
    "seg:G:1": ((-2381, -5197), (1039, -5087)),
    "seg:G:2": ((1039, -5087), (4439, -4976)),
    "seg:M:0": ((-2278, -7893), (-4544, -10025)),
}
SHORE_XY = (8237, -7605)
RELAY_XY = (-1580, 556)
PICK_N, PICK_S = (-5809, 6427), (853, -5081)
C07 = (-8180, 5615)

INITIAL = (("seg:G:0", 1), ("seg:G:1", 1), ("seg:G:2", 1), ("seg:M:0", 1),
           ("seg:H:0", 2), ("seg:H:1", 2), ("pick:N", 3), ("pick:S", 4), ("relay", 5))

# Where each boat is at t = 0: on its tour or at its station.
START = {1: SEGS["seg:G:1"][0], 2: SEGS["seg:H:0"][1], 3: PICK_N, 4: PICK_S, 5: RELAY_XY}


def lane() -> tuple[tuple[int, int], ...]:
    scene = json.loads(Path("data/scene-coordinates.json").read_text())
    return tuple(to_xy(p["lat"], p["lon"]) for p in scene["lane_measured_from_ais"]["centreline"])


def scene_mission() -> Mission:
    tasks = tuple(TaskSpec(k, v) for k, v in SEGS.items()) + (
        TaskSpec("pick:N", (PICK_N,)), TaskSpec("pick:S", (PICK_S,)), TaskSpec("relay", (RELAY_XY,)))
    return Mission(boats=(1, 2, 3, 4, 5), tasks=tasks, initial=INITIAL, shore=SHORE_XY,
                   lane=lane(), lane_half_m=650)


def line_mission() -> Mission:
    """Three boats on one 6 km line, 2 km apart; small and fast for unit tests."""
    tasks = (TaskSpec("seg:A:0", ((0, 0), (3000, 0))), TaskSpec("seg:A:1", ((3000, 0), (6000, 0))),
             TaskSpec("relay", ((3000, 1000),)))
    return Mission(boats=(1, 2, 3), tasks=tasks,
                   initial=(("seg:A:0", 1), ("seg:A:1", 2), ("relay", 3)),
                   shore=(3000, -5000), lane=((0, 20_000), (6000, 20_000)), lane_half_m=650)
