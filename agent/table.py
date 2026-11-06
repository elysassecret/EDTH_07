"""Task table: records, per-boat heartbeats, leases. Owner: A.

One lease per boat: a heartbeat renews all of a boat's tasks. Leases use the heartbeat's
t_created (shared sim clock), so a forwarded heartbeat counts and a late one does not extend
anything. relay and contact use LEASE (60 s); seg and pick use the long seg lease (PLAN F4).
"""
from contract.constants import CLAIMED, DEPUTY_GRACE, LEASE, RELEASED, VETOED
from contract.mission import Mission
from contract.tasks import Rec, kind, merge


class Table:
    def __init__(self, me: int, seg_lease_ms: int, mission: Mission):
        """Every node starts from the same records: initial owners at version 1, the rest
        released at version 0. No messages are needed to start."""
        self.me = me
        self.seg_lease_ms = seg_lease_ms
        self.recs: dict[str, Rec] = {}
        self.last_hb: dict[int, int] = {}  # boat -> newest heartbeat tc; never heard = 0
        owners = dict(mission.initial)
        for spec in mission.tasks:
            o = owners.get(spec.id, 0)
            self.recs[spec.id] = Rec(spec.id, 1 if o else 0, CLAIMED if o else RELEASED, 0, o)

    def heard(self, boat: int, tc: int) -> None:
        if tc > self.last_hb.get(boat, 0):
            self.last_hb[boat] = tc

    def lease_ms(self, task: str) -> int:
        return LEASE if kind(task) in ("relay", "contact") else self.seg_lease_ms

    def lease_ok(self, owner: int, task: str, t: int) -> bool:
        return owner == self.me or t <= self.last_hb.get(owner, 0) + self.lease_ms(task)

    def is_open(self, task: str, t: int) -> bool:
        r = self.recs[task]
        if r.state == RELEASED:
            return True
        if r.state == VETOED or self.lease_ok(r.owner, task, t):
            return False
        grace_end = self.last_hb.get(r.owner, 0) + self.lease_ms(task) + DEPUTY_GRACE
        return not (r.deputy and t < grace_end)

    def apply(self, r: Rec) -> tuple[bool, bool]:
        """Merge one record. Returns (changed, I lost a task I held)."""
        cur = self.recs.get(r.task)
        new = r if cur is None else merge(cur, r)
        if new == cur:
            return False, False
        self.recs[r.task] = new
        held = cur is not None and cur.owner == self.me and cur.state == CLAIMED
        return True, held and not (new.owner == self.me and new.state == CLAIMED)

    def max_ver(self, task: str) -> int:
        return self.recs[task].ver if task in self.recs else 0

    def held_by(self, boat: int) -> list[str]:
        """Tasks a boat holds as owner, in table order."""
        return [k for k, r in self.recs.items() if r.owner == boat and r.state == CLAIMED]
