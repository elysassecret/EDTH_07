"""Agent: the swarm brain on one boat. Owner: A. See agent/PLAN.md section 6.

Sees only its own sensors and its radio inbox; returns an action and bytes to broadcast.
No clock, no files, no randomness: time is the argument t (sim ms).
"""
from agent.net import Every, Net
from agent.table import Table
from contract.constants import HEARTBEAT, PATROL, REBROADCAST, SHORE
from contract.messages import Msg
from contract.mission import Action, Detection, Mission, Own, Params
from contract.tasks import Rec, from_wire, to_wire


class Agent:
    def __init__(self, me: int, mission: Mission, params: Params):
        self.me = me
        self.mission = mission
        self.params = params
        self.net = Net(me)
        self.table = Table(me, params.seg_lease_ms, mission)
        self.peers: dict[int, tuple[int, dict]] = {}  # boat -> (tc, payload) of newest HB
        self.shore_t = -1  # tc of the newest shore heartbeat; -1 = never heard
        self.mode = PATROL
        self.pos = (0, 0)
        self.batt = 1000
        self.t = 0
        stagger = me * 1_000  # five heartbeats should not land in the same tick
        self.hb_due = Every(HEARTBEAT, stagger)
        self.rec_due = Every(REBROADCAST, stagger)

    def step(self, t: int, own: Own, seen: tuple[Detection, ...],
             inbox: list[bytes]) -> tuple[Action, list[bytes]]:
        self.t = t
        self.pos, self.batt = (own.x, own.y), own.batt
        for raw in inbox:
            m = self.net.receive(t, raw)
            if m is not None:
                self.on_msg(m)
        self.net.tick(t)
        if self.hb_due(t):
            self.net.send(t, "HB", self.heartbeat())
        if self.rec_due(t):
            self.net.send(t, "REC", {"recs": [to_wire(r) for r in self.table.recs.values()]})
        return Action(self.mode, None, 0), self.net.flush()

    def on_msg(self, m: Msg) -> None:
        if m.kind == "HB":
            if m.src == SHORE:
                self.shore_t = max(self.shore_t, m.tc)
            else:
                self.table.heard(m.src, m.tc)
                if m.tc > self.peers.get(m.src, (-1, {}))[0]:
                    self.peers[m.src] = (m.tc, m.p)
        elif m.kind == "REC":
            for w in m.p["recs"]:
                self.apply(from_wire(w))
        elif m.kind == "VETO":
            self.apply(from_wire(m.p["rec"]))
        elif m.kind == "ACK":
            self.net.ack(m.p["of"])

    def apply(self, r: Rec) -> None:
        self.table.apply(r)

    def publish(self, r: Rec) -> None:
        """Adopt a record locally and broadcast it."""
        self.table.apply(r)
        self.net.send(self.t, "REC", {"recs": [to_wire(r)]})

    def heartbeat(self) -> dict:
        return {"x": self.pos[0], "y": self.pos[1], "mode": self.mode, "batt": self.batt,
                "cyc": 0, "tour": [], "roles": self.table.held_by(self.me)}

    def view(self) -> dict:
        """JSON-safe state for /truth, state hashes and tests."""
        return {
            "me": self.me, "t": self.t, "mode": self.mode, "pos": list(self.pos),
            "batt": self.batt, "shore_t": self.shore_t,
            "last_hb": {str(b): tc for b, tc in sorted(self.table.last_hb.items())},
            "tasks": {k: to_wire(r) for k, r in sorted(self.table.recs.items())},
        }
