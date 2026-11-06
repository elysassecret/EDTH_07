"""Network layer on each node: message ids, dedupe, expiry, flooding, retries. Owner: A.

The radio (world/) only delivers one broadcast to nodes in range. Multi-hop is done here:
every new, unexpired message is re-broadcast once with hops + 1, up to MAX_HOPS.
Forwarding never changes id, tc or te.
"""
from dataclasses import replace

from contract.constants import MAX_HOPS, RETRY
from contract.messages import Msg, decode, encode, new


class Every:
    """True once each time (t + offset) crosses a multiple of period; the first call is True.

    Boundary crossing, not t % period == 0, so it works whatever tick the world uses.
    """

    def __init__(self, period: int, offset: int = 0):
        self.period, self.offset, self.last = period, offset, None

    def __call__(self, t: int) -> bool:
        b = (t + self.offset) // self.period
        fire, self.last = b != self.last, b
        return fire


class Net:
    def __init__(self, me: int):
        self.me = me
        self.seq = 0
        self.seen: dict[str, int] = {}  # msg id -> te, pruned after expiry
        self.pending: dict[str, tuple[Msg, int]] = {}  # retried until ACK: id -> (msg, next send)
        self.out: list[bytes] = []
        self.fwd: list[bytes] = []
        self.pruned_at = 0
        self.acks: list[str] = []  # ids of VETO and CMD to acknowledge, duplicates included

    def send(self, t: int, kind: str, p: dict, retry: bool = False) -> Msg:
        self.seq += 1
        m = new(self.me, self.seq, t, kind, p)
        self.seen[m.id] = m.te
        self.out.append(encode(m))
        if retry:
            self.pending[m.id] = (m, t + RETRY)
        return m

    def receive(self, t: int, raw: bytes) -> Msg | None:
        """Decode one delivered message; None if garbled, already seen or expired."""
        try:
            m = decode(raw)
        except (ValueError, KeyError, TypeError):
            return None
        if t > m.te:
            return None
        if m.kind in ("VETO", "CMD") and m.src != self.me and m.id not in self.acks:
            self.acks.append(m.id)  # ack resends too, in case our first ACK was lost
        if m.id in self.seen:
            return None
        self.seen[m.id] = m.te
        if m.hops < MAX_HOPS:
            self.fwd.append(encode(replace(m, hops=m.hops + 1)))
        return m

    def take_acks(self) -> list[str]:
        out, self.acks = self.acks, []
        return out

    def ack(self, msg_id: str) -> None:
        self.pending.pop(msg_id, None)

    def tick(self, t: int) -> None:
        """Resend unacknowledged messages every RETRY; forget expired ids once a second."""
        for mid, (m, due) in list(self.pending.items()):
            if t > m.te:
                del self.pending[mid]
            elif t >= due:
                self.out.append(encode(m))
                self.pending[mid] = (m, t + RETRY)
        if t - self.pruned_at >= 1_000:
            self.pruned_at = t
            self.seen = {k: te for k, te in self.seen.items() if te >= t}

    def flush(self) -> list[bytes]:
        out, self.out, self.fwd = self.out + self.fwd, [], []
        return out
