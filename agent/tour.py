"""Patrol tours: integer geometry, cycle length, cheapest insertion, waypoint follower. Owner: A.

A tour is a closed loop of legs (task_id, reversed). Each leg sweeps one cable segment end to
end; between legs the boat transits in a straight line. One segment alone is swept back and
forth, so its cycle is twice its length.
"""
from itertools import pairwise

from contract.geo import dist

Point = tuple[int, int]
Leg = tuple[str, bool]
ARRIVE_M = 10  # the world moves at most 2.3 m per tick


def length(pts: tuple[Point, ...]) -> int:
    return sum(dist(a, b) for a, b in pairwise(pts))


class Tours:
    """Geometry of the mission's segments, shared by everything that plans tours."""

    def __init__(self, segs: dict[str, tuple[Point, ...]]):
        self.pts = segs
        self.len = {k: length(v) for k, v in segs.items()}

    def way(self, leg: Leg) -> tuple[Point, ...]:
        task, rev = leg
        return self.pts[task][::-1] if rev else self.pts[task]

    def cycle_m(self, legs: list[Leg]) -> int:
        total = 0
        for i, leg in enumerate(legs):
            nxt = self.way(legs[(i + 1) % len(legs)])
            total += self.len[leg[0]] + dist(self.way(leg)[-1], nxt[0])
        return total

    def insert(self, legs: list[Leg], task: str) -> list[Leg]:
        """Cheapest insertion over every position and both directions; ties: first found."""
        best, best_c = None, None
        for i in range(len(legs) + 1):
            for rev in (False, True):
                cand = legs[:i] + [(task, rev)] + legs[i:]
                c = self.cycle_m(cand)
                if best_c is None or c < best_c:
                    best, best_c = cand, c
        return best

    def reach_m(self, pos: Point, task: str) -> int:
        p = self.pts[task]
        return min(dist(pos, p[0]), dist(pos, p[-1]))


class Follower:
    """Walks a tour waypoint by waypoint. Keeps its place when legs are added or removed."""

    def __init__(self, tours: Tours):
        self.tours = tours
        self.legs: list[Leg] = []
        self.i = 0  # current leg
        self.j = 0  # next waypoint in that leg

    def set_legs(self, legs: list[Leg], pos: Point) -> None:
        cur = self.legs[self.i][0] if self.legs else None
        self.legs = legs
        found = [k for k, leg in enumerate(legs) if leg[0] == cur]
        if found:
            self.i = found[0]
        else:
            self.start_nearest(pos)

    def start_nearest(self, pos: Point) -> None:
        """Head for the nearest waypoint of the tour (used at start and after losing a leg)."""
        best = None
        for i, leg in enumerate(self.legs):
            for j, p in enumerate(self.tours.way(leg)):
                d = dist(pos, p)
                if best is None or d < best[0]:
                    best = (d, i, j)
        self.i, self.j = (best[1], best[2]) if best else (0, 0)

    def target(self, pos: Point) -> Point | None:
        if not self.legs:
            return None
        way = self.tours.way(self.legs[self.i])
        if dist(pos, way[self.j]) <= ARRIVE_M:
            self.j += 1
            if self.j == len(way):
                self.i, self.j = (self.i + 1) % len(self.legs), 0
            way = self.tours.way(self.legs[self.i])
        return way[self.j]
