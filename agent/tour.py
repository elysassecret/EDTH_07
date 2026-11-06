"""Patrol tour: ordered segments with direction, cheapest insertion, cycle length."""
from __future__ import annotations

import math


def _d(p, q) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def entry_points(a, entry):
    task, rev = entry
    pts = a.mission.tasks[task].points
    return pts[::-1] if rev else pts


def cycle_length_m(a, tour: list) -> float:
    if not tour:
        return 0.0
    if len(tour) == 1:
        return 2.0 * a.mission.tasks[tour[0][0]].length_m
    total = 0.0
    n = len(tour)
    for i, e in enumerate(tour):
        pts = entry_points(a, e)
        total += a.mission.tasks[e[0]].length_m
        nxt = entry_points(a, tour[(i + 1) % n])
        total += _d(pts[-1], nxt[0])
    return total


def cheapest_insertion(a, tour: list, task: str):
    """Returns (cycle_m, new_tour) for the cheapest insertion of task."""
    best = None
    for pos in range(len(tour) + 1):
        for rev in (False, True):
            cand = tour[:pos] + [(task, rev)] + tour[pos:]
            c = cycle_length_m(a, cand)
            if best is None or c < best[0] - 1e-9:
                best = (c, cand)
    return best


def remove_task(tour: list, task: str) -> list:
    return [e for e in tour if e[0] != task]


def removal_that_lowers_max(a, my_tour: list, lo_tour: list):
    """Segment whose move from me to lo lowers max(cycle_me, cycle_lo) the most, or None."""
    my_c = cycle_length_m(a, my_tour)
    best = None
    for e in my_tour:
        mine = cycle_length_m(a, remove_task(my_tour, e[0]))
        theirs, _ = cheapest_insertion(a, lo_tour, e[0])
        new_max = max(mine, theirs)
        if new_max < my_c - 1e-9 and (best is None or new_max < best[0]):
            best = (new_max, e[0], theirs)
    return best


class Follower:
    """Waypoint follower over the tour. Sweeps back and forth on a single segment."""

    def __init__(self):
        self.idx = 0
        self.wp = 0
        self.rev_single = False
        self.current_task: str | None = None

    def resync(self, a, xy):
        """Tour changed: keep the current entry if present, else nearest waypoint of entry 0."""
        tour = a.tour
        if not tour:
            self.idx = self.wp = 0
            self.current_task = None
            return
        if self.current_task is not None:
            for i, e in enumerate(tour):
                if e[0] == self.current_task:
                    self.idx = i
                    return
        best = None
        for i, e in enumerate(tour):
            pts = entry_points(a, e)
            for j, p in enumerate(pts):
                d = _d(p, xy)
                if best is None or d < best[0]:
                    best = (d, i, j)
        _, self.idx, self.wp = best
        self.current_task = tour[self.idx][0]

    def _pts(self, a):
        pts = entry_points(a, a.tour[self.idx])
        if len(a.tour) == 1 and self.rev_single:
            pts = pts[::-1]
        return pts

    def target(self, a, xy, arrive_m: float):
        tour = a.tour
        if not tour:
            return None
        if self.idx >= len(tour):
            self.idx = 0
            self.wp = 0
        self.current_task = tour[self.idx][0]
        pts = self._pts(a)
        if self.wp >= len(pts):
            self.wp = len(pts) - 1
        while _d(pts[self.wp], xy) <= arrive_m:
            self.wp += 1
            if self.wp >= len(pts):
                if len(tour) == 1:
                    self.rev_single = not self.rev_single
                else:
                    self.idx = (self.idx + 1) % len(tour)
                self.wp = 0
                self.current_task = tour[self.idx][0]
                pts = self._pts(a)
                # skip the first waypoint if we are already on it
                if _d(pts[0], xy) <= arrive_m and len(pts) > 1:
                    self.wp = 1
                return pts[self.wp]
        return pts[self.wp]


def loop_polyline(a, tour: list) -> list:
    """The closed loop a boat drives: segment points joined by transits, closed at the end."""
    pts: list = []
    for e in tour:
        pts.extend(entry_points(a, e))
    if len(tour) == 1:
        pts = pts + pts[::-1][1:]
    elif pts:
        pts.append(pts[0])
    return pts


def _walk(pts, s):
    """Point at arc length s along pts and the index of the next vertex."""
    acc = 0.0
    for i in range(len(pts) - 1):
        d = _d(pts[i], pts[i + 1])
        if s <= acc + d:
            f = 0.0 if d == 0 else (s - acc) / d
            return (pts[i][0] + f * (pts[i + 1][0] - pts[i][0]), pts[i][1] + f * (pts[i + 1][1] - pts[i][1])), i + 1
        acc += d
    return pts[-1], len(pts) - 1


def place_on_loop(a, frac: float):
    """Put the follower at fraction frac of the loop and return the matching position."""
    f = a.follower
    tour = a.tour
    if not tour:
        return None
    if len(tour) == 1:
        pts = list(entry_points(a, tour[0]))
        L = sum(_d(p, q) for p, q in zip(pts[:-1], pts[1:]))
        s = frac * 2 * L
        if s <= L:
            xy, nxt = _walk(pts, s)
            f.idx, f.wp, f.rev_single = 0, nxt, False
        else:
            xy, nxt = _walk(pts[::-1], s - L)
            f.idx, f.wp, f.rev_single = 0, nxt, True
        f.current_task = tour[0][0]
        return xy
    pieces = []   # (kind, entry_idx, pts)
    n = len(tour)
    for i, e in enumerate(tour):
        pts = list(entry_points(a, e))
        pieces.append(("seg", i, pts))
        nxt = entry_points(a, tour[(i + 1) % n])
        pieces.append(("transit", (i + 1) % n, [pts[-1], nxt[0]]))
    total = sum(sum(_d(p, q) for p, q in zip(pts[:-1], pts[1:])) for _, _, pts in pieces)
    s = frac * total
    for kind_, i, pts in pieces:
        L = sum(_d(p, q) for p, q in zip(pts[:-1], pts[1:]))
        if s <= L:
            xy, nxt = _walk(pts, s)
            if kind_ == "seg":
                f.idx, f.wp = i, min(nxt, len(pts) - 1)
            else:
                f.idx, f.wp = i, 0
            f.current_task = tour[f.idx][0]
            return xy
        s -= L
    xy = entry_points(a, tour[0])[0]
    f.idx, f.wp, f.current_task = 0, 0, tour[0][0]
    return xy
