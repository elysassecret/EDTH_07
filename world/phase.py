"""Seeded cold-start placement along the cables initially assigned to each sweeper.

This varies starting positions, not historical sensor visits or battery usage. Seed 1
retains the original demo positions; other seeds select a deterministic metre offset.
Pickets/relay stay at their stations. Placement is independent of policy and speed.
"""

import hashlib
from dataclasses import dataclass
from itertools import pairwise

from contract.geo import dist
from contract.mission import Mission, Point

STRATEGY = "cold-seeded-cable-offsets-v1"


@dataclass(frozen=True, slots=True)
class Placement:
    point: Point
    task: str
    offset_m: int
    route_length_m: int


def placements(mission: Mission, seed: int, enabled: bool = True) -> dict[int, Placement]:
    owners = dict(mission.initial)
    result = {}
    for boat in sorted(mission.boats):
        assigned = sorted(
            (task for task in mission.tasks if owners.get(task.id) == boat),
            key=lambda task: task.id,
        )
        if not assigned:
            raise ValueError(f"boat {boat} has no initial task for placement")
        sweeps = [task for task in assigned if task.id.startswith("seg:")]
        if not sweeps:
            result[boat] = Placement(assigned[0].pts[0], assigned[0].id, 0, 0)
            continue
        edges = [
            (task.id, a, b, dist(a, b)) for task in sweeps for a, b in pairwise(task.pts) if a != b
        ]
        total = sum(length for _, _, _, length in edges)
        if total <= 0:
            raise ValueError(f"boat {boat} has no nonzero cable length for placement")
        offset = 0
        if enabled and seed != 1:
            digest = hashlib.sha256(f"{STRATEGY}:{seed}:{boat}".encode()).digest()
            offset = int.from_bytes(digest[:8], "big") % total
        remaining = offset
        for task_id, a, b, length in edges:
            if remaining < length:
                point = (
                    a[0] + (b[0] - a[0]) * remaining // length,
                    a[1] + (b[1] - a[1]) * remaining // length,
                )
                result[boat] = Placement(point, task_id, offset, total)
                break
            remaining -= length
    return result
