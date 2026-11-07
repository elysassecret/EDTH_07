"""Message envelope and codec. Owner: A. Frozen Fri 21:00.

Every message: id, src, tc (t_created), te (t_expire), kind, hops, p (payload).
Expiry per kind in constants.EXPIRY. VETO and CMD are retried every 5 s until ACK. Max 4 hops.
Forwarding never refreshes tc or an observation time. Positions in int metres, times in sim ms.

Payloads:
  HB       boat: x, y, mode, batt (permille), cyc (cycle ms, 0 if none), tour [task ids],
           roles [task ids held], optional head [seq, hash, sig hex] of the boat's own
           evidence chain (evidence/chain.py)
           shore: {} (its arrival is the shore-age signal)
  BID      task, e (slot number), cost (ms), boat
  REC      recs: list of wire records (tasks.to_wire), optional why {task: the owner's
           plain-words reason for claiming it, under 120 chars} (#86)
  OBS      track, x, y, sog (mm/s), cog (deg), ais, to (t observed), by, dist (m)
  CONTACT  id (contact task), first (t first seen), flags {dwell, name, anchor, cannot_hold,
           capped}, course (deg or null)
  VETO     rec: wire record with state VETOED
  CMD      task, dec ("close"), ans ("approve" | "decline")
  ACK      of (msg id acknowledged)
"""
import json
from dataclasses import dataclass

from contract.constants import EXPIRY

KINDS = ("HB", "BID", "REC", "OBS", "CONTACT", "VETO", "CMD", "ACK")


@dataclass(frozen=True, slots=True)
class Msg:
    id: str  # f"{src}:{seq}", seq counts up per node from 1
    src: int  # 0 = shore
    tc: int
    te: int
    kind: str
    hops: int
    p: dict


def new(src: int, seq: int, t: int, kind: str, p: dict) -> Msg:
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind}")
    return Msg(f"{src}:{seq}", src, t, t + EXPIRY[kind], kind, 0, p)


def encode(m: Msg) -> bytes:
    d = {"id": m.id, "src": m.src, "tc": m.tc, "te": m.te, "kind": m.kind, "hops": m.hops,
         "p": m.p}
    return json.dumps(d, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def decode(b: bytes) -> Msg:
    d = json.loads(b)
    if d["kind"] not in KINDS:
        raise ValueError(f"unknown kind {d['kind']}")
    return Msg(d["id"], d["src"], d["tc"], d["te"], d["kind"], d["hops"], d["p"])
