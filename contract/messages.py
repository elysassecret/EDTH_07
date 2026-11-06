"""Envelope for every radio message. Crosses the radio as encoded bytes only.

msg_id, src, t_created, t_expire, kind, hops, payload
kind in HB, BID, REC, OBS, CONTACT, VETO, CMD, ACK.
Forwarding never refreshes t_created or an observation time.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .constants import EXPIRY_MS


@dataclass(slots=True)
class Envelope:
    msg_id: str
    src: int
    t_created: int
    t_expire: int
    kind: str
    hops: int
    payload: dict[str, Any] = field(default_factory=dict)

    def encode(self) -> bytes:
        return json.dumps(
            [self.msg_id, self.src, self.t_created, self.t_expire, self.kind, self.hops, self.payload],
            separators=(",", ":"), sort_keys=True).encode()

    @staticmethod
    def decode(b: bytes) -> "Envelope":
        m, s, tc, te, k, h, p = json.loads(b.decode())
        return Envelope(m, s, tc, te, k, h, p)

    def forwarded(self) -> "Envelope":
        return Envelope(self.msg_id, self.src, self.t_created, self.t_expire, self.kind, self.hops + 1, self.payload)


def make(src: int, seq: int, t: int, kind: str, payload: dict[str, Any]) -> Envelope:
    return Envelope(f"{src}-{seq}", src, t, t + EXPIRY_MS[kind], kind, 0, payload)
