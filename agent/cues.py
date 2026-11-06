"""AIS cues (P1): dead reckoning to the first cable hit, filter, cue task through the same auction.

Runs on each boat, only on pings inside its modelled reception range.
A cue is "a cue for a look", never "suspicious". Military and state vessels
are report-only: no task is opened, the fleet keeps clear.
"""
from __future__ import annotations

import math

from contract.constants import CLOSED, CUE, CUE_TTL, KN_TO_MPS, PATROL, RELEASED
from contract.tasks import Rec

from . import table as T

EXCLUDE = {"Pleasure", "Sailing", "SAR", "Pilot", "Law enforcement", "Military"}
REPORT_ONLY = {"Military", "Law enforcement"}


def _d(p, q) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def _seg_intersect(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]), t)
    return None


def lane_offset_m(a, p) -> float:
    lane = a.mission.lane
    best = 1e18
    for q1, q2 in zip(lane[:-1], lane[1:]):
        dx, dy = q2[0] - q1[0], q2[1] - q1[1]
        l2 = dx * dx + dy * dy
        tt = 0.0 if l2 == 0 else max(0.0, min(1.0, ((p[0] - q1[0]) * dx + (p[1] - q1[1]) * dy) / l2))
        best = min(best, math.hypot(p[0] - (q1[0] + tt * dx), p[1] - (q1[1] + tt * dy)))
    return best


def first_cable_hit(a, x, y, sog_kn, cog_deg, horizon_s: int = 600):
    v = sog_kn * KN_TO_MPS
    if v < 0.05:
        return None
    r = math.radians(cog_deg)
    ex, ey = x + math.sin(r) * v * horizon_s, y + math.cos(r) * v * horizon_s
    best = None
    for task in sorted(a.mission.tasks):
        g = a.mission.tasks[task]
        if g.kind != "seg":
            continue
        pts = g.points
        for p, q in zip(pts[:-1], pts[1:]):
            hit = _seg_intersect((x, y), (ex, ey), p, q)
            if hit and (best is None or hit[2] < best[0]):
                best = (hit[2], (hit[0], hit[1]), task.split(":")[1])
    if best is None:
        return None
    frac, pt, letter = best
    return {"x": pt[0], "y": pt[1], "dt_ms": int(frac * horizon_s * 1000), "cable": letter}


def on_ais(a, pings, t: int) -> None:
    for p in sorted(pings, key=lambda p: (p.track, p.t_ms)):
        a.ais_seen[p.track] = {"x": round(p.x), "y": round(p.y), "sog": p.sog_kn, "cog": p.cog_deg,
                               "t": p.t_ms, "type": p.ship_type}
        hit = first_cable_hit(a, p.x, p.y, p.sog_kn, p.cog_deg)
        if not hit:
            continue
        unusual = p.sog_kn < 3.0 or lane_offset_m(a, (hit["x"], hit["y"])) > 1000.0
        if not unusual:
            continue
        if p.ship_type in REPORT_ONLY:
            key = f"report:{p.track}:{hit['cable']}"
            if key not in a.reported:
                a.reported[key] = t
                a.log("report_only", {"track": p.track, "type": p.ship_type, "cable": hit["cable"]}, t)
            continue
        if p.ship_type in EXCLUDE:
            continue
        task = f"cue:{p.track}:{hit['cable']}"
        if task in a.table:
            continue
        geom = {"x": round(hit["x"]), "y": round(hit["y"]), "t_cross": t + hit["dt_ms"],
                "expires": t + CUE_TTL, "track": p.track, "type": p.ship_type, "by": a.me}
        a.cue_geoms[task] = geom
        a.publish(Rec(task, 1, RELEASED, 0, 0, 0), t)
        a.send("CONTACT", {"cue": task, "geom": geom}, t)
        a.log("cue_open", {"task": task, "type": p.ship_type, "cable": hit["cable"]}, t)


def cue_tick(a, t: int):
    task = a.cue_task
    rec = a.table.get(task)
    g = a.cue_geoms.get(task)
    if rec is None or g is None or rec.state != 1 or rec.owner != a.me:
        a.mode, a.cue_task = PATROL, None
        a.follower.resync(a, a.xy)
        return None
    if _d(a.xy, (g["x"], g["y"])) <= a.r_verify_m:
        a.publish(Rec(task, T.max_ver(a, task) + 1, CLOSED, 0, a.me, 0), t)
        a.log("cue_look", {"task": task, "result": "verification look done"}, t)
        a.mode, a.cue_task = PATROL, None
        a.follower.resync(a, a.xy)
        return None
    if t > g["expires"] + 120_000:
        a.publish(Rec(task, T.max_ver(a, task) + 1, CLOSED, 0, a.me, 0), t)
        a.log("cue_expired", {"task": task}, t)
        a.mode, a.cue_task = PATROL, None
        a.follower.resync(a, a.xy)
        return None
    return (g["x"], g["y"])


def expire_cues(a, t: int) -> None:
    for task in sorted(a.table):
        if not task.startswith("cue:"):
            continue
        r = a.table[task]
        g = a.cue_geoms.get(task)
        if r.state == RELEASED and g is not None and t > g["expires"]:
            a.publish(Rec(task, T.max_ver(a, task) + 1, CLOSED, 0, a.me, 0), t)
