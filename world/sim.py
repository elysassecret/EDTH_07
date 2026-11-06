"""The simulation: one process, 1 s ticks, integer milliseconds, range-filtered messages.

Each tick: world.step (motion, battery, scripted events), radio.deliver,
agents step in ID order with only their own sensors and inbox, shore steps,
observers update, then snapshot and state hash when due.

Warm-up: the same system runs from t = -warm_s to 0 with repair off and no
battery drain, so every mode starts from identical positions and ages.
"""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

import numpy as np

from agent.core import Agent
from agent.shore import Shore
from contract.config import ROOT, load_scenario
from contract.constants import RETURNING, SHORE_ID, UNAVAILABLE
from contract.views import Sensors
from evidence.chain import Chain

from . import geo
from .channel import ChannelTape
from .motion import Boat, Vessel
from .radio import Radio
from .routes import load_scene
from .sensors import ais_in_range, camera

try:
    from ais.replay import AisReplay
except Exception:  # pragma: no cover
    AisReplay = None


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL,
                                       text=True).strip()
    except Exception:
        return "nogit"


class RunLog:
    def __init__(self, path: Path | None):
        self.path = path
        self.f = open(path, "w", encoding="utf-8") if path else None
        self.hashes: list[tuple[int, str]] = []

    def write(self, obj: dict) -> None:
        if self.f:
            self.f.write(json.dumps(obj, separators=(",", ":"), sort_keys=True) + "\n")

    def close(self) -> None:
        if self.f:
            self.f.close()
            self.f = None


