"""The boat agent. Same code on every boat; no coordinator.

Inputs per tick: own position, own battery, own camera, own AIS receiver, own
radio inbox (bytes). Outputs: a navigation request and radio messages (bytes).
Time is the sim clock passed as an argument; agents never read the wall clock.
"""
from __future__ import annotations

import math

from contract.constants import (ACTIVE_SILENCE, CLAIMED, CLOSED, CUE, HEARTBEAT, HOLDING, PATROL, PEER_STALE,
                                REBALANCE, RELAY, RELEASED, RETURNING, SHADOWING, SHORE_ID, SLOT, UNAVAILABLE)
from contract.messages import Envelope, make
from contract.tasks import Mission, Rec, kind
from contract.views import Nav, Sensors

from . import auction as A
from . import contact as C
from . import cues as Q
from . import deputy as D
from . import relay as R
from . import table as T
from . import tour as TR


def _d(p, q) -> float:
    return math.hypot(p[0] - q[0], p[1] - q[1])


class Agent:
    def __init__(self, me: int, mission: Mission, cfg: dict, chain=None):
        self.me = me
        self.mission = mission
        b, r, ag = cfg["boat"], cfg["radio"], cfg["agent"]
        self.V = float(b["speed_mps"])
        self.reserve_s = int(b["reserve_s"])
        self.r_verify_m = float(b["r_verify_m"])
        self.keep_in_view_m = float(b["keep_in_view_m"])
        self.standoff_m = float(b["standoff_m"])
        self.standoff_floor_m = float(b["standoff_floor_m"])
        self.arrive_m = float(b["arrive_m"])
        self.dwell_ms = int(b["dwell_s"]) * 1000
        self.dwell_sog_mps = float(b["dwell_sog_kn"]) * 0.514444
        self.cable_near_m = float(cfg["scene"]["cable_near_m"])
        self.shadow_cap_ms = 1_800_000
        self.max_hops = int(r["max_hops"])
        self.sweep = bool(ag["sweep"])
        self.repair_cfg = bool(ag["repair"])
        self.repair = self.repair_cfg
        self.rebalance_ratio = float(ag["rebalance_ratio"])
        self.cycle_max_ms = int(ag["cycle_max_s"]) * 1000
        self.warm = False
        self.chain = chain

        self.t = 0
        self.xy = (0.0, 0.0)
        self.batt_s = 0
        self.batt_permille = 1000
        self.mode = PATROL
        self.docked = False
        self.seq = 0
        self.table: dict[str, Rec] = {}
        self.last_hb: dict[int, int] = {}
        self.peers: dict[int, dict] = {}
        self.bids: dict[int, dict[str, list]] = {}
        self.seen: dict[str, int] = {}
        self.tour: list[tuple[str, bool]] = []
        self.follower = TR.Follower()
        self.pick: str | None = None
        self.contact_obs: dict[str, dict] = {}
        self.contact_views: dict[str, dict[int, dict]] = {}
        self.dwell: dict[str, int] = {}
        self.hold_cid: str | None = None
        self.shadow_cid: str | None = None
        self.shadow_t0 = 0
        self.shadow_in_view_sent = False
        self.close_approved: dict[str, bool] = {}
        self.cue_geoms: dict[str, dict] = {}
        self.cue_task: str | None = None
        self.ais_seen: dict[str, dict] = {}
        self.reported: dict[str, int] = {}
        self.reports: list[dict] = []
        self.events: list[tuple[int, str, dict]] = []
        self.outbox: list[bytes] = []
        self.stats = {"claims": 0, "releases": 0, "msgs_in": 0, "msgs_out": 0, "forwarded": 0}
        self.repair_claims_after: dict[str, int] = {}
        self.open_since: dict[str, int] = {}
        for rec in mission.initial_records():
            self.table[rec.task] = rec
        for task, owner in sorted(mission.initial_owner.items()):
            if owner == me:
                self._adopt(task)

    # ---- lifecycle -------------------------------------------------------
    def set_warm(self, warm: bool) -> None:
        self.warm = warm
        self.repair = False if warm else self.repair_cfg

    def place(self, xy, t: int, resync: bool = True) -> None:
        self.xy = (float(xy[0]), float(xy[1]))
        self.t = t
        for b in self.mission.boats:
            self.last_hb[b] = t
        self.last_hb[SHORE_ID] = t
        if resync:
            self.follower.resync(self, self.xy)

    def _adopt(self, task: str) -> None:
        k = kind(task)
        if k == "seg":
            _, self.tour = TR.cheapest_insertion(self, self.tour, task)
        elif k == "pick":
            self.pick = task

    # ---- messaging -------------------------------------------------------
    def send(self, kind_: str, payload: dict, t: int) -> None:
        self.seq += 1
        env = make(self.me, self.seq, t, kind_, payload)
        self.seen[env.msg_id] = env.t_expire
        self.outbox.append(env.encode())
        self.stats["msgs_out"] += 1

    def publish(self, rec: Rec, t: int) -> None:
        T.on_record(self, rec, t)
        self.send("REC", {"rec": rec.tup()}, t)
        if rec.state == CLAIMED:
            self.stats["claims"] += 1
        elif rec.state == RELEASED:
            self.stats["releases"] += 1

    def log(self, kind_: str, body: dict, t: int) -> None:
        self.events.append((t, kind_, body))
        if len(self.events) > 200:
            self.events = self.events[-200:]
        if self.chain is not None:
            self.chain.append(t, kind_, body)

    def _forward(self, env: Envelope, t: int) -> None:
        if env.hops + 1 >= self.max_hops or t > env.t_expire:
            return
        self.outbox.append(env.forwarded().encode())
        self.stats["forwarded"] += 1

    def _handle(self, raw: bytes, t: int) -> None:
        env = Envelope.decode(raw)
        self.stats["msgs_in"] += 1
        if t > env.t_expire or env.msg_id in self.seen:
            return
        self.seen[env.msg_id] = env.t_expire
        p = env.payload
        k = env.kind
        if k == "HB":
            self._on_hb(env, t)
            return
        if k == "BID":
            e = int(p["e"])
            if e >= t // SLOT - 1:
                self.bids.setdefault(e, {}).setdefault(p["task"], []).append((int(p["cost"]), int(p["boat"])))
            self._forward(env, t)
        elif k == "REC":
            T.on_record(self, Rec.from_tup(p["rec"]), t)
            self._forward(env, t)
        elif k == "OBS":
            C.record_obs(self, p["cid"], p["obs"])
            self._forward(env, t)
        elif k == "CONTACT":
            if "cid" in p:
                C.record_obs(self, p["cid"], p["obs"])
                if p["cid"] not in self.table:
                    T.on_record(self, Rec(p["cid"], 1, RELEASED, 0, 0, 0), t)
            elif "cue" in p:
                self.cue_geoms.setdefault(p["cue"], p["geom"])
                if p["cue"] not in self.table:
                    T.on_record(self, Rec(p["cue"], 1, RELEASED, 0, 0, 0), t)
            self._forward(env, t)
        elif k == "VETO":
            T.on_record(self, Rec.from_tup(p["rec"]), t)
            self.log("veto_received", {"task": p["rec"][0]}, t)
            self._forward(env, t)
        elif k == "CMD":
            self._on_cmd(p, t)
            self._forward(env, t)

    def _on_hb(self, env: Envelope, t: int) -> None:
        p = env.payload
        src = env.src
        self.last_hb[src] = max(self.last_hb.get(src, -10**12), env.t_created)
        if src != SHORE_ID:
            self.peers[src] = {"x": p["x"], "y": p["y"], "mode": p["mode"], "batt": p["batt"], "cycle": p["cycle"],
                               "tour": p["tour"], "pick": p["pick"], "relay": p["relay"],
                               "shore_age": p["shore_age"], "t": env.t_created}
        for b, (x, y, mode, batt, age, cycle, pick, relay, tour) in sorted(p.get("peers", {}).items()):
            b = int(b)
            if b in (self.me, src, SHORE_ID):
                continue
            t_obs = env.t_created - age
            if b not in self.peers or self.peers[b]["t"] < t_obs:
                self.peers[b] = {"x": x, "y": y, "mode": mode, "batt": batt, "cycle": cycle, "tour": tour,
                                 "pick": pick, "relay": relay, "shore_age": 10**12, "t": t_obs}
            # gossip liveness: a peer heard this boat `age` ms before it sent, so its lease is renewed to then
            if self.last_hb.get(b, -10**12) < t_obs:
                self.last_hb[b] = t_obs
        for tup in p.get("recs", []):
            T.on_record(self, Rec.from_tup(tup), t)
        for cid, obs in sorted(p.get("contacts", {}).items()):
            C.record_obs(self, cid, obs)
        for task, geom in sorted(p.get("cues", {}).items()):
            self.cue_geoms.setdefault(task, geom)
        for cid in p.get("close_ok", []):
            self.close_approved[cid] = True

    def _on_cmd(self, p: dict, t: int) -> None:
        if p.get("action") == "close":
            self.close_approved[p["cid"]] = True
            self.log("close_approved", {"cid": p["cid"]}, t)

    def _heartbeat(self, t: int) -> None:
        peers = {}
        for b, q in sorted(self.peers.items()):
            if t - q["t"] <= ACTIVE_SILENCE:
                peers[str(b)] = [q["x"], q["y"], q["mode"], q["batt"], t - q["t"], q["cycle"], q["pick"], q["relay"], q["tour"]]
        contacts = {cid: o for cid, o in sorted(self.contact_obs.items())
                    if cid in self.table and self.table[cid].state != CLOSED}
        cues = {k: g for k, g in sorted(self.cue_geoms.items()) if k in self.table and self.table[k].state == RELEASED}
        ais = {k: v for k, v in sorted(self.ais_seen.items()) if t - v["t"] <= 180_000}
        head = self.chain.head() if self.chain is not None else None
        payload = {"x": round(self.xy[0]), "y": round(self.xy[1]), "mode": self.mode, "batt": self.batt_permille,
                   "cycle": int(A.my_cycle_s(self) * 1000), "tour": [e[0] for e in self.tour],
                   "pick": self.pick or "", "relay": A.i_am_relay(self), "shore_age": R.shore_age(self, t),
                   "path": R.shore_path(self, t),
                   "recs": [r.tup() for _, r in sorted(self.table.items())], "peers": peers,
                   "contacts": contacts, "cues": cues, "ais": ais, "head": head,
                   "close_ok": sorted(k for k, v in self.close_approved.items() if v),
                   "reports": [rp for rp in self.reports[-3:]],
                   "ev": [[et, ek, {k2: v2 for k2, v2 in eb.items() if isinstance(v2, (int, str, bool))}]
                          for et, ek, eb in self.events[-3:]]}
        self.send("HB", payload, t)

    # ---- table callbacks ---------------------------------------------------
    def on_table_change(self, cur: Rec | None, new: Rec, t: int) -> None:
        lost = cur is not None and cur.owner == self.me and cur.state == CLAIMED and \
            (new.owner != self.me or new.state != CLAIMED)
        if lost:
            self._drop(new.task, t)
        if new.state == RELEASED:
            self.open_since[new.task] = t
        else:
            self.open_since.pop(new.task, None)
        if new.owner == self.me and new.state == CLAIMED and (cur is None or cur.owner != self.me or cur.state != CLAIMED):
            pass  # adoption happens in on_won (our own publish) or deputy takeover
        if new.state == CLAIMED and new.owner != self.me and not self.warm and t >= 0:
            k = kind(new.task)
            if k in ("seg", "pick"):
                self.repair_claims_after[new.task] = self.repair_claims_after.get(new.task, 0) + 1

    def _drop(self, task: str, t: int) -> None:
        k = kind(task)
        if k == "seg":
            self.tour = TR.remove_task(self.tour, task)
            self.follower.resync(self, self.xy)
        elif k == "pick" and self.pick == task:
            self.pick = None
        elif k == "contact" and self.shadow_cid == task:
            self.log("shadow_end", {"cid": task, "why": "record_changed"}, t)
            C.end_shadow(self)
        elif k == "cue" and self.cue_task == task:
            self.cue_task = None
            if self.mode == CUE:
                self.mode = PATROL
                self.follower.resync(self, self.xy)
        elif k == "relay" and self.mode == RELAY:
            self.mode = PATROL
            self.follower.resync(self, self.xy)

    def on_won(self, task: str, t: int) -> None:
        k = kind(task)
        self.log("claim", {"task": task}, t)
        if k == "seg":
            _, self.tour = TR.cheapest_insertion(self, self.tour, task)
            self.follower.resync(self, self.xy)
            if self.pick:
                self._release(self.pick, t)
        elif k == "pick":
            self.pick = task
        elif k == "relay":
            self.mode = RELAY
            self.hold_cid = None
            for other in T.owned(self):
                if kind(other) in ("seg", "pick"):
                    self._release(other, t)
            self.tour = []
            self.pick = None
        elif k == "contact":
            self.mode = SHADOWING
            self.shadow_cid, self.shadow_t0 = task, t
            self.shadow_in_view_sent = False
            self.hold_cid = None
            self.log("shadow_start", {"cid": task}, t)
            if self.pick:
                self._release(self.pick, t)
        elif k == "cue":
            self.cue_task = task
            self.mode = CUE

    def _release(self, task: str, t: int) -> None:
        r = self.table.get(task)
        if r is None or r.owner != self.me or r.state != CLAIMED:
            return
        self.publish(Rec(task, r.ver + 1, RELEASED, 0, self.me, 0), t)
        self.log("release", {"task": task}, t)

    def _start_return(self, why: str, t: int) -> None:
        self.log("return", {"why": why, "batt_s": self.batt_s}, t)
        if self.mode == SHADOWING and self.shadow_cid:
            C.close_contact(self, self.shadow_cid, "returning", t)
            C.end_shadow(self)
        self.mode = RETURNING
        self.hold_cid = None
        for task in T.owned(self):
            if kind(task) in ("seg", "pick", "relay", "cue"):
                self._release(task, t)
        self.tour = []
        self.pick = None
        self.cue_task = None

    # ---- the tick ----------------------------------------------------------
    def step(self, s: Sensors) -> tuple[Nav, list[bytes]]:
        t = s.t
        self.t = t
        self.xy = (s.x, s.y)
        self.batt_s = s.batt_s
        self.batt_permille = s.batt_permille
        self.outbox = []
        if self.docked:
            return Nav(None, UNAVAILABLE), []
        for raw in s.inbox:
            self._handle(raw, t)
        if t % 60_000 == 0:
            self.seen = {k: v for k, v in self.seen.items() if v >= t}
        if s.ais and not self.warm:
            Q.on_ais(self, s.ais, t)
        if not self.warm:
            C.process_observations(self, s.observations, t)
            Q.expire_cues(self, t)
            D.on_tick(self, t)
            self._purge_contacts(t)
        target = self._navigate(s, t)
        if t % SLOT == 0:
            A.on_slot(self, t)
        if (t + self.me * 37_000) % REBALANCE == 0 and not self.warm:
            A.on_rebalance(self, t)
        if t % HEARTBEAT == (self.me * 1000) % HEARTBEAT:
            self._heartbeat(t)
        return Nav(target, self.mode), self.outbox

    def _purge_contacts(self, t: int) -> None:
        for cid in sorted(self.contact_obs):
            r = self.table.get(cid)
            if r is None:
                continue
            if r.state == RELEASED and t - self.contact_obs[cid]["t"] > 60_000 and self.mode != HOLDING:
                self.publish(Rec(cid, r.ver + 1, CLOSED, 0, self.me, 0), t)
                self.log("contact_close", {"cid": cid, "reason": "stale_unclaimed"}, t)

    def _navigate(self, s: Sensors, t: int):
        if self.mode == RETURNING:
            if _d(self.xy, self.mission.shore_xy) <= self.arrive_m + 100:
                self.docked = True
                self.mode = UNAVAILABLE
                self.log("docked", {}, t)
                return None
            return self.mission.shore_xy
        if not self.warm:
            if s.forced_return:
                self._start_return("hull_battery_monitor", t)
                return self.mission.shore_xy
            if self.batt_s - self.reserve_s <= _d(self.xy, self.mission.shore_xy) / self.V + 60:
                self._start_return("return_rule", t)
                return self.mission.shore_xy
        if self.mode == SHADOWING:
            return C.shadow_tick(self, t)
        if self.mode == HOLDING:
            return C.holder_tick(self, t)
        if self.mode == CUE:
            return Q.cue_tick(self, t)
        if A.i_am_relay(self):
            self.mode = RELAY
            return None if _d(self.xy, self.mission.relay_xy) <= self.arrive_m else self.mission.relay_xy
        self.mode = PATROL
        if self.cue_task and self.cue_task in self.table and self.table[self.cue_task].owner == self.me:
            self.mode = CUE
            return Q.cue_tick(self, t)
        if self.pick:
            pt = self.mission.tasks[self.pick].points[0]
            return None if _d(self.xy, pt) <= self.arrive_m else pt
        if self.tour and self.sweep:
            return self.follower.target(self, self.xy, self.arrive_m)
        return None

    # ---- introspection for the evaluator (truth panel only) -------------------
    def snapshot(self, t: int) -> dict:
        return {"id": self.me, "x": round(self.xy[0]), "y": round(self.xy[1]), "mode": self.mode,
                "batt": self.batt_permille, "tour": [e[0] for e in self.tour], "pick": self.pick,
                "relay": A.i_am_relay(self), "shore_age": min(R.shore_age(self, t), 10**9),
                "path": R.shore_path(self, t), "cycle_s": int(A.my_cycle_s(self)),
                "shadow": self.shadow_cid, "hold": self.hold_cid, "cue": self.cue_task,
                "reports_queued": sum(1 for r in self.reports if r.get("queued"))}
