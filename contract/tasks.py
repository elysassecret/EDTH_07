"""Task records and the merge rule. Owner: A. Frozen Fri 21:00.

Each task is a last-writer-wins register. `key` orders every field of a record, so `merge`
is the max under a total order: commutative, associative and idempotent. VETOED comes
first in the key, so once a contact is stopped no later claim can undo it.
"""
from dataclasses import dataclass

from contract.constants import VETOED

BID_ORDER = {"relay": 1, "contact": 2, "cue": 3, "seg": 4, "pick": 5}


@dataclass(frozen=True, slots=True)
class Rec:
    task: str
    ver: int
    state: int
    bid: int
    owner: int
    deputy: int = 0  # 0 = none


def kind(task: str) -> str:
    """'seg:G:0' -> 'seg', 'relay' -> 'relay'."""
    return task.split(":", 1)[0]


def key(r: Rec):
    return (r.state == VETOED, r.ver, r.state, -r.bid, r.owner, r.deputy)


def merge(a: Rec, b: Rec) -> Rec:
    if a.task != b.task:
        raise ValueError(f"merge across tasks: {a.task} vs {b.task}")
    return a if key(a) >= key(b) else b


def to_wire(r: Rec) -> list:
    return [r.task, r.ver, r.state, r.bid, r.owner, r.deputy]


def from_wire(x: list) -> Rec:
    task, ver, state, bid, owner, deputy = x
    return Rec(str(task), int(ver), int(state), int(bid), int(owner), int(deputy))
