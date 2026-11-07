"""Agent: the swarm brain on one boat. Owner: A. See agent/PLAN.md section 6.

Sees only its own sensors and its radio inbox; returns an action and bytes to broadcast.
No clock, no files, no randomness: time is the argument t (sim ms).

Each boat also keeps its own evidence chain (#37): what it claimed, released, flagged and was
told, hash-linked by evidence/chain.py. Its signed head rides in every heartbeat, so the shore
and peers hold a copy and a lost or altered boat cannot silently rewrite its record.
"""
from hashlib import sha256
from math import cos, isqrt, radians, sin

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent.auction import DROPS, Auction, ms
from agent.contact import Contacts, ring_point, task_of
from agent.net import Every, Net
from agent.table import Table
from agent.tour import KORSOR_SHORE, Follower, Leg, Tours, Visits, dist_to_line, route_water
from contract.constants import (
    CLAIMED,
    HEARTBEAT,
    PATROL,
    PEER_STALE,
    REBALANCE,
    REBROADCAST,
    RELEASED,
    RETURNING,
    SENTINEL,
    SHADOWING,
    SHORE,
    SLOT,
    UNAVAILABLE,
)
from contract.geo import dist
from contract.messages import Msg
from contract.mission import Action, Detection, Mission, Own, Params
from contract.tasks import Rec, from_wire, kind, to_wire
from evidence.chain import Chain, head_message

HOME_M = 50  # at the shore station
STANDOFF_MARGIN_M = 50  # steer round the stand-off ring this far outside it
CPA_MARGIN_M = 400  # plan round a ship this much wider than the clearance: it moves while we turn
AIM_M = 500  # while rounding a ring, aim this far ahead along the tangent
STATION_BACK_M = 100  # SENTINEL: once correcting, drive back to this close before drifting again
SIN = [round(1000 * sin(radians(d))) for d in range(360)]  # integer trig for courses (#118)
COS = [round(1000 * cos(radians(d))) for d in range(360)]
TIME_SOURCE = "sim clock (simulation; no GNSS model)"  # same words as evidence/build.py


def demo_key(me: int) -> Ed25519PrivateKey:
    """Demo key, derived from the boat id so runs repeat. Not a secret: anyone can rebuild it.
    A fielded boat would hold its own key; signing is deterministic either way (Ed25519)."""
    return Ed25519PrivateKey.from_private_bytes(sha256(f"edth07-demo-key:usv-{me:02d}".encode())
                                                .digest())


