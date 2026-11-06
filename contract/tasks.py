"""Task records, the merge rule, and the mission geometry handed to agents.

Merge is a per-task last-writer-wins register with a logical counter and a
replica-ID tie-break (RFC 677 lineage). key = (ver, state, -bid, owner, deputy):
higher version wins; at equal version a claim beats a release and a veto beats
both; at equal state the cheaper bid wins; then the higher boat ID, then the
higher deputy ID so the order is total and merge is commutative.
It is not CBBA and not consensus. Guarantee: eventual convergence per
connected group, given delivery.
"""
from __future__ import annotations

from dataclasses import dataclass

from .constants import CLAIMED, RELEASED, VETOED


@dataclass(frozen=True, slots=True)
class Rec:
    task: str
    ver: int
    state: int
    bid: int
    owner: int
    deputy: int = 0   # 0 = none

    def tup(self):
        return [self.task, self.ver, self.state, self.bid, self.owner, self.deputy]

    @staticmethod
    def from_tup(t) -> "Rec":
        return Rec(str(t[0]), int(t[1]), int(t[2]), int(t[3]), int(t[4]), int(t[5]))


def key(r: Rec):
    return (r.ver, r.state, -r.bid, r.owner, r.deputy)


def merge(a: Rec, b: Rec) -> Rec:
    return a if key(a) >= key(b) else b


KIND_ORDER = {"relay": 1, "contact": 2, "cue": 3, "seg": 4, "pick": 5}


def kind(task: str) -> str:
    return task.split(":", 1)[0]


def bid_order(task: str):
    return (KIND_ORDER.get(kind(task), 9), task)


@dataclass(frozen=True, slots=True)
class TaskGeom:
    """Geometry of a task in local metres (x east, y north)."""
    task: str
    kind: str
    points: tuple[tuple[float, float], ...]   # polyline for seg; one point otherwise
    length_m: float = 0.0
    t_cross_ms: int = 0        # cue only: predicted crossing time
    expires_ms: int = 0        # cue only


@dataclass(frozen=True, slots=True)
class Mission:
    tasks: dict[str, TaskGeom]
    initial_owner: dict[str, int]
    shore_xy: tuple[float, float]
    relay_xy: tuple[float, float]
    boats: tuple[int, ...]
    cable_samples: tuple[tuple[float, float], ...]   # every sample point, for "over a cable"
    lane: tuple[tuple[float, float], ...]            # lane centreline

    def initial_records(self) -> list[Rec]:
        return [Rec(t, 1, CLAIMED if o else RELEASED, 0, o, 0) for t, o in sorted(self.initial_owner.items())]


__all__ = ["Rec", "key", "merge", "kind", "bid_order", "TaskGeom", "Mission", "CLAIMED", "RELEASED", "VETOED"]
