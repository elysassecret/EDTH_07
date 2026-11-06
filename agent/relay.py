"""Shore-age gossip and the relay role.

shore_age = time since this boat last had a path to shore: directly (a shore
heartbeat heard) or through a peer whose heartbeat carried its own shore age.
A group that already has a shore path elects no relay (P7).
"""
from __future__ import annotations

from contract.constants import SHORE_ID

FAR = 10**12


def shore_age(a, t: int) -> int:
    best = FAR
    hb = a.last_hb.get(SHORE_ID)
    if hb is not None:
        best = t - hb
    for b, p in sorted(a.peers.items()):
        if b == SHORE_ID or "shore_age" not in p:
            continue
        age = p["shore_age"] + (t - p["t"])
        if age < best:
            best = age
    return best


def shore_path(a, t: int) -> str:
    """'direct', 'relay' or 'none' for display."""
    hb = a.last_hb.get(SHORE_ID)
    if hb is not None and t - hb <= 20_000:
        return "direct"
    return "relay" if shore_age(a, t) <= 30_000 else "none"