def round_ring(p: tuple[int, int], c: tuple[int, int], r: int,
               goal: tuple[int, int]) -> tuple[int, int]:
    """A point AIM_M ahead of p along the tangent to circle (c, r) on the goal's side. Recomputed
    every tick, this walks the boat round the circle until the goal is in clear view."""
    dx, dy = p[0] - c[0], p[1] - c[1]
    d2 = dx * dx + dy * dy
    s = isqrt(max(d2 - r * r, 0))
    tangents = [(c[0] + (r * r * dx + k * r * s * -dy) // d2, c[1] + (r * r * dy + k * r * s * dx) // d2)
                for k in (1, -1)]
    t = min(tangents, key=lambda q: (dist(q, goal), q))
    vx, vy = t[0] - p[0], t[1] - p[1]
    n = isqrt(vx * vx + vy * vy)
    if n < AIM_M // 10:  # on the ring itself: the tangent is the perpendicular
        vx, vy = min(((-dy, dx), (dy, -dx)),
                     key=lambda w: dist((p[0] + w[0], p[1] + w[1]), goal))
        n = isqrt(vx * vx + vy * vy) or 1
    return p[0] + vx * AIM_M // n, p[1] + vy * AIM_M // n


class Agent:
    def __init__(self, me: int, mission: Mission, params: Params):
        self.me = me
        self.mission = mission
        self.params = params
        self.net = Net(me)
        self.table = Table(me, params.seg_lease_ms, mission)
        self.tours = Tours({s.id: s.pts for s in mission.tasks if kind(s.id) == "seg"})
        self.stations = {s.id: s.pts[0] for s in mission.tasks if kind(s.id) != "seg"}
        self.follow = Follower(self.tours)
        self.visits = Visits(self.tours.pts, params.r_verify_m)
        self.auction = Auction(self)
        self.contacts = Contacts(self)
        self.chain = Chain(f"usv-{me:02d}-onboard")
        self.key = demo_key(me)
        self.signed: list = []  # [seq, hash, sig] of the newest signed head
        self.speed_permille = 1000  # share of cruise speed the boat really makes (#106)
        self.health = ""  # last health report, "" while progress is to plan
        self.fails = 0  # failed progress checks in a row
        self.win: list | None = None  # [t0, start pos, expected dx mm, expected dy mm, last t]
        self.why: dict[str, str] = {}  # task I claimed -> the reason I gave (#86)
        self.peers: dict[int, tuple[int, dict]] = {}  # boat -> (tc, payload) of newest HB
        self.shore_t = -1  # tc of the newest shore heartbeat; -1 = never heard
        self.mode = PATROL
        self.pos = (0, 0)
        self.batt = 1000
        self.cur = (0, 0)
        self.t = 0
        self.returning = False
        self.action: Action | None = None
        self.driving = False  # SENTINEL correction under way
        self.started = False
        self.detoured = False  # the stand-off ring made me skip or round part of my sweep
        self.majority_since: int | None = None
        self.majority = False
        mine = sorted(k for k, o in mission.initial if o == me and kind(k) == "seg")
        first = self.tours.pts[mine[0]] if mine else None
        self.static_point = ((first[0][0] + first[-1][0]) // 2,
                             (first[0][1] + first[-1][1]) // 2) if first else None
        stagger = me * 1_000  # five heartbeats should not land in the same tick
        self.hb_due = Every(HEARTBEAT, stagger)
        self.rec_due = Every(REBROADCAST, stagger)
        self.slot_due = Every(SLOT)
        self.rebalance_due = Every(REBALANCE, me * 60_000)
        self.direct: dict[int, int] = {}  # node -> tc of newest heartbeat heard with 0 hops

    def step(self, t: int, own: Own, seen: tuple[Detection, ...],
             inbox: list[bytes]) -> tuple[Action, list[bytes]]:
        self.t = t
        prev = self.pos
        self.pos, self.batt, self.cur = (own.x, own.y), own.batt, (own.cur_x, own.cur_y)
        self.watch_progress(t, prev)
        self.visits.credit(self.pos, t)
        for raw in inbox:
            m = self.net.receive(t, raw)
            if m is not None:
                self.on_msg(m)
        for mid in self.net.take_acks():
            self.net.send(t, "ACK", {"of": mid})
        self.net.tick(t)
        self.update_majority(t)
        self.sync_tour()
        self.contacts.tick(t, seen)
        if not self.returning and self.return_due():
            self.go_home()
        if self.may_bid(t):
            self.auction.take_over(t)
        if self.slot_due(t):
            self.auction.on_slot(t)
        if self.rebalance_due(t) and self.may_bid(t):
            self.auction.rebalance(t)
        if self.hb_due(t):
            self.net.send(t, "HB", self.heartbeat())
            for o in self.contacts.observations():
                self.net.send(t, "OBS", o)
        if self.rec_due(t):
            mine = {k: w for k, w in sorted(self.why.items()) if w and self.holds_task(k)}
            self.net.send(t, "REC", {"recs": [to_wire(r) for r in self.table.recs.values()]}
                          | ({"why": mine} if mine else {}))
            for task in self.contacts.flags:
                self.net.send(t, "CONTACT", self.contacts.message(task))
        action = self.avoid(self.behave())
        self.mode, self.action = action.mode, action
        return action, self.net.flush()

    # messages and records ------------------------------------------------------------------
    def on_msg(self, m: Msg) -> None:
        if m.kind == "HB":
            if m.hops == 0:
                self.direct[m.src] = max(self.direct.get(m.src, 0), m.tc)
            if m.src == SHORE:
                self.shore_t = max(self.shore_t, m.tc)
            else:
                self.table.heard(m.src, m.tc)
                if m.tc > self.peers.get(m.src, (-1, {}))[0]:
                    self.peers[m.src] = (m.tc, m.p)
                    self.visits.credit((m.p["x"], m.p["y"]), m.tc)
        elif m.kind == "REC":
            for w in m.p["recs"]:
                self.table.apply(from_wire(w))
        elif m.kind == "VETO":
            self.table.apply(from_wire(m.p["rec"]))
        elif m.kind == "BID":
            self.auction.on_bid(m.p)
        elif m.kind == "OBS":
            self.contacts.on_obs(m.p)
        elif m.kind == "CONTACT":
            self.contacts.on_contact(m.p)
        elif m.kind == "CMD":
            self.log("command", m.p)
            self.contacts.on_cmd(m.p)
        elif m.kind == "ACK":
            self.net.ack(m.p["of"])

    def publish(self, r: Rec) -> None:
        """Adopt a record locally and broadcast it."""
        why = self.why.get(r.task) if r.owner == self.me and r.state == CLAIMED else None
        if r.owner == self.me:
            self.log("task", {"rec": to_wire(r)} | ({"why": why} if why else {}))
        self.table.apply(r)
        self.net.send(self.t, "REC", {"recs": [to_wire(r)]} | ({"why": {r.task: why}} if why else {}))

    def claim(self, task: str, cost: int, deputy: int, why: str = "") -> None:
        self.why[task] = why
        self.publish(Rec(task, self.table.max_ver(task) + 1, CLAIMED, cost, self.me, deputy))
        for other in self.table.held_by(self.me):
            if kind(other) in DROPS.get(kind(task), ()):
                self.release(other)  # PLAN F6: free the work this boat can no longer do
        self.sync_tour()

    def release(self, task: str) -> None:
        self.why.pop(task, None)
        self.publish(Rec(task, self.table.max_ver(task) + 1, RELEASED, 0, self.me))
        self.sync_tour()

    # what this boat holds ------------------------------------------------------------------
    def holds_task(self, task: str) -> bool:
        r = self.table.recs.get(task)
        return r is not None and r.owner == self.me and r.state == CLAIMED

    def holds(self, k: str) -> bool:
        return any(kind(x) == k for x in self.table.held_by(self.me))

    def legs(self) -> list[Leg]:
        return self.follow.legs

    def station(self, task: str) -> tuple[int, int]:
        return self.stations[task]

    def sync_tour(self) -> None:
        """The table is the truth: the tour is exactly the segments this boat holds."""
        held = [k for k in self.table.held_by(self.me) if kind(k) == "seg"]
        legs = [leg for leg in self.follow.legs if leg[0] in held]
        for k in sorted(held):
            if all(leg[0] != k for leg in legs):
                legs = self.tours.insert(legs, k)
        if legs != self.follow.legs or not self.started:
            had = {leg[0] for leg in self.follow.legs}
            self.follow.set_legs(legs, self.pos)
            if self.started and any(leg[0] not in had for leg in legs):
                self.head_for_oldest()
            self.started = True

    def head_for_oldest(self) -> None:
        """After taking over segments, sweep first the one with the oldest sample this boat
        knows of (never seen counts as oldest), instead of carrying on in tour order."""
        legs, v = self.follow.legs, self.visits
        i = min(range(len(legs)), key=lambda k: (v.oldest(legs[k][0]), k))
        if v.oldest(legs[i][0]) < v.oldest(legs[self.follow.i][0]):
            self.follow.i, self.follow.j = i, 0

    # health check (#106) -------------------------------------------------------------------
    def v_plan(self) -> int:
        """The speed to plan with: cruise, or what the boat has really been making since a failed
        health check. Bids, energy checks and the return rule all use it."""
        return max(self.params.speed_mm_s * self.speed_permille // 1000, 1)

    def watch_progress(self, t: int, prev: tuple[int, int]) -> None:
        """Compare the progress the boat makes with what its own command and the current it
        measures predict (the motion is: speed towards the target, then the current). Explainable
        rule, not a diagnosis: a shortfall is evidence of a propulsion fault or of more current
        than measured, not proof of either."""
        a, p = self.action, self.params
        moving = a is not None and a.target is not None and a.mode in (PATROL, RETURNING)
        if not moving or self.win is None:
            self.win = [t, self.pos, 0, 0, t] if moving else None
            return
        dt = t - self.win[4]
        d = dist(prev, a.target)
        if d:
            step = min(a.speed_mm_s * dt // 1000, d * 1000)  # mm the motors should give
            self.win[2] += (a.target[0] - prev[0]) * step // d + self.cur[0] * dt // 1000
            self.win[3] += (a.target[1] - prev[1]) * step // d + self.cur[1] * dt // 1000
        self.win[4] = t
        if t - self.win[0] < p.health_window_ms:
            return
        t0, start, ex, ey, _ = self.win
        self.win = [t, self.pos, 0, 0, t]
        e2 = ex * ex + ey * ey
        if 4 * e2 < (p.speed_mm_s * (t - t0) // 1000) ** 2:
            return  # turned back or arrived: too little straight progress to judge
        mx, my = (self.pos[0] - start[0]) * 1000, (self.pos[1] - start[1]) * 1000
        ratio = (mx * ex + my * ey) * 1000 // e2
        self.judge(ratio, (t - t0) // 1000)

    def judge(self, ratio: int, window_s: int) -> None:
        p = self.params
        if ratio >= p.health_recover_permille:
            if self.speed_permille != 1000:  # it had replanned: say so once, then plan at cruise
                self.health, self.speed_permille = "progress back to plan", 1000
                self.log("health", {"text": self.health})
            else:
                self.health = ""
            self.fails = 0
            return
        self.fails = self.fails + 1 if ratio < p.health_min_permille else 0
        if self.fails < p.health_fails:
            return
        self.speed_permille = max(ratio, 100)
        if self.fails == p.health_fails:
            self.health = (f"progress below plan: {ratio // 10}% of predicted over {window_s} s; "
                           "possible propulsion fault or strong current (model estimate)")
            self.log("health", {"text": self.health, "ratio_permille": ratio})
            for task in self.table.held_by(self.me):  # what no longer fits at this speed
                if kind(task) != "contact" and not self.auction.energy_ok(task):
                    self.release(task)
        elif self.fails >= p.health_fails + p.health_attempts and not self.returning:
            self.health = (f"no recovery after {self.fails} checks: releasing everything and "
                           "going home")
            self.log("health", {"text": self.health, "ratio_permille": ratio})
            self.go_home()

    # energy --------------------------------------------------------------------------------
    def remaining_ms(self) -> int:
        return self.batt * self.params.endurance_ms // 1000

    def return_ms(self, frm: tuple[int, int]) -> int:
        """Time to the shore from a point, with the current this boat measures."""
        shore, v = self.mission.shore, self.v_plan()
        d = dist(frm, shore)
        if d == 0:
            return 0
        along = (self.cur[0] * (shore[0] - frm[0]) + self.cur[1] * (shore[1] - frm[1])) // d
        return ms(d, max(v + along, v // 4))

    def return_due(self) -> bool:
        p = self.params
        need = p.return_safety_permille * (self.return_ms(self.pos) + p.reserve_ms) // 1000
        return self.remaining_ms() <= need

    def go_home(self) -> None:
        """Automatic safety: release everything at once so others re-auction next slot."""
        self.returning = True
        self.log("return", {"batt": self.batt, "x": self.pos[0], "y": self.pos[1]})
        self.contacts.holding = None
        for task in self.table.held_by(self.me):
            self.release(task)

    def live_peers(self, t: int) -> int:
        return sum(1 for b, tc in self.table.last_hb.items() if b != self.me
                   and t - tc <= PEER_STALE)

    def n_active(self, t: int) -> int:
        """The whole fleet minus boats whose last heartbeat announced going home. Silence does
        not shrink it: a group cut off by range must not count itself a majority (4 km radio)."""
        return sum(1 for b in self.mission.boats if b == self.me or b not in self.peers
                   or self.peers[b][1]["mode"] not in (RETURNING, UNAVAILABLE))

    def update_majority(self, t: int) -> None:
        """Expiry takeovers need a live majority, so an isolated boat claims nothing (P4).
        After a rejoin the majority must hold for PEER_STALE first, so fresh heartbeats from
        owners we could not hear have time to arrive before anything is taken over."""
        if 1 + self.live_peers(t) < self.n_active(t) // 2 + 1:
            self.majority_since = None
        elif self.majority_since is None:
            self.majority_since = t
        self.majority = self.majority_since is not None and t - self.majority_since >= PEER_STALE

    def may_bid(self, t: int) -> bool:
        p = self.params
        if self.returning or p.policy == "static":
            return False
        return p.policy != "off" or t < p.repair_off_after_ms

    # behaviour -----------------------------------------------------------------------------
    def keep_station(self, point: tuple[int, int]) -> Action:
        d = dist(self.pos, point)
        if d > self.params.sentinel_radius_m:
            self.driving = True
        elif d <= STATION_BACK_M:
            self.driving = False
        return Action(SENTINEL, point if self.driving else None, self.params.speed_mm_s)

    def behave(self) -> Action:
        v = self.params.speed_mm_s
        if self.returning:
            if dist(self.pos, self.mission.shore) <= HOME_M:
                return Action(UNAVAILABLE, None, 0)
            return Action(RETURNING, self.mission.shore, v)
        watched = self.contacts.watching()
        if watched and not self.contacts.stale(watched.split(":", 1)[1], self.t):
            return Action(SHADOWING, self.contacts.ring(watched), v)
        hold = self.contacts.holding
        if hold:
            pos, r = self.contacts.position(task_of(hold)), self.contacts.radius(task_of(hold))
            return Action(SHADOWING, ring_point(pos, self.pos, r), v)
        held = self.table.held_by(self.me)
        if self.params.policy == "static" and self.legs():
            return self.keep_station(self.static_point)
        for task in held:
            if kind(task) in ("relay", "pick"):
                return self.keep_station(self.station(task))
        if self.legs():
            return Action(PATROL, self.follow.target(self.pos), v)
        return Action(SENTINEL, None, 0)

    # safety filter (PLAN 7.9) --------------------------------------------------------------
    def avoid(self, a: Action) -> Action:
        """A patrol or station target never takes the boat inside the stand-off ring of a contact
        with no AIS: a look closer than 1 nm is the watch officer's call (the close card). The
        boat skips waypoints inside the ring and steers round it on the tangent."""
        if a.target is None:
            return a
        target = a.target
        if a.mode in (PATROL, SENTINEL):
            r = self.params.standoff_m + STANDOFF_MARGIN_M
            rings = [(o["x"], o["y"]) for k, o in sorted(self.contacts.tracks.items())
                     if not o["ais"] and not self.contacts.stale(k, self.t)]
            if self.detoured and not rings and a.mode == PATROL:
                self.detoured = False  # the ring has gone: what it made me skip is now the oldest
                self.head_for_oldest()
                target = self.follow.target(self.pos)
            elif a.mode == PATROL:
                for _ in range(sum(len(self.tours.way(leg)) for leg in self.follow.legs)):
                    if not any(dist(target, c) <= r for c in rings):
                        break
                    self.follow.skip()
                    self.detoured = True
                    target = self.follow.target(self.pos)
            for c in rings:
                if dist(target, c) <= r:  # a station inside the ring: hold on its edge instead
                    target = ring_point(c, target, r)
                if dist(self.pos, c) <= r:
                    target = ring_point(c, self.pos, r + STANDOFF_MARGIN_M)  # straight out
                elif dist_to_line(c, (self.pos, target)) < r:
                    target = round_ring(self.pos, c, r, target)
                    self.detoured = True
        if a.mode in (PATROL, RETURNING):  # on the move: plan round AIS ships (#118)
            r = self.params.ship_clearance_m + CPA_MARGIN_M
            for c in self.ship_cpa(target, a.speed_mm_s):
                if dist(self.pos, c) <= r:
                    target = ring_point(c, self.pos, r + STANDOFF_MARGIN_M)  # open the distance
                elif dist_to_line(c, (self.pos, target)) < r:
                    target = round_ring(self.pos, c, r, target)
        if self.mission.shore == KORSOR_SHORE and len(self.tours.pts.get("seg:M:0", ())) > 2:
            target = route_water(self.pos, target)
        return Action(a.mode, target, a.speed_mm_s)

    def ship_cpa(self, target: tuple[int, int], speed: int) -> list[tuple[int, int]]:
        """Where each AIS ship will be at the closest point of approach to this boat's straight
        line, for the ships that would pass inside the clearance within the horizon. Positions are
        dead-reckoned from the last report with its course and speed: planning, not a safety
        case; the autopilot keeps final collision avoidance."""
        p, (px, py) = self.params, self.pos
        d = dist(self.pos, target)
        vox, voy = ((target[0] - px) * speed // d, (target[1] - py) * speed // d) if d else (0, 0)
        out = []
        for k, o in sorted(self.contacts.tracks.items()):
            if not o["ais"] or self.contacts.stale(k, self.t):
                continue
            vsx, vsy = o["sog"] * SIN[o["cog"] % 360] // 1000, o["sog"] * COS[o["cog"] % 360] // 1000
            age = self.t - o["to"]
            sx, sy = o["x"] * 1000 + vsx * age // 1000, o["y"] * 1000 + vsy * age // 1000  # mm now
            rx, ry, wx, wy = sx - px * 1000, sy - py * 1000, vsx - vox, vsy - voy
            w2 = wx * wx + wy * wy
            tc = min(max(-(rx * wx + ry * wy) // w2, 0), p.cpa_horizon_ms // 1000) if w2 else 0
            cx, cy = rx + wx * tc, ry + wy * tc
            if cx * cx + cy * cy < (p.ship_clearance_m * 1000) ** 2:
                out.append(((sx + vsx * tc) // 1000, (sy + vsy * tc) // 1000))
        return out

    def heartbeat(self) -> dict:
        legs = self.legs()
        cyc = ms(self.tours.cycle_m(legs), self.v_plan()) if legs else 0
        return {"x": self.pos[0], "y": self.pos[1], "mode": self.mode, "batt": self.batt,
                "cyc": cyc, "tour": [leg[0] for leg in legs],
                "roles": self.table.held_by(self.me),
                "to": list(self.action.target) if self.action and self.action.target else None,
                "spd": self.action.speed_mm_s if self.action and self.action.target else 0,
                "nbr": sorted(n for n, tc in self.direct.items() if self.t - tc <= PEER_STALE),
                "head": self.head(),
                **({"health": self.health} if self.health else {}),
                "det": self.params.r_detect_m, "kiv": self.params.keep_in_view_m}

    # evidence (#37) ------------------------------------------------------------------------
    def log(self, kind_: str, data: dict) -> None:
        t = self.t // 1000
        self.chain.append(kind_, t, t, TIME_SOURCE, f"USV {self.me:02d} on board", [], data)

    def head(self) -> list:
        """[seq, hash, sig] of this boat's chain; signed again only when it grew."""
        seq, h = self.chain.head
        if not self.signed or self.signed[0] != seq:
            sig = self.key.sign(head_message(self.chain.name, seq, h)).hex()
            self.signed = [seq, h, sig]
        return self.signed

    def view(self) -> dict:
        """JSON-safe state for /truth, state hashes and tests."""
        return {
            "me": self.me, "t": self.t, "mode": self.mode, "pos": list(self.pos),
            "batt": self.batt, "shore_t": self.shore_t, "returning": self.returning,
            "tour": [[k, rev] for k, rev in self.legs()],
            "holding": self.contacts.holding,
            "contacts": {k: dict(v) for k, v in sorted(self.contacts.flags.items())},
            "last_hb": {str(b): tc for b, tc in sorted(self.table.last_hb.items())},
            "tasks": {k: to_wire(r) for k, r in sorted(self.table.recs.items())},
        }
