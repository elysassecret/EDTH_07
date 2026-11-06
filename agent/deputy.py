"""Named deputy (P1): relay and contact only.

The second-lowest bidder is named at claim time. On lease expiry it takes
over without a bid round, or declines and the task reopens after DEPUTY_GRACE.
Never say "no radio traffic": heartbeats renew the lease and the takeover is published.
"""
from __future__ import annotations

from contract.constants import CLAIMED, RELEASED
from contract.tasks import Rec

from . import auction as A
from . import table as T


def on_tick(a, t: int) -> None:
    for task in sorted(a.table):
        r = a.table[task]
        if r.deputy != a.me or r.state != CLAIMED or T.lease_ok(a, r.owner, t):
            continue
        if A.can_bid(a, task, t):
            a.publish(Rec(task, r.ver + 1, CLAIMED, A.bid_cost(a, task, t), a.me, 0), t)
            a.log("deputy_takeover", {"task": task, "from": r.owner}, t)
            a.on_won(task, t)
        else:
            a.publish(Rec(task, r.ver + 1, RELEASED, 0, a.me, 0), t)
            a.log("deputy_decline", {"task": task, "from": r.owner}, t)
