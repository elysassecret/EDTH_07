"""Equirectangular local frame about 55.40 N 11.00 E, and the rotated box frame.

xy: metres, x east, y north.
uv: metres along the box long axis (+SSE, bearing 165) and across it (+WSW).
"""
from __future__ import annotations

import math

LAT0, LON0 = 55.40, 11.00
KX = 63.212 * 1000.0    # m per degree longitude
KY = 111.190 * 1000.0   # m per degree latitude

BOX_CENTER = (55.405, 10.965)
BOX_BEARING = 165.0
BOX_LEN = 25_000.0
BOX_WID = 10_000.0


def ll_to_xy(lat: float, lon: float) -> tuple[float, float]:
    return ((lon - LON0) * KX, (lat - LAT0) * KY)


def xy_to_ll(x: float, y: float) -> tuple[float, float]:
    return (y / KY + LAT0, x / KX + LON0)


_cx, _cy = ll_to_xy(*BOX_CENTER)
_b = math.radians(BOX_BEARING)
# unit vector along the long axis (bearing 165 from north): east component sin, north component cos
_ux, _uy = math.sin(_b), math.cos(_b)
# across axis +WSW = rotate the long axis 90 deg clockwise... bearing 165+90 = 255 (WSW)
_vb = math.radians(BOX_BEARING + 90.0)
_vx, _vy = math.sin(_vb), math.cos(_vb)


def xy_to_uv(x: float, y: float) -> tuple[float, float]:
    dx, dy = x - _cx, y - _cy
    return (dx * _ux + dy * _uy, dx * _vx + dy * _vy)


def uv_to_xy(u: float, v: float) -> tuple[float, float]:
    return (_cx + u * _ux + v * _vx, _cy + u * _uy + v * _vy)


def in_box(x: float, y: float, margin: float = 0.0) -> bool:
    u, v = xy_to_uv(x, y)
    return abs(u) <= BOX_LEN / 2 + margin and abs(v) <= BOX_WID / 2 + margin


def box_corners_xy() -> list[tuple[float, float]]:
    hl, hw = BOX_LEN / 2, BOX_WID / 2
    return [uv_to_xy(-hl, -hw), uv_to_xy(-hl, hw), uv_to_xy(hl, hw), uv_to_xy(hl, -hw)]


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clip_segment_uv(p: tuple[float, float], q: tuple[float, float]):
    """Liang-Barsky clip of segment p-q (uv) to the box. Returns (p', q') or None."""
    hl, hw = BOX_LEN / 2, BOX_WID / 2
    x0, y0 = p
    dx, dy = q[0] - x0, q[1] - y0
    t0, t1 = 0.0, 1.0
    for pk, qk in ((-dx, x0 + hl), (dx, hl - x0), (-dy, y0 + hw), (dy, hw - y0)):
        if pk == 0:
            if qk < 0:
                return None
            continue
        r = qk / pk
        if pk < 0:
            if r > t1:
                return None
            if r > t0:
                t0 = r
        else:
            if r < t0:
                return None
            if r < t1:
                t1 = r
    return ((x0 + t0 * dx, y0 + t0 * dy), (x0 + t1 * dx, y0 + t1 * dy))


def clip_polyline_xy(points_xy: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    """Clip a polyline to the box. Returns a list of polylines (xy) inside the box."""
    pieces: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for a, b in zip(points_xy[:-1], points_xy[1:]):
        c = clip_segment_uv(xy_to_uv(*a), xy_to_uv(*b))
        if c is None:
            if cur:
                pieces.append(cur)
                cur = []
            continue
        pa, pb = uv_to_xy(*c[0]), uv_to_xy(*c[1])
        if not cur or dist(cur[-1], pa) > 1e-6:
            if cur:
                pieces.append(cur)
            cur = [pa]
        cur.append(pb)
    if cur:
        pieces.append(cur)
    return pieces


def polyline_length(pts) -> float:
    return sum(dist(a, b) for a, b in zip(pts[:-1], pts[1:]))


def point_along(pts, s: float) -> tuple[float, float]:
    """Point at arc length s along polyline pts (clamped)."""
    if s <= 0:
        return pts[0]
    for a, b in zip(pts[:-1], pts[1:]):
        d = dist(a, b)
        if s <= d:
            f = s / d if d > 0 else 0.0
            return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
        s -= d
    return pts[-1]


def split_polyline(pts, max_len: float) -> list[list[tuple[float, float]]]:
    """Split into n = ceil(L/max_len) pieces of equal arc length, keeping vertices."""
    L = polyline_length(pts)
    n = max(1, math.ceil(L / max_len - 1e-9))
    piece_len = L / n
    out: list[list[tuple[float, float]]] = []
    for i in range(n):
        s0, s1 = i * piece_len, (i + 1) * piece_len
        piece = [point_along(pts, s0)]
        acc = 0.0
        for a, b in zip(pts[:-1], pts[1:]):
            d = dist(a, b)
            if s0 < acc + d < s1 and acc + d > s0:
                piece.append(b)
            acc += d
        piece.append(point_along(pts, s1))
        out.append(piece)
    return out


def samples_along(pts, step: float) -> list[tuple[float, float]]:
    L = polyline_length(pts)
    n = max(1, int(round(L / step)))
    return [point_along(pts, L * i / n) for i in range(n + 1)]


def point_segment_dist(p, a, b) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def point_polyline_dist(p, pts) -> float:
    return min(point_segment_dist(p, a, b) for a, b in zip(pts[:-1], pts[1:]))


def seg_intersect(p1, p2, p3, p4):
    """Intersection point of segments p1p2 and p3p4, or None."""
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]), t)
    return None


def bearing_to_vec(course_deg: float) -> tuple[float, float]:
    r = math.radians(course_deg)
    return (math.sin(r), math.cos(r))
