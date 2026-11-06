"""Dark contact: dwell rule, contact task, scout holds, stand-off, keep-in-view, cannot-hold, Stop.

Policy (standing orders): watching is pre-approved. Everything beyond watching
waits for a person. No answer means no action; the boat keeps watching.
"""
from __future__ import annotations

import math

from contract.constants import (CLAIMED, CLOSED, CONTACT_STALE, HOLDING, PATROL, RELAY, RELEASED, SHADOWING,
                                SHORE_SILENCE)
from contract.tasks import Rec

from . import relay as relay_mod
from . import table as T


def _d(p, q) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def near_cable(a, xy) -> bool:
    best = min(_d(xy, s) for s in a.mission.cable_samples)
    return best <= a.cable_near_m


def contact_id(vid: str) -> str:
    return f"contact:{vid}"


def record_obs(a, cid: str, obs: dict) -> bool:
    """Newest observation time wins. Per-boat views are kept so a holder can see the owner's report."""
    views = a.contact_views.setdefault(cid, {})
    prev = views.get(obs["by"])
    if prev is None or obs["t"] > prev["t"]:
        views[obs["by"]] = obs
    cur = a.contact_obs.get(cid)
    if cur is None or obs["t"] > cur["t"] or (obs["t"] == cur["t"] and obs["by"] > cur["by"]):
        a.contact_obs[cid] = obs
        return True
    return False


def process_observations(a, observations, t: int) -> None:
    seen_now = set()
    for o in sorted(observations, key=lambda o: o.vid):
        cid = contact_id(o.vid)
        seen_now.add(o.vid)
        rec = a.table.get(cid)
        if rec is not None and rec.state != CLOSED:
            in_view = o.dist_m <= a.keep_in_view_m
            look = (a.mode == SHADOWING and a.shadow_cid == cid and o.dist_m <= a.standoff_floor_m + 50)
            obs = {"x": round(o.x), "y": round(o.y), "sog": round(o.sog_mps, 2), "cog": round(o.cog_deg),
                   "t": t, "by": a.me, "in_view": in_view, "ais": o.ais_match,
                   "name_read": look, "anchor_seen": look}
            if record_obs(a, cid, obs) and a.mode == SHADOWING and a.shadow_cid == cid and in_view and not a.shadow_in_view_sent:
                a.send("OBS", {"cid": cid, "obs": obs}, t)
                a.shadow_in_view_sent = True
            continue
        if rec is not None:
            continue                              # closed: ignore
        if o.ais_match or o.sog_mps > a.dwell_sog_mps or not near_cable(a, (o.x, o.y)):
            a.dwell.pop(o.vid, None)
            continue
        start = a.dwell.setdefault(o.vid, t)
        if t - start >= a.dwell_ms:
            open_contact(a, o, t)
    for vid in [v for v in a.dwell if v not in seen_now]:
        a.dwell.pop(vid)


def open_contact(a, o, t: int) -> None:
    cid = contact_id(o.vid)
    obs = {"x": round(o.x), "y": round(o.y), "sog": round(o.sog_mps, 2), "cog": round(o.cog_deg),
           "t": t, "by": a.me, "in_view": o.dist_m <= a.keep_in_view_m, "ais": False,
           "name_read": False, "anchor_seen": False}
    a.contact_obs[cid] = obs
    a.publish(Rec(cid, 1, RELEASED, 0, 0, 0), t)
    a.send("CONTACT", {"cid": cid, "obs": obs, "dwell_s": a.dwell_ms // 1000}, t)
    a.log("contact_open", {"cid": cid, "x": obs["x"], "y": obs["y"], "dwell_s": a.dwell_ms // 1000}, t)
    a.dwell.pop(o.vid, None)
    if a.mode == PATROL:
        a.mode = HOLDING
        a.hold_cid = cid
        a.log("hold_start", {"cid": cid}, t)


def close_contact(a, cid: str, reason: str, t: int) -> None:
    a.publish(Rec(cid, T.max_ver(a, cid) + 1, CLOSED, 0, a.me, 0), t)
    queued = relay_mod.shore_age(a, t) > SHORE_SILENCE
    a.reports.append({"cid": cid, "reason": reason, "t": t, "queued": queued,
                      "last": dict(a.contact_obs.get(cid, {}))})
    a.log("contact_close", {"cid": cid, "reason": reason, "queued": queued}, t)


def holder_tick(a, t: int):
    """Scout keeps the contact in view until another boat reports it in view, then releases."""
    cid = a.hold_cid
    rec = a.table.get(cid)
    obs = a.contact_obs.get(cid)
    if rec is None or rec.state == CLOSED or obs is None:
        a.mode, a.hold_cid = PATROL, None
        a.log("hold_end", {"cid": cid, "why": "closed"}, t)
        return None
    if rec.state == CLAIMED and rec.owner == a.me:
        a.mode, a.hold_cid = SHADOWING, None
        a.shadow_cid, a.shadow_t0 = cid, t
        a.shadow_in_view_sent = False
        a.log("shadow_start", {"cid": cid, "from": "holder"}, t)
        return shadow_tick(a, t)
    owner_view = a.contact_views.get(cid, {}).get(rec.owner) if rec.state == CLAIMED else None
    if owner_view is not None and owner_view["in_view"] and t - owner_view["t"] <= 20_000:
        a.mode, a.hold_cid = PATROL, None
        a.log("hold_end", {"cid": cid, "why": "relieved_by_%d" % rec.owner}, t)
        a.follower.resync(a, a.xy)
        return None
    if t - obs["t"] > CONTACT_STALE:
        close_contact(a, cid, "stale", t)
        a.mode, a.hold_cid = PATROL, None
        return None
    return keep_in_view_target(a, (obs["x"], obs["y"]))


def keep_in_view_target(a, cxy):
    d = _d(a.xy, cxy)
    want = min(a.standoff_m, a.keep_in_view_m - 200)
    if d > a.keep_in_view_m - 100 or d < a.standoff_floor_m:
        return approach_point(a, cxy, want)
    return None


def approach_point(a, cxy, standoff: float):
    d = _d(a.xy, cxy)
    if d < 1e-6:
        return (cxy[0] + standoff, cxy[1])
    f = standoff / d
    return (cxy[0] + (a.xy[0] - cxy[0]) * f, cxy[1] + (a.xy[1] - cxy[1]) * f)


def shadow_tick(a, t: int):
    cid = a.shadow_cid
    rec = a.table.get(cid)
    obs = a.contact_obs.get(cid)
    if rec is None or rec.state != CLAIMED or rec.owner != a.me:
        why = "vetoed" if rec is not None and rec.state == CLOSED else "lost_ownership"
        a.log("shadow_end", {"cid": cid, "why": why}, t)
        end_shadow(a)
        return None
    if obs is None or t - obs["t"] > CONTACT_STALE:
        close_contact(a, cid, "stale", t)
        end_shadow(a)
        return None
    if obs["by"] == a.me and obs["sog"] > a.V and t - obs["t"] <= 2000:
        close_contact(a, cid, "cannot_hold", t)
        end_shadow(a)
        return None
    if t - a.shadow_t0 >= a.shadow_cap_ms:
        close_contact(a, cid, "cap_reached", t)
        end_shadow(a)
        return None
    standoff = a.standoff_floor_m if a.close_approved.get(cid) else a.standoff_m
    return approach_point(a, (obs["x"], obs["y"]), standoff)


def end_shadow(a) -> None:
    a.mode = PATROL
    a.shadow_cid = None
    a.shadow_in_view_sent = False
    a.follower.resync(a, a.xy)
