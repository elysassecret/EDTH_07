"""Task records and the merge rule. Owner: A. Frozen Fri 21:00."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Rec:
    task: str
    ver: int
    state: int
    bid: int
    owner: int
    deputy: int = 0  # 0 = none


def key(r: Rec):
    return (r.ver, r.state, -r.bid, r.owner)


def merge(a: Rec, b: Rec) -> Rec:
    return a if key(a) >= key(b) else b
