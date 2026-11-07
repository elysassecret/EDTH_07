"""ShoreNode: the shore station's side of the protocol. Owner: A; wrapped by server/ (C).

It is one more radio node (ID 0): it forwards like a boat, sends a heartbeat every 5 s
(boats measure shore age from it), and knows only what it has received. `picture()` builds
the /shore snapshot from that alone: a boat whose link is down keeps its old data and age.
`command()` turns the watch officer's answers into VETO and CMD messages, retried until the
boat that owns the task acknowledges, or the message expires.

Contacts come only from delivered OBS and CONTACT messages (#17). When a boat claims a contact,
the shore opens two cards with stable ids: `contact:<track>` (keep in view, delegated: already
running, Confirm/Stop) and `close:contact:<track>` (close to 500 m, held: Approve/Decline).
"""
from itertools import pairwise
from math import atan2, degrees, hypot

from agent.contact import FLAGS, Contacts
from agent.net import Every, Net
from agent.table import Table
from agent.tour import dist_to_line
from contract.constants import CLAIMED, CONTACT_STALE, HEARTBEAT, PEER_STALE, SHORE, VETOED
from contract.geo import dist, to_lonlat
from contract.messages import Msg
from contract.mission import Mission, Params
from contract.tasks import Rec, from_wire, kind, to_wire
from contract.views import Boat, Contact, ContactFlags, Decision, Event, Link, Snapshot, TaskView

SAMPLE_M = 100  # the evaluator's sample step (config/scene.toml sample_step_m)
TRAIL = 60  # recent positions kept per track for the chart
ANSWERS = {"approve": "approved", "decline": "declined", "stop": "stopped",
           "confirm": "confirmed"}
FLAG_TEXT = {"dwell": "{t} has stayed slow near a cable with no AIS: cue for a look",
             "name": "Look within 500 m done: {t}", "anchor": None,
             "cannot_hold": "Cannot hold {t}; report queued; last course {c}",
             "capped": "Watch time cap reached for {t}; released"}


