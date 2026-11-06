"""Fixed-order sequential single-item auction in 12 s slots on shared time. No coordinator.

Every boat bids once per slot on the first open task it is eligible for, in
bid order (relay, contact, cue, seg, pick). At the next slot each boat closes
the previous round with the bids it heard; the cheapest bid wins, ties to the
higher boat ID. A winner publishes a claim at version+1. A lost bid resolves
at merge, because the bid sits in the merge key. Claims carry a deputy for
relay and contact only.
"""
from __future__ import annotations

import math

from contract.constants import (CLAIMED, CUE, HOLDING, PATROL, RELAY, RELEASED, RETURNING, SHADOWING, SHORE_ID,
                                SHORE_SILENCE, SLOT, UNAVAILABLE, ACTIVE_SILENCE, PEER_STALE)
from contract.tasks import Rec, bid_order, kind

from . import relay as relay_mod
from . import table as T
from . import tour as TR


def _d(p, q) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


def live_peers(a, t: int) -> list[int]:
    return [b for b in a.mission.boats if b != a.me and a.last_hb.get(b) is not None and t - a.last_hb[b] <= PEER_STALE]


def n_active(a, t: int) -> int:
    n = 0
    for b in a.mission.boats:
        if b == a.me:
            n += 1
            continue
        hb = a.last_hb.get(b)
        if hb is None or t - hb > ACTIVE_SILENCE:
            continue
        if a.peers.get(b, {}).get("mode") in (RETURNING, UNAVAILABLE):
            continue
        n += 1
    return n


def dist_home(a) -> float:
    return _d(a.xy, a.mission.shore_xy)


def spare_s(a) -> float:
    """Seconds of endurance beyond reserve and the trip home."""
    return a.batt_s - a.reserve_s - dist_home(a) / a.V


def energy_ok(a, cycle_s: float) -> bool:
    return spare_s(a) >= cycle_s / 2.0


def cycle_after(a, task: str) -> tuple[float, float]:
    """(cycle seconds after cheapest insertion, one-time transit seconds to the segment)."""
    c_m, new_tour = TR.cheapest_insertion(a, a.tour, task)
    pts = a.mission.tasks[task].points
    transit = min(_d(a.xy, pts[0]), _d(a.xy, pts[-1])) / a.V
    return c_m / a.V, transit


def my_cycle_s(a) -> float:
    return TR.cycle_length_m(a, a.tour) / a.V


def bid_cost(a, task: str, t: int) -> int:
    k = kind(task)
    batt_term = 1_800_000 * (1000 - a.batt_permille) // 1000
    if k == "seg":
        cyc, transit = cycle_after(a, task)
        return int(cyc * 1000 + transit * 1000) + batt_term
    if k == "pick":
        pt = a.mission.tasks[task].points[0]
        return int(_d(a.xy, pt) / a.V * 1000) + batt_term
    if k == "relay":
        return int(_d(a.xy, a.mission.relay_xy) / a.V * 1000) + batt_term
    if k == "contact":
        g = a.contact_obs.get(task)
        pos = (g["x"], g["y"]) if g else a.xy
        travel = max(0.0, _d(a.xy, pos) - a.standoff_m) / a.V
        return int((travel + my_cycle_s(a)) * 1000) + batt_term
    if k == "cue":
        g = a.cue_geoms.get(task)
        pos = (g["x"], g["y"]) if g else a.xy
        return int((_d(a.xy, pos) / a.V + my_cycle_s(a)) * 1000) + batt_term
    return 10**9


def i_am_relay(a) -> bool:
    r = a.table.get("relay")
    return r is not None and r.state == CLAIMED and r.owner == a.me


def seg_owners(a, t: int) -> set[int]:
    out = set()
    for task in sorted(a.table):
        r = a.table[task]
        if kind(task) == "seg" and r.state == CLAIMED and T.lease_ok(a, r.owner, t):
            out.add(r.owner)
    return out


def i_am_last_cable_owner(a, t: int) -> bool:
    return seg_owners(a, t) == {a.me}


def owns(a, k: str) -> bool:
    return bool(T.owned(a, k))


def contact_speed(a, task: str) -> float:
    g = a.contact_obs.get(task)
    return g["sog"] if g else 0.0


def eta_ok(a, task: str, t: int) -> bool:
    g = a.cue_geoms.get(task)
    if not g:
        return False
    d = _d(a.xy, (g["x"], g["y"]))
    return (max(0.0, d - a.r_verify_m) / a.V) * 1000 <= g["t_cross"] - t - 60_000 and t < g["expires"]


