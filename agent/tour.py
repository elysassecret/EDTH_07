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
SPROGO_LANDFALL = (-2278, -7893)
SPROGO_OFFSHORE = (-2293, -7950)
KORSOR_SHORE = (8237, -7605)
KORSOR_HARBOUR = (8195, -7620)

BARRIERS: tuple[tuple[Point, ...], ...] = (
    (
        (-3750, -8550),
        (-2850, -8120),
        (-2580, -8060),
        (-2290, -7940),
        (-2150, -7900),
        (-2000, -8120),
        (-1350, -7850),
        (-700, -7600),
        (-120, -7500),
        (-120, -6150),
        (-2600, -6150),
        (-3750, -7850),
        (-3750, -8550),
    ),
    ((780, -6950), (1080, -6950), (1080, -6580), (780, -6580), (780, -6950)),
    ((3460, -6300), (3740, -6300), (3740, -6030), (3460, -6030), (3460, -6300)),
    (
        (4950, 9500),
        (4950, 1500),
        (6650, -3500),
        (5650, -6050),
        (7900, -7420),
        (8165, -7540),
        (8350, -7540),
    ),
    ((7980, -7840), (8380, -8350)),
)

WATER_WPS: tuple[Point, ...] = (
    (-3950, -6050),
    (-3950, -8700),
    (-1900, -8300),
    (50, -7650),
    (50, -5950),
    (4200, -5800),
    (5200, -6650),
    (7800, -7720),
)


def _ccw(a: Point, b: Point, c: Point) -> bool:
    return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])


def _seg_hit(p1: Point, p2: Point, q1: Point, q2: Point) -> bool:
    if p1 == q1 or p1 == q2 or p2 == q1 or p2 == q2:
        return False
    return (_ccw(p1, q1, q2) != _ccw(p2, q1, q2)) and (_ccw(p1, p2, q1) != _ccw(p1, p2, q2))


def _clear_water(a: Point, b: Point) -> bool:
    return not any(_seg_hit(a, b, u, v) for poly in BARRIERS for u, v in pairwise(poly))


def route_water_path(pos: Point, target: Point) -> list[Point]:
    """Shortest water-only waypoint chain around Sprogø, East Bridge piers and Halsskov."""
    start = SPROGO_OFFSHORE if pos == SPROGO_LANDFALL else pos
    goal = (
        SPROGO_OFFSHORE
        if target == SPROGO_LANDFALL
        else KORSOR_HARBOUR
        if target == KORSOR_SHORE
        else target
    )
    start = next((w for w in WATER_WPS if dist(start, w) <= 20), start)
    if _clear_water(start, goal):
        return [pos, goal]
    wps = [w for w in WATER_WPS if w != start and w != goal]
    nodes = [start, *wps, goal]
    n = len(nodes)
    inf = 10**12
    d = [inf] * n
    prv = [-1] * n
    vis = [False] * n
    d[0] = 0
    for _ in range(n):
        u = min((i for i in range(n) if not vis[i]), key=lambda i: d[i], default=-1)
        if u == -1 or d[u] == inf or u == n - 1:
            break
        vis[u] = True
        for v in range(1, n):
            if not vis[v] and _clear_water(nodes[u], nodes[v]):
                nd = d[u] + dist(nodes[u], nodes[v])
                if nd < d[v]:
                    d[v] = nd
                    prv[v] = u
    if prv[n - 1] == -1:
        return [pos, goal]
    out: list[Point] = []
    cur = n - 1
    while cur > 0:
        out.append(nodes[cur])
        cur = prv[cur]
    return [pos, *reversed(out)]


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