class Sim:
    def __init__(self, cfg: dict, mode: str = "elysa", seed: int = 1, scenario: list[dict] | None = None,
                 use_ais: bool = True, evidence: bool = True, log_path: Path | None = None):
        self.cfg = cfg
        self.mode = mode
        self.seed = int(seed)
        self.scene = load_scene(cfg)
        self.mission = self.scene.mission()
        self.events = scenario if scenario is not None else load_scenario()
        self.rng = np.random.default_rng(self.seed)
        run = cfg["run"]
        self.warm_ms = int(run["warm_s"]) * 1000
        self.horizon_ms = int(run["horizon_s"]) * 1000
        self.snapshot_every = int(run["snapshot_every_s"]) * 1000
        self.hash_every = int(run["hash_every_s"]) * 1000
        self.t = -self.warm_ms
        nodes = [SHORE_ID, *self.mission.boats]
        r = cfg["radio"]
        rng_tape, rng_phase = self.rng.spawn(2)
        self.tape = ChannelTape(nodes, int(run["warm_s"]) + int(run["horizon_s"]) + 7200, -int(run["warm_s"]),
                                float(r["loss"]), tuple(r["delay_s"]), rng_tape)
        self.radio = Radio(cfg, self.tape)
        self.chains = {b: Chain(b, self.seed) for b in self.mission.boats} if evidence else {}
        self.agents = {b: Agent(b, self.mission, cfg, self.chains.get(b)) for b in self.mission.boats}
        self.shore = Shore(self.mission, cfg)
        bc = cfg["boat"]
        self.boats: dict[int, Boat] = {}
        self.phase = {b: float(rng_phase.random()) for b in self.mission.boats}
        for b in self.mission.boats:
            ag = self.agents[b]
            if ag.tour:
                from agent.tour import place_on_loop
                xy = place_on_loop(ag, self.phase[b])
            elif ag.pick:
                xy = self.mission.tasks[ag.pick].points[0]
            else:
                xy = self.mission.relay_xy
            self.boats[b] = Boat(b, xy[0], xy[1], float(bc["speed_mps"]), int(bc["endurance_s"]), int(bc["endurance_s"]))
            ag.set_warm(True)
            ag.place(xy, self.t, resync=not ag.tour)
        self.radio.positions[SHORE_ID] = self.mission.shore_xy
        self._sync_positions()
        self.vessels: dict[str, Vessel] = {}
        self.r_detect = {k: int(v) for k, v in bc["r_detect_m"].items()}
        self.ais_a, self.ais_b = float(bc["ais_class_a_m"]), float(bc["ais_class_b_m"])
        self.shore_ais_m = float(r["shore_ais_m"])
        self.boat_ais_recent: dict[int, dict[str, tuple[float, float, int]]] = {b: {} for b in self.mission.boats}
        reset = next((e for e in self.events if e["kind"] == "reset"), {})
        self.ais = AisReplay(None, reset.get("ais_t0", "2026-11-03T10:15:00")) if (use_ais and AisReplay) else None
        if self.ais is not None and not self.ais.available:
            self.ais = None
        self.injections: list[dict] = []
        self.pending: list[dict] = []
        self.applied: list[dict] = []
        self.observers: list = []
        self.warm_hash = ""
        self.log = RunLog(log_path)
        self.ticks = 0
        self.last_snapshot: dict | None = None
        self.log.write({"schema": 1, "seed": self.seed, "mode": mode, "config_hash": cfg["_hash"],
                        "git": git_commit(), "tape_hash": self.tape.hash(), "warm_s": run["warm_s"],
                        "horizon_s": run["horizon_s"]})

    # ---- helpers -----------------------------------------------------------
    def _sync_positions(self) -> None:
        for b, boat in self.boats.items():
            self.radio.positions[b] = (boat.x, boat.y)

    def inject(self, ev: dict) -> None:
        """Runtime injection (judge or operator). Applied at the next tick, logged for replay."""
        ev = dict(ev)
        ev["t"] = self.t // 1000 + 1
        self.pending.append(ev)

    def _apply(self, ev: dict, t: int) -> None:
        k = ev["kind"]
        if k == "reset":
            pass
        elif k == "battery_low":
            boat = self.boats[int(ev["boat"])]
            boat.forced_return = True
            home = math.hypot(boat.x - self.mission.shore_xy[0], boat.y - self.mission.shore_xy[1])
            boat.batt_s = min(boat.batt_s, int(self.cfg["boat"]["reserve_s"] + home / boat.speed_mps + 300))
        elif k == "link_off":
            a, b = self._node(ev["a"]), self._node(ev["b"])
            self.radio.cut.add((a, b))
            self.radio.cut.add((b, a))
        elif k == "link_on":
            a, b = self._node(ev["a"]), self._node(ev["b"])
            self.radio.cut.discard((a, b))
            self.radio.cut.discard((b, a))
        elif k == "contact_start":
            x, y = geo.ll_to_xy(float(ev["lat"]), float(ev["lon"])) if "lat" in ev else (float(ev["x"]), float(ev["y"]))
            self.vessels[ev["id"]] = Vessel(ev["id"], x, y, float(ev.get("sog_kn", 0.0)), float(ev.get("course", 0.0)),
                                            bool(ev.get("ais", False)), ev.get("class", "dusk"), t)
        elif k == "contact_depart":
            v = self.vessels.get(ev["id"])
            if v:
                v.sog_kn = float(ev["sog_kn"])
                v.course_deg = float(ev["course"])
                v.departed = True
        elif k == "contact_remove":
            self.vessels.pop(ev["id"], None)
        elif k == "boat_fail":
            b = int(ev["boat"])
            self.boats[b].failed = True
            self.radio.silent.add(b)
        elif k == "boat_restore":
            b = int(ev["boat"])
            self.boats[b].failed = False
            self.radio.silent.discard(b)
        elif k == "cmd":
            self.shore.command(ev, t)
        elif k == "evaluate":
            for o in self.observers:
                if hasattr(o, "update"):
                    pass
        self.applied.append({"t": t // 1000, **{a: b for a, b in ev.items() if a != "t"}})
        self.log.write({"event": ev, "t": t})

    def _node(self, x) -> int:
        return SHORE_ID if x in ("shore", 0, "0") else int(x)

    # ---- the tick -------------------------------------------------------------
    def step(self) -> None:
        self.t += 1000
        t = self.t
        self.ticks += 1
        warm = t <= 0
        if t == 0:
            self._end_warm()
        # scripted events and injections
        if not warm:
            for ev in self.events:
                if ev["t"] * 1000 == t:
                    self._apply(ev, t)
            due = [e for e in self.pending if e["t"] * 1000 <= t]
            self.pending = [e for e in self.pending if e["t"] * 1000 > t]
            for ev in due:
                self.injections.append(ev)
                self._apply(ev, t)
        # world motion
        for b, boat in sorted(self.boats.items()):
            boat.step(1.0, drain=not warm)
        for v in self.vessels.values():
            v.step(1.0)
        self._sync_positions()
        # AIS pings this second
        pings = self.ais.between(t - 1000, t) if (self.ais is not None and not warm) else []
        if pings:
            for p in pings:
                if math.hypot(p.x - self.mission.shore_xy[0], p.y - self.mission.shore_xy[1]) <= self.shore_ais_m:
                    cur = self.shore.ais.get(p.track)
                    if cur is None or p.t_ms > cur["t"]:
                        self.shore.ais[p.track] = {"x": round(p.x), "y": round(p.y), "sog": p.sog_kn, "cog": p.cog_deg,
                                                   "t": p.t_ms, "type": p.ship_type}
            for o in self.observers:
                if hasattr(o, "on_ais"):
                    o.on_ais(pings, t)
        # radio delivery
        self.radio.deliver(t)
        # agents
        vessels = [v for _, v in sorted(self.vessels.items())]
        for b in self.mission.boats:
            boat = self.boats[b]
            ag = self.agents[b]
            if boat.failed:
                self.radio.take_inbox(b)
                continue
            inbox = self.radio.take_inbox(b)
            my_pings = ais_in_range((boat.x, boat.y), pings, self.ais_a, self.ais_b) if pings else []
            recent = self.boat_ais_recent[b]
            for p in my_pings:
                recent[p.track] = (p.x, p.y, p.t_ms)
            if t % 60_000 == 0:
                for k in [k for k, v in recent.items() if t - v[2] > 120_000]:
                    recent.pop(k)
            obs = camera(boat, vessels, self.r_detect, recent, t) if vessels else []
            s = Sensors(t, boat.x, boat.y, boat.batt_s, boat.batt_permille, boat.speed_mps, obs, my_pings, inbox,
                        boat.forced_return)
            nav, out = ag.step(s)
            boat.mode = nav.mode
            boat.target = nav.target
            boat.docked = ag.docked
            boat.tour = [e[0] for e in ag.tour]
            if boat.docked:
                self.radio.silent.add(b)
            for m in out:
                self.radio.send(t, b, m)
        shore_out = self.shore.step(t, self.radio.take_inbox(SHORE_ID))
        for m in shore_out:
            self.radio.send(t, SHORE_ID, m)
        # observers and logging
        for o in self.observers:
            o.update(t)
        if not warm:
            if t % self.snapshot_every == 0:
                snap = self.truth_view()
                self.log.write({"snapshot": snap})
                self.last_snapshot = snap
            if t % self.hash_every == 0:
                h = self.state_hash()
                self.log.hashes.append((t, h))
                self.log.write({"t": t, "hash": h})

    def _end_warm(self) -> None:
        for b, ag in self.agents.items():
            ag.set_warm(False)
            self.boats[b].batt_s = self.boats[b].endurance_s
        self.warm_hash = self.state_hash()
        self.log.write({"warm_hash": self.warm_hash, "t": 0,
                        "phase": {str(b): round(p, 6) for b, p in sorted(self.phase.items())}})

    def run_warm(self) -> None:
        while self.t < 0:
            self.step()

    def run_until(self, t_s: int) -> None:
        while self.t < t_s * 1000:
            self.step()

    def state_hash(self) -> str:
        h = hashlib.sha256()
        h.update(str(self.t).encode())
        for b, boat in sorted(self.boats.items()):
            h.update(f"{b}:{boat.x:.3f}:{boat.y:.3f}:{boat.batt_s}:{boat.mode}:{boat.failed}:{boat.docked}".encode())
            ag = self.agents[b]
            h.update(json.dumps([r.tup() for _, r in sorted(ag.table.items())], separators=(",", ":")).encode())
            h.update(json.dumps(ag.tour, separators=(",", ":")).encode())
        for v in sorted(self.vessels.values(), key=lambda v: v.id):
            h.update(f"{v.id}:{v.x:.3f}:{v.y:.3f}".encode())
        h.update(json.dumps([r.tup() for _, r in sorted(self.shore.table.items())], separators=(",", ":")).encode())
        return h.hexdigest()[:16]

    # ---- views ------------------------------------------------------------------
    def truth_view(self) -> dict:
        t = self.t
        boats = []
        for b, boat in sorted(self.boats.items()):
            s = self.agents[b].snapshot(t)
            s.update({"x": round(boat.x), "y": round(boat.y), "batt": boat.batt_permille, "failed": boat.failed,
                      "docked": boat.docked, "mode": boat.mode, "target": boat.target})
            boats.append(s)
        tasks = {}
        for task in sorted(self.mission.tasks):
            best = None
            for b, ag in sorted(self.agents.items()):
                r = ag.table.get(task)
                if r is not None and (best is None or (r.ver, r.state, -r.bid, r.owner) > (best.ver, best.state, -best.bid, best.owner)):
                    best = r
            if best is not None:
                tasks[task] = {"v": best.ver, "owner": best.owner, "deputy": best.deputy, "state": best.state}
        for b, ag in sorted(self.agents.items()):
            for task, r in ag.table.items():
                if task not in tasks:
                    tasks[task] = {"v": r.ver, "owner": r.owner, "deputy": r.deputy, "state": r.state}
        metrics = {}
        for o in self.observers:
            if hasattr(o, "seg_age"):
                metrics = {"seg_age": o.seg_age(t), "km_overdue": round(o.km_overdue(t), 1),
                           "worst_age_s": o.worst_age(t), "crossings": len(o.crossings),
                           "crossings_in_view": sum(1 for c in o.crossings if c["in_view"])}
        hops = self.radio.shore_reach()
        return {"t": t // 1000, "boats": boats, "tasks": tasks, "metrics": metrics,
                "vessels": [{"id": v.id, "x": round(v.x), "y": round(v.y), "sog_kn": v.sog_kn, "course": v.course_deg,
                             "ais": v.ais, "cls": v.cls} for v in sorted(self.vessels.values(), key=lambda v: v.id)],
                "links": [[a, b] for a, b in self.radio.graph()], "hops": {str(k): v for k, v in hops.items()},
                "cut": sorted([a, b] for a, b in self.radio.cut if a < b), "failed": sorted(self.radio.silent),
                "events": self.applied[-30:], "radio": dict(self.radio.stats)}

    def shore_view(self) -> dict:
        v = self.shore.view(self.t)
        v["t"] = self.t // 1000
        return v

    def evidence_bundle(self) -> dict:
        witnessed: dict[str, list] = {}
        for b, ag in sorted(self.agents.items()):
            for q, info in ag.peers.items():
                pass
        # heads witnessed by shore in heartbeats
        for b, q in sorted(self.shore.boats.items()):
            if q.get("head"):
                witnessed.setdefault(str(b), []).append(q["head"])
        return {"seed": self.seed, "mode": self.mode, "chains": {str(b): c.dump() for b, c in sorted(self.chains.items())},
                "witnessed": witnessed}