def can_bid(a, task: str, t: int) -> bool:
    if a.mode in (RETURNING, UNAVAILABLE):
        return False
    k = kind(task)
    r = a.table[task]
    if k == "seg":
        if not a.repair:
            return False
        if a.mode in (SHADOWING, HOLDING, CUE) or i_am_relay(a):
            return False
        if r.state == CLAIMED and 1 + len(live_peers(a, t)) < n_active(a, t) // 2 + 1:
            return False                       # expiry takeover needs a live majority
        cyc, _ = cycle_after(a, task)
        return cyc * 1000 <= a.cycle_max_ms and energy_ok(a, cyc)
    if k == "pick":
        if not a.repair:
            return False
        return a.mode == PATROL and not i_am_relay(a) and not owns(a, "seg") and not a.pick
    if k == "relay":
        # no quorum here on purpose: the side that lost its shore path is the side that needs a relay.
        # But a relay with nobody to relay for is pointless, and a cable scout leaves relay duty to an
        # idle or picket boat when one is alive in its group.
        peers = live_peers(a, t)
        if not peers or a.mode in (SHADOWING,):
            return False
        if owns(a, "seg") and any(not a.peers.get(b, {}).get("tour") and a.peers.get(b, {}).get("mode") == PATROL
                                  and not a.peers.get(b, {}).get("relay") for b in peers):
            return False
        return relay_mod.shore_age(a, t) > SHORE_SILENCE and spare_s(a) >= 3600
    if k == "contact":
        return (a.mode in (PATROL, HOLDING) and not i_am_relay(a) and not i_am_last_cable_owner(a, t)
                and spare_s(a) >= a.shadow_cap_ms / 1000 and contact_speed(a, task) <= a.V)
    if k == "cue":
        return (a.mode == PATROL and not i_am_relay(a) and not i_am_last_cable_owner(a, t)
                and eta_ok(a, task, t))
    return False


KNOWN_OPEN_MS = 6_000   # a task must have been open, as seen locally, for half a slot before a bid


def known_open(a, task: str, t: int) -> bool:
    """True if this boat has seen the task open long enough that peers can have heard too."""
    if not T.is_open(a, task, t):
        a.open_since.pop(task, None)
        return False
    since = a.open_since.get(task)
    if since is None:
        a.open_since[task] = t
        return False
    return t - since >= KNOWN_OPEN_MS


def on_slot(a, t: int) -> None:
    e = t // SLOT
    close_round(a, e - 1, t)
    for task in sorted(a.table, key=bid_order):
        if known_open(a, task, t) and can_bid(a, task, t):
            cost = bid_cost(a, task, t)
            a.bids.setdefault(e, {}).setdefault(task, []).append((cost, a.me))
            a.send("BID", {"task": task, "e": e, "cost": cost, "boat": a.me}, t)
            a.log("bid", {"task": task, "e": e, "cost": cost}, t)
            break                                   # one bid per slot


def close_round(a, e: int, t: int) -> None:
    rounds = a.bids.pop(e, {})
    for task in sorted(rounds):
        if task not in a.table or not T.is_open(a, task, t):
            continue                                # live claim arrived: cancel
        bs = sorted(set(rounds[task]), key=lambda b: (b[0], -b[1]))
        if bs[0][1] != a.me:
            continue
        dep = bs[1][1] if len(bs) > 1 and kind(task) in ("relay", "contact") else 0
        rec = Rec(task, T.max_ver(a, task) + 1, CLAIMED, bs[0][0], a.me, dep)
        a.publish(rec, t)
        a.on_won(task, t)
    # drop stale rounds
    for old in [k for k in a.bids if k < e]:
        a.bids.pop(old, None)


def on_rebalance(a, t: int) -> None:
    if not a.repair or a.mode != PATROL or i_am_relay(a) or len(a.tour) < 2:
        return
    if any(T.is_open(a, task, t) for task in a.table if kind(task) == "seg"):
        return
    cands = []
    for b in live_peers(a, t):
        p = a.peers.get(b, {})
        if p.get("mode") != PATROL or p.get("relay") or p.get("pick"):
            continue
        cands.append((p.get("cycle", 0), b))
    if not cands:
        return
    lo_cycle, lo = min(cands)
    if my_cycle_s(a) * 1000 <= a.rebalance_ratio * lo_cycle:
        return
    lo_tour = [(x, False) for x in a.peers[lo].get("tour", [])]
    hit = TR.removal_that_lowers_max(a, a.tour, lo_tour)
    if hit is None:
        return
    _, task, theirs_m = hit
    if theirs_m / a.V * 1000 < my_cycle_s(a) * 1000:
        a.publish(Rec(task, T.max_ver(a, task) + 1, RELEASED, 0, a.me, 0), t)
        a.log("rebalance_release", {"task": task, "to_hint": lo}, t)
