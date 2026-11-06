"""Task table: one lease per boat, heartbeats renew all of a boat's tasks."""
from __future__ import annotations

from contract.constants import CLAIMED, DEPUTY_GRACE, LEASE, RELEASED, VETOED
from contract.tasks import Rec, merge


def lease_ok(a, b: int, t: int) -> bool:
    if b == a.me:
        return True
    hb = a.last_hb.get(b)
    return hb is not None and t <= hb + LEASE


def is_open(a, task: str, t: int) -> bool:
    r = a.table[task]
    if r.state == RELEASED:
        return True
    if r.state == VETOED or lease_ok(a, r.owner, t):
        return False
    if r.deputy and t < a.last_hb.get(r.owner, -10**12) + LEASE + DEPUTY_GRACE:
        return False
    return True


def on_record(a, r: Rec, t: int) -> bool:
    """Merge one record. Returns True if the table changed."""
    cur = a.table.get(r.task)
    if cur is None:
        a.table[r.task] = r
        a.on_table_change(None, r, t)
        return True
    new = merge(cur, r)
    if new is cur:
        return False
    a.table[r.task] = new
    a.on_table_change(cur, new, t)
    return True


def max_ver(a, task: str) -> int:
    r = a.table.get(task)
    return r.ver if r else 0


def owned(a, kind_name: str | None = None) -> list[str]:
    out = []
    for task in sorted(a.table):
        r = a.table[task]
        if r.state == CLAIMED and r.owner == a.me and (kind_name is None or task.split(":", 1)[0] == kind_name):
            out.append(task)
    return out