class ShoreNode:
    def __init__(self, mission: Mission, params: Params):
        self.mission, self.params = mission, params
        self.net = Net(SHORE)
        self.table = Table(SHORE, params.seg_lease_ms, mission)
        self.segs = {s.id: s.pts for s in mission.tasks if kind(s.id) == "seg"}
        self.boats: dict[int, tuple[int, int, dict]] = {}  # boat -> (tc, hops, payload) newest HB
        self.direct: dict[int, int] = {}  # boat -> tc of newest HB heard with 0 hops
        self.samples = {k: samples(pts) for k, pts in self.segs.items()}
        self.seen: dict[str, list[int | None]] = {k: [None] * len(v) for k, v in self.samples.items()}
        self.decisions: dict[str, dict] = {}  # decision id -> Decision fields + msg id
        self.contacts = Contacts(self)  # the boats' merge rules, fed only by delivered messages
        self.trail: dict[str, list[tuple[float, float]]] = {}
        self.bids: dict[str, dict[int, tuple[int, int]]] = {}  # task -> boat -> (round, cost ms)
        self.explained: set[tuple[str, int]] = set()  # (task, version) already explained
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
        self.offer(t)
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
                self.credit(pos, m.tc)
        elif m.kind in ("REC", "VETO"):
            for w in m.p["recs"] if m.kind == "REC" else [m.p["rec"]]:
                r = from_wire(w)
                if self.table.apply(r)[0] and r.state == CLAIMED and r.ver > 1:
                    self.explain(m.tc, self.table.recs[r.task])
        elif m.kind == "BID":
            self.bids.setdefault(m.p["task"], {})[m.p["boat"]] = (m.p["e"], m.p["cost"])
        elif m.kind == "OBS":
            track, old = m.p["track"], self.contacts.tracks.get(m.p["track"])
            self.contacts.on_obs(m.p)
            if old is None:
                self.log(m.tc, "contact_reported", f"USV {m.p['by']:02d} reports {track}"
                         + ("" if m.p["ais"] else " (camera, no AIS)"))
            if self.contacts.tracks[track] is not old:
                o = self.contacts.tracks[track]
                self.trail.setdefault(track, []).append(to_lonlat(o["x"], o["y"]))
                del self.trail[track][:-TRAIL]
        elif m.kind == "CONTACT":
            before = dict(self.contacts.flags.get(m.p["id"], {}))
            self.contacts.on_contact(m.p)
            f, track = self.contacts.flags[m.p["id"]], m.p["id"].split(":", 1)[1]
            for k in FLAGS:
                if f[k] and not before.get(k) and FLAG_TEXT[k]:
                    self.log(m.tc, f"contact_{k}", FLAG_TEXT[k].format(t=track, c=f["course"]))
        elif m.kind == "ACK":
            self.on_ack(m.src, m.p["of"], m.tc)

    def explain(self, t: int, r: Rec) -> None:
        """Why a boat got a task (roadmap: explain every assignment): its bid, and the bids the
        shore heard from others in the same round. Only what reached the shore; bids that did
        not arrive are not guessed."""
        if r.state != CLAIMED or (r.task, r.ver) in self.explained or not r.owner:
            return
        self.explained.add((r.task, r.ver))
        heard = self.bids.get(r.task, {})
        e = heard.get(r.owner, (None, 0))[0]
        others = sorted((c, b) for b, (eb, c) in heard.items() if b != r.owner and eb == e)
        if others:
            text = (f"USV {r.owner:02d} took {r.task}: lowest bid {hm(r.bid)}, ahead of "
                    + ", ".join(f"USV {b:02d} {hm(c)}" for c, b in others))
        else:
            text = f"USV {r.owner:02d} took {r.task}: bid {hm(r.bid)}, the only bid shore heard"
        self.log(t, "assignment", text + " (bid = travel and patrol time plus battery and role "
                 "penalties)")

    # decision cards ---------------------------------------------------------------------------
    def offer(self, t: int) -> None:
        """Open both cards when a boat claims a contact; keep the acting boat and route current
        while they are open; withdraw them once the contact is stopped, cannot be held or capped."""
        for task, r in sorted(self.table.recs.items()):
            if kind(task) != "contact":
                continue
            f = self.contacts.flags.get(task, {})
            over = r.state == VETOED or f.get("cannot_hold") or f.get("capped")
            for did, dec in ((task, "keep"), (f"close:{task}", "close")):
                d = self.decisions.get(did)
                if d is None and r.state == CLAIMED and not over:
                    d = self.decisions[did] = self.card(t, did, task, dec, r.owner)
                    d["state"] = "pending"
                    self.log(t, "decision_open", f"{'Running' if dec == 'keep' else 'Waiting'}"
                             f": {d['text']}")
                if d is None or d["state"] != "pending":
                    continue
                if over:
                    d["state"] = "expired"
                    self.log(t, "decision_withdrawn", f"No longer needed: {d['text']}")
                elif r.state == CLAIMED:
                    d["boat"], d["route"] = r.owner, self.route(r.owner, task)

    def card(self, t: int, did: str, task: str, dec: str, boat: int) -> dict:
        track = task.split(":", 1)[1]
        keep = dec == "keep"
        text = (f"USV {boat:02d} keeping {track} in view. Standing Order 2" if keep
                else f"USV {boat:02d} to close to 500 m for a look at {track}")
        return {"id": did, "task": task, "dec": dec, "text": text, "state": "pending",
                "t": t // 1000, "tier": "delegated" if keep else "held",
                "actions": ["confirm", "stop"] if keep else ["approve", "decline"], "boat": boat,
                "route": self.route(boat, task), "msg": "", "te": t}

    def route(self, boat: int, task: str) -> list[tuple[float, float]] | None:
        o = self.contacts.tracks.get(task.split(":", 1)[1])
        if boat not in self.boats or o is None:
            return None
        hb = self.boats[boat][2]
        return [to_lonlat(hb["x"], hb["y"]), to_lonlat(o["x"], o["y"])]

    def credit(self, pos: tuple[int, int], tc: int) -> None:
        """A reported position visits every sample within r_verify_m, as the evaluator counts
        visits (#22, #29): touching one end of a segment does not refresh the far end."""
        r = self.params.r_verify_m
        for seg, pts in self.segs.items():
            if dist_to_line(pos, pts) > r:
                continue
            seen = self.seen[seg]
            for i, sp in enumerate(self.samples[seg]):
                if dist(pos, sp) <= r and (seen[i] is None or seen[i] < tc):
                    seen[i] = tc

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
            task, dec = did, "keep"
        else:
            dec, task = did.split(":", 1)
        owner = self.table.recs[task].owner if task in self.table.recs else 0
        d = self.decisions.get(did) or self.card(t, did, task, dec, owner)
        d.update(state=ANSWERS[c], te=t)
        text = d["text"]
        if c == "stop":
            rec = Rec(task, self.table.max_ver(task) + 1, VETOED, 0, 0, 0)
            self.table.apply(rec)
            m = self.net.send(t, "VETO", {"rec": to_wire(rec)}, retry=True)
            d.update(msg=m.id, te=m.te)
        elif c in ("approve", "decline"):
            m = self.net.send(t, "CMD", {"task": task, "dec": dec, "ans": c}, retry=True)
            d.update(msg=m.id, te=m.te)
        self.decisions[did] = d
        if c == "stop":  # the watch is over, so is any pending close
            self.offer(t)
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
        # worst sample per segment; a never-reported sample counts from t = 0, as the evaluator
        # does, and the console shows an age equal to the run time as "no visit reported"
        ages = {k: (t - min(x or 0 for x in v)) // 1000 for k, v in sorted(self.seen.items())}
        decisions = [Decision(**{k: v for k, v in d.items() if k not in ("msg", "te")})
                     for d in self.decisions.values()]
        contacts = []
        for track, o in sorted(self.contacts.tracks.items()):
            task = f"contact:{track}"
            r, f = self.table.recs.get(task), self.contacts.flags.get(task, {})
            lon, lat = to_lonlat(o["x"], o["y"])
            contacts.append(Contact(
                id=task if not o["ais"] else f"ais:{track}", track=track, x=o["x"], y=o["y"],
                lon=lon, lat=lat, sog=o["sog"], cog=o["cog"], ais=o["ais"],
                first_seen=self.contacts.first[track] // 1000, last_seen=o["to"] // 1000,
                seen_by=sorted(b for b, ob in self.contacts.by[track].items()
                               if o["to"] - ob["to"] <= CONTACT_STALE),
                watcher=r.owner if r and r.state == CLAIMED else 0, state=r.state if r else 0,
                flags=ContactFlags(**{k: bool(f.get(k)) for k in FLAGS}), course=f.get("course"),
                source="ais" if o["ais"] else "camera", trail=self.trail.get(track, [])))
        return Snapshot(view="shore", t=t // 1000, speed=speed, boats=boats, tasks=tasks,
                        seg_age=ages, links=links, contacts=contacts, decisions=decisions, alerts=[],
                        events=[Event(**e) for e in self.events])


def samples(pts: tuple[tuple[int, int], ...]) -> list[tuple[int, int]]:
    """Points every SAMPLE_M along the polyline from its start, endpoint excluded, placed the
    way world/routes.py samples routes. Display only: floats never touch agent state."""
    out, offset, walked = [], 0, 0.0
    for a, b in pairwise(pts):
        d = hypot(b[0] - a[0], b[1] - a[1])
        while offset < walked + d:
            f = (offset - walked) / d
            out.append((round(a[0] + (b[0] - a[0]) * f), round(a[1] + (b[1] - a[1]) * f)))
            offset += SAMPLE_M
        walked += d
    return out


def hm(ms_: int) -> str:
    """Bid cost (ms) as hours and minutes."""
    m = ms_ // 60_000
    return f"{m // 60} h {m % 60:02d} m" if m >= 60 else f"{m} m"
