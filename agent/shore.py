"""ShoreNode: the shore station's side of the protocol. Owner: A; wrapped by server/ (C).

It is one more radio node (ID 0): it forwards like a boat, sends a heartbeat every 5 s
(boats measure shore age from it), and keeps only what it has received.
"""
from agent.net import Every, Net
from agent.table import Table
from contract.constants import HEARTBEAT, SHORE
from contract.messages import Msg
from contract.mission import Mission, Params
from contract.tasks import from_wire


class ShoreNode:
    def __init__(self, mission: Mission, params: Params):
        self.net = Net(SHORE)
        self.table = Table(SHORE, params.seg_lease_ms, mission)
        self.boats: dict[int, tuple[int, int, dict]] = {}  # boat -> (tc, hops, payload) newest HB
        self.hb_due = Every(HEARTBEAT)

    def step(self, t: int, inbox: list[bytes]) -> list[bytes]:
        for raw in inbox:
            m = self.net.receive(t, raw)
            if m is not None:
                self.on_msg(m)
        self.net.tick(t)
        if self.hb_due(t):
            self.net.send(t, "HB", {})
        return self.net.flush()

    def on_msg(self, m: Msg) -> None:
        if m.kind == "HB" and m.src != SHORE:
            self.table.heard(m.src, m.tc)
            if m.tc > self.boats.get(m.src, (-1, 0, {}))[0]:
                self.boats[m.src] = (m.tc, m.hops, m.p)
        elif m.kind == "REC":
            for w in m.p["recs"]:
                self.table.apply(from_wire(w))
        elif m.kind == "ACK":
            self.net.ack(m.p["of"])
