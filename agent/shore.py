"""ShoreNode: the shore station's side of the protocol. Owner: A; wrapped by server/ (C).

It is one more radio node (ID 0): it forwards like a boat, sends a heartbeat every 5 s
(boats measure shore age from it), and knows only what it has received. `picture()` builds
the /shore snapshot from that alone: a boat whose link is down keeps its old data and age.
`command()` turns the watch officer's answers into VETO and CMD messages, retried until the
boat that owns the task acknowledges, or the message expires.
"""
from math import atan2, degrees

from agent.net import Every, Net
from agent.table import Table
from agent.tour import dist_to_line
from contract.constants import HEARTBEAT, PEER_STALE, SHORE, VETOED
from contract.geo import dist, to_lonlat
from contract.messages import Msg
from contract.mission import Mission, Params
from contract.tasks import Rec, from_wire, kind, to_wire
from contract.views import Boat, Decision, Event, Link, Snapshot, TaskView

ANSWERS = {"approve": "approved", "decline": "declined", "stop": "stopped",
           "confirm": "confirmed"}


class ShoreNode:
    def __init__(self, mission: Mission, params: Params):
        self.mission, self.params = mission, params
        self.net = Net(SHORE)
        self.table = Table(SHORE, params.seg_lease_ms, mission)
        self.segs = {s.id: s.pts for s in mission.tasks if kind(s.id) == "seg"}
        self.boats: dict[int, tuple[int, int, dict]] = {}  # boat -> (tc, hops, payload) newest HB
        self.direct: dict[int, int] = {}  # boat -> tc of newest HB heard with 0 hops
        self.visited: dict[str, int] = {}  # seg -> tc of newest report of a boat on it
        self.decisions: dict[str, dict] = {}  # decision id -> Decision fields + msg id
        self.events: list[dict] = []
        self.hb_due = Every(HEARTBEAT)
        self.t = 0

    def step(self, t: int, inbox: list[bytes]) -> list[bytes]:
        self.t = t
        for raw in inbox:
            m = self.net.receive(t, raw)
            if m is not None:
                self.on_msg(m)
        self.net.tick(t)
        for d in self.decisions.values():
            if d["state"] in ("approved", "declined", "stopped") and t > d["te"]:
                d["state"] = "expired"
                self.log(t, "decision_expired", f"Decision expired, not delivered: {d['text']}")
        if self.hb_due(t):
            self.net.send(t, "HB", {})
        return self.net.flush()

    def on_msg(self, m: Msg) -> None:
        if m.kind == "HB" and m.src != SHORE:
            self.table.heard(m.src, m.tc)
            if m.hops == 0:
                self.direct[m.src] = max(self.direct.get(m.src, 0), m.tc)
            if m.tc > self.boats.get(m.src, (-1, 0, {}))[0]:
                self.boats[m.src] = (m.tc, m.hops, m.p)
                pos = (m.p["x"], m.p["y"])
                for seg, pts in self.segs.items():
                    if dist_to_line(pos, pts) <= self.params.r_verify_m:
                        self.visited[seg] = max(self.visited.get(seg, 0), m.tc)
        elif m.kind in ("REC", "VETO"):
            for w in m.p["recs"] if m.kind == "REC" else [m.p["rec"]]:
                self.table.apply(from_wire(w))
        elif m.kind == "ACK":
            self.on_ack(m.src, m.p["of"], m.tc)

    # watch officer ----------------------------------------------------------------------------
    def command(self, t: int, cmd: dict) -> bool:
        """confirm/stop/approve/decline. `id` is the task for stop/confirm (e.g. 'contact:C-07')
        and '<dec>:<task>' for approve/decline (e.g. 'close:contact:C-07'). Returns False for
        commands that are not the shore protocol's (inject goes to the world)."""
        c = cmd.get("cmd")
        if c not in ANSWERS:
            return False
        did = cmd["id"]
        if c in ("stop", "confirm"):
            task, dec = did, "watch"
        else:
            dec, task = did.split(":", 1)
        owner = self.table.recs[task].owner if task in self.table.recs else 0
        text = {"watch": f"Keep {task} in view", "close": f"Close to 500 m: {task}"}.get(dec, did)
        d = {"id": did, "task": task, "dec": dec, "text": text, "state": ANSWERS[c], "t": t // 1000,
             "tier": "delegated" if dec == "watch" else "held", "boat": owner, "msg": "", "te": t}
        if c == "stop":
            rec = Rec(task, self.table.max_ver(task) + 1, VETOED, 0, 0, 0)
            self.table.apply(rec)
            m = self.net.send(t, "VETO", {"rec": to_wire(rec)}, retry=True)
            d.update(msg=m.id, te=m.te)
        elif c in ("approve", "decline"):
            m = self.net.send(t, "CMD", {"task": task, "dec": dec, "ans": c}, retry=True)
            d.update(msg=m.id, te=m.te)
        self.decisions[did] = d
        self.log(t, f"decision_{ANSWERS[c]}", f"{ANSWERS[c].capitalize()} by watch officer: {text}")
        return True

    def on_ack(self, boat: int, msg_id: str, tc: int) -> None:
        for d in self.decisions.values():
            if d["msg"] != msg_id or d["state"] == "delivered":
                continue
            if boat == d["boat"] or not d["boat"]:  # delivered to the boat that acts
                d["state"] = "delivered"
                self.net.ack(msg_id)
                self.log(tc, "decision_delivered", f"Delivered to USV {boat:02d}: {d['text']}")

    def log(self, t: int, kind_: str, text: str) -> None:
        self.events.append({"t": t // 1000, "kind": kind_, "text": text})

    # picture ----------------------------------------------------------------------------------
    def via(self, t: int) -> dict[int, int]:
        """Next hop toward shore per boat, by breadth-first search over reported links.
        Links are directed: a boat that hears the shore may not be heard by it (#21), so the
        shore edge comes only from heartbeats the shore itself heard with 0 hops."""
        adj: dict[int, list[int]] = {SHORE: []}
        for b, (tc, _, p) in sorted(self.boats.items()):
            if t - tc > PEER_STALE:
                continue
            for n in p.get("nbr", []):
                if n == SHORE:
                    continue
                adj.setdefault(b, []).append(n)
                adj.setdefault(n, []).append(b)
        for b, tc in sorted(self.direct.items()):
            if t - tc <= PEER_STALE:
                adj[SHORE].append(b)
                adj.setdefault(b, []).append(SHORE)
        parent, queue = {SHORE: SHORE}, [SHORE]
        for node in queue:
            for n in sorted(set(adj.get(node, []))):
                if n not in parent:
                    parent[n] = node
                    queue.append(n)
        return {b: p for b, p in parent.items() if b != SHORE}

    def picture(self, t: int, speed: int = 1) -> Snapshot:
        p = self.params
        via = self.via(t)
        boats, links = [], []
        for b, (tc, _, hb) in sorted(self.boats.items()):
            pos = (hb["x"], hb["y"])
            lon, lat = to_lonlat(*pos)
            remaining = hb["batt"] * p.endurance_ms // 1000
            need = p.return_safety_permille * (
                dist(pos, self.mission.shore) * 1_000_000 // p.speed_mm_s + p.reserve_ms) // 1000
            to = hb.get("to")  # heading for display only: trig never touches agent state
            hdg = round(degrees(atan2(to[0] - pos[0], to[1] - pos[1]))) % 360 if to else 0
            fresh = t - tc <= PEER_STALE
            direct = t - self.direct.get(b, -PEER_STALE - 1) <= PEER_STALE
            boats.append(Boat(
                id=b, x=pos[0], y=pos[1], lon=lon, lat=lat, mode=hb["mode"], batt=hb["batt"],
                endurance_s=remaining // 1000, must_return_by=(tc + max(remaining - need, 0)) // 1000,
                link="direct" if direct else "peer" if fresh else "none", tour=hb["tour"],
                roles=hb["roles"], last_heard=tc // 1000, hdg=hdg, sog=hb.get("spd", 0),
                via=via.get(b)))
            links.append(Link(a=SHORE, b=b, state="up" if direct else "down"))
            for n in hb.get("nbr", []):
                if n != SHORE and b < n and fresh:
                    links.append(Link(a=b, b=n, state="up"))
        tasks = {k: TaskView(v=r.ver, owner=r.owner, deputy=r.deputy, state=r.state)
                 for k, r in sorted(self.table.recs.items())}
        ages = {k: (t - self.visited.get(k, 0)) // 1000 for k in sorted(self.segs)}
        decisions = [Decision(**{k: v for k, v in d.items() if k not in ("msg", "te")})
                     for d in self.decisions.values()]
        return Snapshot(view="shore", t=t // 1000, speed=speed, boats=boats, tasks=tasks,
                        seg_age=ages, links=links, contacts=[], decisions=decisions, alerts=[],
                        events=[Event(**e) for e in self.events])
