"""Patrol tours: integer geometry, cycle length, cheapest insertion, waypoint follower. Owner: A.

A tour is a closed loop of legs (task_id, reversed). Each leg sweeps one cable segment end to
end; between legs the boat transits in a straight line. One segment alone is swept back and
forth, so its cycle is twice its length.
"""
from itertools import pairwise

from agent import water
from contract.geo import dist

Point = tuple[int, int]
Leg = tuple[str, bool]
ARRIVE_M = 10  # the world moves at most 2.3 m per tick
SPROGO_LANDFALL = (-2278, -7893)
SPROGO_OFFSHORE = (-2293, -7950)
KORSOR_SHORE = (8237, -7605)
KORSOR_HARBOUR = (8195, -7620)

def route_water_path(pos: Point, target: Point) -> list[Point]:
    """Water-only waypoint chain from pos to target around the real coastline (agent/water.py,
    from the map's land.geojson with a safety margin). Replaces the hand-drawn barriers, which
    let boats cut across Zealand north of Korsør and across Sprogø."""
    return water.path(pos, target)


def route_water(pos: Point, target: Point) -> Point:
    """Next water-only waypoint from pos toward target."""
    return route_water_path(pos, target)[1]


def length(pts: tuple[Point, ...]) -> int:
    return sum(dist(a, b) for a, b in pairwise(pts))


def dist_to_line(p: Point, pts: tuple[Point, ...]) -> int:
    """Shortest distance from a point to a polyline, integer maths only."""
    best = dist(p, pts[0])
    for a, b in pairwise(pts):
        dx, dy = b[0] - a[0], b[1] - a[1]
        den = dx * dx + dy * dy
        if den == 0:
            continue
        num = min(max((p[0] - a[0]) * dx + (p[1] - a[1]) * dy, 0), den)
        best = min(best, dist(p, (a[0] + dx * num // den, a[1] + dy * num // den)))
    return best


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


class Visits:
    """When each sample point of each segment (every STEP_M from its start) was last within
    r of a position this boat knows of: its own, or a peer's heartbeat. -1 = never."""

    STEP_M = 100

    def __init__(self, segs: dict[str, tuple[Point, ...]], r: int):
        self.r, self.pts = r, segs
        self.samples = {k: every(v, self.STEP_M) for k, v in segs.items()}
        self.seen = {k: [-1] * len(v) for k, v in self.samples.items()}
        self.box = {k: (min(x for x, _ in v) - r, min(y for _, y in v) - r,
                        max(x for x, _ in v) + r, max(y for _, y in v) + r)
                    for k, v in self.samples.items() if v}
        self.lim = (r + 1) ** 2  # isqrt(d2) <= r exactly when d2 < (r + 1)^2

    def credit(self, pos: Point, t: int) -> None:
        """Runs every tick on every boat, so it skips far segments by bounding box and compares
        squared distances; the result is the same as dist(pos, sample) <= r."""
        x, y = pos
        for k, (x0, y0, x1, y1) in self.box.items():
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                continue
            seen = self.seen[k]
            for i, (px, py) in enumerate(self.samples[k]):
                if seen[i] < t and (px - x) ** 2 + (py - y) ** 2 < self.lim:
                    seen[i] = t

    def oldest(self, task: str) -> int:
        return min(self.seen[task])


def every(pts: tuple[Point, ...], step: int) -> list[Point]:
    """Points every `step` metres along a polyline from its start, endpoint excluded."""
    out, offset, walked = [], 0, 0
    for a, b in pairwise(pts):
        d = dist(a, b)
        while offset < walked + d:
            f = offset - walked
            out.append((a[0] + (b[0] - a[0]) * f // d, a[1] + (b[1] - a[1]) * f // d))
            offset += step
        walked += d
    return out


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
        wp = self.tours.way(self.legs[self.i])[self.j]
        if dist(pos, wp) <= (65 if wp == SPROGO_LANDFALL else ARRIVE_M):
            self.skip()
        return self.tours.way(self.legs[self.i])[self.j]

    def skip(self) -> None:
        """On to the next waypoint (arrived, or it cannot be reached right now)."""
        self.j += 1
        if self.j == len(self.tours.way(self.legs[self.i])):
            self.i, self.j = (self.i + 1) % len(self.legs), 0
