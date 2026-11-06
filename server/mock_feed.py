"""Mock snapshot feed for the operator console. Owner: C.

Stand-in for the real sim (world/ + agent/) until it exists, so the console never waits.

    uv run python -m server.mock_feed --port 8765 --seed 1

    ws://localhost:8765/shore   delivered data only (what the shore station would know)
    ws://localhost:8765/truth   everything, for the evaluator panel (labelled TRUTH in the UI)

Every message is JSON with a "type": "scene" (sent once on connect: segments, stations),
"snapshot" (5-10 Hz) or "ack" (reply to a command).

Every number in this file is a MOCK INPUT chosen to exercise the console, not a sim result.
Geometry comes from data/scene-coordinates.json and config/*.toml.

Deterministic: the world never reads the wall clock and only uses its own seeded Random.
Same seed + same command list at the same sim times -> byte-identical snapshots.
Times in snapshots are sim seconds since t0 (t0_utc is the wall-clock label for t = 0).
Every point list (trail, route, segments, stations) is [lon, lat].
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import logging
import math
import random
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE_FILE = ROOT / "data" / "scene-coordinates.json"
log = logging.getLogger("mock_feed")

# Snapshots follow contract/views.py (Snapshot, schema_version 1); tests validate against it.
# Extra keys the contract does not have yet are marked "console extra" below; pydantic ignores
# them, and each one is listed in server/README.md as a proposed contract addition.
SCHEMA_VERSION = 1
LINK_WORD = {"direct": "direct", "relay": "peer", "none": "none"}  # contract Boat.link
DEC_STATE = {"waiting": "pending", "active": "pending", "confirmed": "approved",
             "approved": "approved", "stopped": "declined", "declined": "declined",
             "expired": "expired", "withdrawn": "expired"}  # contract Decision.state
T0_UTC = "2026-11-03T10:15:00Z"  # scenarios/fixed.toml ais_t0, treated as UTC (unverified)
LAT0, LON0 = 55.40, 11.00  # local frame origin, BUILD_PLAN step 5
EARTH_R = 6_371_000.0
KN = 0.514444  # m/s per knot

MODES = ("PATROL", "ECO", "SENTINEL", "DORMANT", "SHADOWING", "RETURNING", "UNAVAILABLE")
DRIFT_RADIUS_M = 150.0  # mock SENTINEL drift circle
VISIT_M = 300.0  # a sweeping boat within this distance "visits" a segment sample (mock)
SEG_COUNTS = {"H": 2, "G": 3, "M": 1}  # matches the task table in BUILD_PLAN
SEG_CABLE = {"H": "HVDC_Storebaelt_I", "G": "Great_Belt_1_fibre", "M": "MV_60kV_Sprogo_Funen"}
UNANSWERED_ALARM_S = 300  # research notes: "Unanswered: repeats in 05:00, then alarm"


# ---------------------------------------------------------------- geometry

def to_xy(lat: float, lon: float) -> tuple[float, float]:
    x = EARTH_R * math.radians(lon - LON0) * math.cos(math.radians(LAT0))
    y = EARTH_R * math.radians(lat - LAT0)
    return x, y


def to_ll(x: float, y: float) -> tuple[float, float]:
    lat = LAT0 + math.degrees(y / EARTH_R)
    lon = LON0 + math.degrees(x / (EARTH_R * math.cos(math.radians(LAT0))))
    return lat, lon


def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Degrees true from a to b."""
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360.0


def resample(pts: list[tuple[float, float]], step: float) -> list[tuple[float, float]]:
    out = [pts[0]]
    carry = 0.0
    for a, b in itertools.pairwise(pts):
        seg = dist(a, b)
        d = step - carry
        while d <= seg:
            f = d / seg
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            d += step
        carry = seg - (d - step)
    if dist(out[-1], pts[-1]) > 1.0:
        out.append(pts[-1])
    return out


def inside(p: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    x, y = p
    hit = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


def path_len(pts: list[tuple[float, float]]) -> float:
    return sum(dist(a, b) for a, b in itertools.pairwise(pts))


def point_at(pts: list[tuple[float, float]], s: float) -> tuple[tuple[float, float], float]:
    """Point at distance s along the polyline, and the heading there."""
    for a, b in itertools.pairwise(pts):
        seg = dist(a, b)
        if s <= seg or b is pts[-1]:
            f = 0.0 if seg == 0 else min(1.0, s / seg)
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f), bearing(a, b)
        s -= seg
    return pts[-1], 0.0


def dist_along(pts: list[tuple[float, float]], i: int) -> float:
    """Distance along the polyline to vertex i."""
    return sum(dist(a, b) for a, b in itertools.pairwise(pts[: i + 1]))


def r6(v: float) -> float:
    return round(v, 6)


def lonlat(p: tuple[float, float]) -> list[float]:
    """Local metres -> [lon, lat], the GeoJSON/MapLibre order used for every point list."""
    lat, lon = to_ll(*p)
    return [r6(lon), r6(lat)]


# ---------------------------------------------------------------- scene

@dataclass
class Scene:
    box: list[tuple[float, float]]  # x, y corners
    segments: dict[str, list[tuple[float, float]]]  # seg id -> samples (x, y), 100 m apart
    shore: tuple[float, float]
    stations: dict[str, tuple[float, float]]
    boat: dict
    radio: dict
    ui: dict


def load_scene() -> Scene:
    sc = json.loads(SCENE_FILE.read_text(encoding="utf-8"))
    cfg = tomllib.loads((ROOT / "config" / "scene.toml").read_text(encoding="utf-8"))
    boat = tomllib.loads((ROOT / "config" / "boat.toml").read_text(encoding="utf-8"))
    radio = tomllib.loads((ROOT / "config" / "radio.toml").read_text(encoding="utf-8"))
    ui = json.loads((ROOT / "config" / "ui.json").read_text(encoding="utf-8"))
    c = sc["box"]["corners_wgs84"]
    box = [to_xy(c[k]["lat"], c[k]["lon"]) for k in ("NW", "NE", "SE", "SW")]
    step = float(cfg["sample_step_m"])
    segments: dict[str, list[tuple[float, float]]] = {}
    for code, n in SEG_COUNTS.items():
        line = [to_xy(lat, lon) for lat, lon in sc["cables"][SEG_CABLE[code]]["lat_lon"]]
        samples = resample(line, step)
        # longest contiguous run of samples inside the box
        best: list[tuple[float, float]] = []
        run: list[tuple[float, float]] = []
        for p in samples:
            if inside(p, box):
                run.append(p)
                if len(run) > len(best):
                    best = list(run)
            else:
                run = []
        per = (len(best) - 1) / n
        for i in range(n):
            a, b = round(i * per), round((i + 1) * per)
            segments[f"seg:{code}:{i}"] = best[a : b + 1]
    stations = {
        "relay": to_xy(*cfg["relay_station"]),
        "pick:N": to_xy(*cfg["picket_n"]),
        "pick:S": to_xy(*cfg["picket_s"]),
    }
    return Scene(box, segments, to_xy(*cfg["shore"]), stations, boat, radio, ui)


# ---------------------------------------------------------------- world state

@dataclass
class Boat:
    id: int
    pos: tuple[float, float]
    hdg: float = 0.0
    sog: float = 0.0  # m/s
    mode: str = "PATROL"
    endurance_s: float = 25200.0
    radio_on: bool = True
    path: list[tuple[float, float]] | None = None
    u: float = 0.0  # unfolded distance along path (ping-pong)
    target: tuple[float, float] | None = None
    on_arrive: str = ""  # "dock" | "hold" | "close"
    station: tuple[float, float] | None = None
    phase: float = 0.0
    saved: tuple[list[tuple[float, float]], float] | None = None  # sweep to resume


@dataclass
class Contact:
    id: str
    pos: tuple[float, float]
    sog: float  # m/s
    cog: float
    ais: bool
    name: str | None
    cls: str  # detection class from config/boat.toml r_detect_m
    active: bool = True
    detected: bool = False
    last_seen: float | None = None
    seen_pos: tuple[float, float] | None = None
    seen_by: list[int] = field(default_factory=list)
    trail: list[tuple[float, float]] = field(default_factory=list)
    trail_t: float = -1e9
    first_seen: float | None = None
    looked: bool = False
    name_status: str = "NOT READ"
    anchor_status: str = "NOT SEEN"


class MockWorld:
    """Deterministic fake of the swarm, driven by the fixed event tape and operator commands."""

    def __init__(self, seed: int = 1, scene: Scene | None = None):
        self.seed = seed
        self.sc = scene or load_scene()
        self.rng = random.Random(seed)
        self.v = float(self.sc.boat["speed_mps"])
        self.reserve = float(self.sc.boat["reserve_s"])
        self.t_ms = 0
        self.events: list[dict] = []
        self.alerts: dict[str, dict] = {}
        self.decisions: dict[str, dict] = {}
        self.cut: set[tuple[str, str]] = set()
        self.tasks: dict[str, dict] = {}
        self.shore_view: dict[int, dict] = {}
        self.event_times: list[float] = []
        self.pending: list[tuple[float, str, dict]] = []  # (t_s, kind, args), sorted
        self.n_dec = 0
        self._build()

    # ---- setup
    def _build(self) -> None:
        sc, rng = self.sc, self.rng
        g_path = [p for k in ("seg:G:0", "seg:G:1", "seg:G:2") for p in sc.segments[k]]
        m_path = sc.segments["seg:M:0"]
        # boat 01 sweeps Great Belt 1 then 60 kV; ends nearest each other are joined by transit
        if dist(g_path[-1], m_path[0]) > dist(g_path[-1], m_path[-1]):
            m_path = m_path[::-1]
        p1 = g_path + m_path
        p2 = sc.segments["seg:H:0"] + sc.segments["seg:H:1"]
        self.paths = {1: p1, 2: p2}
        self.boats: dict[int, Boat] = {}
        for i in range(1, 6):
            self.boats[i] = Boat(i, sc.stations["relay"], endurance_s=rng.uniform(21000, 25200),
                                 phase=rng.uniform(0, 2 * math.pi))
        self._set_path(self.boats[1], p1, rng.uniform(0, 2 * path_len(p1)))
        # boat 02's phase is chosen so its camera first reaches C-07 near t = 7500 s
        # (the demo seed in BUILD_PLAN), with a per-seed jitter, so detection time varies by seed
        self._set_path(self.boats[2], p2, self._phase_for_detection(p2, 7500 + rng.uniform(-90, 90)))
        for bid, st in ((3, "pick:N"), (4, "pick:S"), (5, "relay")):
            self._hold(self.boats[bid], sc.stations[st])
        own = {"seg:G:0": 1, "seg:G:1": 1, "seg:G:2": 1, "seg:M:0": 1, "seg:H:0": 2,
               "seg:H:1": 2, "pick:N": 3, "pick:S": 4, "relay": 5}
        self.tasks = {k: {"v": 1, "owner": o, "deputy": 0, "state": 1} for k, o in own.items()}
        self.seg_age = {k: float(rng.randint(0, 3000)) for k in sc.segments}
        # synthetic AIS traffic along the measured lane, both directions
        sc_json = json.loads(SCENE_FILE.read_text(encoding="utf-8"))
        lane = [to_xy(p["lat"], p["lon"]) for p in sc_json["lane_measured_from_ais"]["centreline"]]
        self.lane = lane
        self.lane_len = path_len(lane)
        self.contacts: dict[str, Contact] = {}
        self.ais_tracks: dict[str, tuple[float, float, int]] = {}
        for k in range(6):
            cid = f"AIS-{k + 1:02d}"
            sog = rng.uniform(9, 13) * KN
            u0 = rng.uniform(0, self.lane_len)
            d = 1 if k % 2 == 0 else -1
            self.ais_tracks[cid] = (u0, sog, d)
            self.contacts[cid] = Contact(cid, lane[0], sog, 0.0, True, f"MOCK CARGO {k + 1}",
                                         "ship_day")
        self._move_ais(0.0)
        for e in self._tape():
            self.pending.append(e)
            self.event_times.append(e[0])
        self.pending.sort(key=lambda e: e[0])
        self._event("reset", f"Reset, seed {self.seed}. Mock feed, not sim output.")

    def _tape(self) -> list[tuple[float, str, dict]]:
        tape = tomllib.loads((ROOT / "scenarios" / "fixed.toml").read_text(encoding="utf-8"))
        out = []
        for e in tape["event"]:
            if e["kind"] in ("reset",):
                continue
            out.append((float(e["t"]), e["kind"], dict(e)))
        return out

    def _phase_for_detection(self, path: list[tuple[float, float]], want_t: float) -> float:
        c07 = to_xy(55.4505, 10.8706)  # scenarios/fixed.toml contact_start
        r = float(self.sc.boat["r_detect_m"]["dusk"])
        L = path_len(path)
        probe = Boat(0, (0.0, 0.0), path=path)
        best, best_err = 0.0, float("inf")
        for k in range(int(2 * L // 100)):
            u0 = k * 100.0
            first = None
            for dt in range(0, 3000, 10):
                probe.u = u0 + self.v * (7320 + dt)
                self._place_on_path(probe)
                if dist(probe.pos, c07) <= r:
                    first = 7320 + dt
                    break
            if first is not None and abs(first - want_t) < best_err:
                best, best_err = u0, abs(first - want_t)
        return best

    def _set_path(self, b: Boat, path: list[tuple[float, float]], u: float) -> None:
        b.path, b.u, b.target, b.station = path, u, None, None
        b.mode = "PATROL"
        self._place_on_path(b)

    def _place_on_path(self, b: Boat) -> None:
        assert b.path is not None
        L = path_len(b.path)
        uu = b.u % (2 * L)
        fwd = uu <= L
        p, h = point_at(b.path, uu if fwd else 2 * L - uu)
        b.pos, b.hdg = p, h if fwd else (h + 180) % 360

    def _drift(self, b: Boat) -> tuple[float, float]:
        tt = self.t / 600.0 + b.phase
        return DRIFT_RADIUS_M * math.sin(tt), DRIFT_RADIUS_M * math.cos(tt)

    def _hold(self, b: Boat, here: tuple[float, float], mode: str = "SENTINEL") -> None:
        """Hold near `here`: drift-and-correct circle, no jump from the current position."""
        dx, dy = self._drift(b)
        b.path, b.target, b.mode = None, None, mode
        b.station = (here[0] - dx, here[1] - dy)
        b.pos = here

    def _goto(self, b: Boat, p: tuple[float, float], on_arrive: str, mode: str) -> None:
        b.path, b.station, b.target, b.on_arrive, b.mode = None, None, p, on_arrive, mode

    # ---- helpers
    @property
    def t(self) -> float:
        return self.t_ms / 1000.0

    def _event(self, kind: str, text: str, exercise: bool = False) -> None:
        self.events.append({"t": round(self.t, 1), "kind": kind, "text": text,
                            "exercise": exercise})

    def _alert(self, key: str, level: str, text: str) -> None:
        a = self.alerts.get(key)
        if a and a["active"] and a["level"] == level and a["text"] == text:
            return  # dedup
        self.alerts[key] = {"key": key, "level": level, "text": text, "t": round(self.t, 1),
                            "active": True, "acked": False}

    def _clear(self, key: str) -> None:
        if key in self.alerts:
            self.alerts[key]["active"] = False

    def _decision(self, tier: str, text: str, boat: int, contact: str | None,
                  actions: list[str], route: list[tuple[float, float]] | None, kind: str) -> str:
        self.n_dec += 1
        did = f"D-{self.n_dec:03d}"
        self.decisions[did] = {
            "id": did, "tier": tier, "kind": kind, "text": text, "boat": boat,
            "contact": contact, "actions": actions, "created": round(self.t, 1),
            "status": "waiting" if tier == "held" else "active",
            "route": [lonlat(p) for p in route] if route else None,
        }
        return did

    def _tasks_of(self, bid: int) -> list[str]:
        return sorted(k for k, r in self.tasks.items() if r["owner"] == bid and r["state"] == 1)

    def _claim(self, task: str, bid: int, state: int = 1) -> None:
        r = self.tasks.setdefault(task, {"v": 0, "owner": 0, "deputy": 0, "state": 0})
        r.update(v=r["v"] + 1, owner=bid if state == 1 else r["owner"], state=state)

    def _release(self, task: str) -> None:
        self._claim(task, 0, state=0)

    # ---- radio
    def _links(self) -> tuple[list[dict], dict[int, tuple[str, int | str | None]]]:
        rb, rs = float(self.sc.radio["boat_m"]), float(self.sc.radio["shore_m"])
        up = [b for b in self.boats.values() if b.radio_on]
        links, adj = [], {b.id: [] for b in up}
        adj_shore: list[int] = []
        for b in up:
            d = dist(b.pos, self.sc.shore)
            if d <= rs:
                cut = (str(b.id), "shore") in self.cut
                links.append({"a": b.id, "b": "shore", "ok": not cut, "m": round(d)})
                if not cut:
                    adj_shore.append(b.id)
        for i, a in enumerate(up):
            for b in up[i + 1:]:
                d = dist(a.pos, b.pos)
                if d <= rb:
                    cut = (str(a.id), str(b.id)) in self.cut or (str(b.id), str(a.id)) in self.cut
                    links.append({"a": a.id, "b": b.id, "ok": not cut, "m": round(d)})
                    if not cut:
                        adj[a.id].append(b.id)
                        adj[b.id].append(a.id)
        # breadth-first from shore; "via" is the next hop toward shore
        status: dict[int, tuple[str, int | str | None]] = {
            b.id: ("none", None) for b in self.boats.values()}
        frontier = sorted(adj_shore)
        for bid in frontier:
            status[bid] = ("direct", "shore")
        seen = set(frontier)
        while frontier:
            nxt = []
            for bid in frontier:
                for n in sorted(adj[bid]):
                    if n not in seen:
                        seen.add(n)
                        status[n] = ("relay", bid)
                        nxt.append(n)
            frontier = nxt
        # cut links that are in range are kept in the list (drawn crossed); cut links out of
        # range are listed too, so the operator still sees the injected failure
        for a, b in sorted(self.cut):
            if not any(str(x["a"]) == a and str(x["b"]) == b for x in links):
                links.append({"a": int(a), "b": b if b == "shore" else int(b), "ok": False,
                              "m": None})
        return links, status

    # ---- commands
    def command(self, msg: dict) -> dict:
        cmd = msg.get("cmd")
        did = msg.get("id")
        try:
            if cmd in ("confirm", "stop", "approve", "decline"):
                return self._answer(cmd, str(did))
            if cmd == "inject":
                return self._inject(msg)
            if cmd == "ack":
                if did not in self.alerts:
                    return {"ok": False, "error": f"no alert {did}"}
                self.alerts[did]["acked"] = True
                return {"ok": True}
            return {"ok": False, "error": f"unknown cmd {cmd!r}"}
        except (KeyError, ValueError, TypeError) as e:
            return {"ok": False, "error": f"bad command: {e}"}

    def _answer(self, cmd: str, did: str) -> dict:
        d = self.decisions.get(did)
        if d is None:
            return {"ok": False, "error": f"no decision {did}"}
        if cmd not in d["actions"]:
            return {"ok": False, "error": f"{did} takes {d['actions']}, not {cmd}"}
        if d["status"] not in ("waiting", "active"):
            return {"ok": False, "error": f"{did} is {d['status']}, no longer open"}
        d["status"] = {"confirm": "confirmed", "stop": "stopped", "approve": "approved",
                       "decline": "declined"}[cmd]
        d["answered"] = round(self.t, 1)
        self._event("decision", f"{did} {d['status']} by watch officer: {d['text']}")
        self._clear(f"decision:{did}")
        b = self.boats[d["boat"]]
        c = self.contacts.get(d["contact"] or "")
        if d["kind"] == "keep_in_view" and cmd == "stop" and c:
            self._claim(f"contact:{c.id}", 0, state=2)  # VETOED
            self._back_to_picket(b)
            for o in self.decisions.values():
                if o["contact"] == c.id and o["status"] == "waiting":
                    o["status"] = "withdrawn"
        if d["kind"] == "close_look" and cmd == "approve" and c and d["route"]:
            lon, lat = d["route"][-1]
            self._goto(b, to_xy(lat, lon), "close", "SHADOWING")
        return {"ok": True}

    def _inject(self, msg: dict) -> dict:
        kind = msg["kind"]
        a = int(msg["a"])
        if a not in self.boats:
            return {"ok": False, "error": f"no boat {a}"}
        if kind in ("link_off", "link_on"):
            b = msg.get("b")
            b = "shore" if b in (None, "shore", 0) else str(int(b))
            self._apply(kind, {"a": a, "b": b}, exercise=True, injected=True)
        elif kind in ("battery_low", "boat_off"):
            self._apply(kind, {"boat": a}, exercise=True, injected=True)
        else:
            return {"ok": False, "error": f"unknown inject kind {kind!r}"}
        self.event_times.append(self.t)
        return {"ok": True}

    # ---- events
    def _apply(self, kind: str, e: dict, exercise: bool = True, injected: bool = False) -> None:
        src = "operator injection" if injected else "event tape"
        if kind == "battery_low":
            b = self.boats[int(e["boat"])]
            home = dist(b.pos, self.sc.shore) / self.v
            b.endurance_s = min(b.endurance_s, home + self.reserve + 120)
            for task in self._tasks_of(b.id):
                self._release(task)
            self._goto(b, self.sc.shore, "dock", "RETURNING")
            self._event(kind, f"EXERCISE: USV {b.id:02d} battery low, returning to Korsør "
                              f"(automatic safety, cannot be stopped). Its tasks are open. "
                              f"[{src}]", exercise)
            self._alert(f"batt:{b.id}", "caution", f"USV {b.id:02d} low battery, returning")
            self.pending.append((self.t + 12, "reassign", {}))
        elif kind == "boat_off":
            b = self.boats[int(e["boat"])]
            b.radio_on, b.mode, b.path, b.target, b.station = False, "UNAVAILABLE", None, None, None
            b.sog = 0.0
            self._event(kind, f"EXERCISE: USV {b.id:02d} switched off [{src}]", exercise)
            self.pending.append((self.t + 60, "lease_expired", {"boat": b.id}))
        elif kind in ("link_off", "link_on"):
            pair = (str(e["a"]), str(e["b"]))
            other = "shore" if pair[1] == "shore" else f"USV {int(pair[1]):02d}"
            if kind == "link_off":
                self.cut.add(pair)
                self._event(kind, f"EXERCISE: link USV {int(pair[0]):02d} - {other} cut [{src}]",
                            exercise)
            else:
                self.cut.discard(pair)
                self._event(kind, f"Link USV {int(pair[0]):02d} - {other} restored [{src}]",
                            exercise)
        elif kind == "contact_start":
            p = to_xy(float(e["lat"]), float(e["lon"]))
            self.contacts[e["id"]] = Contact(e["id"], p, float(e["sog_kn"]) * KN, 90.0,
                                             bool(e["ais"]), None, str(e["class"]))
        elif kind == "contact_depart":
            c = self.contacts[e["id"]]
            c.sog, c.cog = float(e["sog_kn"]) * KN, float(e["course"])
        elif kind == "reassign":
            self._reassign()
        elif kind == "lease_expired":
            for task in self._tasks_of(int(e["boat"])):
                self._release(task)
            self._event("lease", f"USV {int(e['boat']):02d} lease expired; its tasks are open")
            self._reassign()
        elif kind == "evaluate":
            self._event(kind, "Evaluation point reached (scorecard is computed by eval/)")

    def _reassign(self) -> None:
        """Mock of the auction: the nearest picket takes all open cable segments of a path."""
        open_segs = sorted(k for k, r in self.tasks.items() if k.startswith("seg:")
                           and r["state"] == 0)
        if not open_segs:
            return
        cands = [b for b in self.boats.values() if b.radio_on and b.mode == "SENTINEL"
                 and any(t.startswith("pick:") for t in self._tasks_of(b.id))]
        if not cands:
            self._event("reassign", f"No free boat for {', '.join(open_segs)}; gap stays open")
            return
        for pid, path in sorted(self.paths.items()):
            segs = [s for s in open_segs if self.sc.segments[s][0] in path]
            if not segs:
                continue
            if not cands:
                break
            b = min(cands, key=lambda c: (min(dist(c.pos, p) for p in path[::5]), c.id))
            cands.remove(b)
            for task in self._tasks_of(b.id):
                if task.startswith("pick:"):
                    self._release(task)
                    self._alert(task, "caution", f"Lane picket {task[-1]} uncovered")
                    self._event("release", f"USV {b.id:02d} released {task}: picket "
                                           f"{task[-1]} uncovered")
            for s in segs:
                self._claim(s, b.id)
            near = min(range(len(path)), key=lambda i: dist(path[i], b.pos))
            self._set_path(b, path, dist_along(path, near))
            self._event("claim", f"USV {b.id:02d} took {', '.join(segs)}")

    def _back_to_picket(self, b: Boat) -> None:
        """Return to the first uncovered picket (N before S); else hold near the relay."""
        for st in ("pick:N", "pick:S"):
            if self.tasks.get(st, {}).get("state") != 1:
                self._claim(st, b.id)
                self._clear(st)
                self._event("claim", f"USV {b.id:02d} back on {st}")
                self._goto(b, self.sc.stations[st], "hold", "PATROL")
                return
        self._goto(b, self.sc.stations["relay"], "hold", "PATROL")

    # ---- stepping
    def step(self, dt_ms: int) -> None:
        horizon = 14400 * 1000
        dt_ms = max(0, min(dt_ms, horizon - self.t_ms))
        if dt_ms == 0:
            return
        self.t_ms += dt_ms
        dt = dt_ms / 1000.0
        while self.pending and self.pending[0][0] <= self.t:
            _, kind, e = self.pending.pop(0)
            self._apply(kind, e)
            self.pending.sort(key=lambda x: x[0])
        for b in self.boats.values():
            self._move(b, dt)
        self._move_ais(dt)
        for c in self.contacts.values():
            if not c.id.startswith("AIS-"):
                x, y = c.pos
                r = math.radians(c.cog)
                c.pos = (x + math.sin(r) * c.sog * dt, y + math.cos(r) * c.sog * dt)
        self._sense()
        self._contact_story()
        self._ages(dt)
        self._shore_update()

    def _move(self, b: Boat, dt: float) -> None:
        rate = {"SENTINEL": 0.35, "DORMANT": 0.1, "UNAVAILABLE": 0.0}.get(b.mode, 1.0)  # mock
        b.endurance_s = max(0.0, b.endurance_s - dt * rate)
        if b.target is not None:
            d = dist(b.pos, b.target)
            step = self.v * dt
            b.hdg = bearing(b.pos, b.target) if d > 1 else b.hdg
            if step >= d:
                b.pos, b.target, b.sog = b.target, None, 0.0
                if b.on_arrive == "dock":
                    b.mode = "UNAVAILABLE"
                    self._event("dock", f"USV {b.id:02d} alongside at Korsør")
                    self._clear(f"batt:{b.id}")
                elif b.on_arrive == "hold":
                    self._hold(b, b.pos, "SENTINEL" if b.mode == "PATROL" else b.mode)
                elif b.on_arrive == "close":
                    for c in self.contacts.values():
                        if not c.ais and c.active and dist(c.pos, b.pos) <= 600:
                            c.name_status, c.anchor_status = "IMAGE TAKEN", "IMAGE TAKEN"
                            c.looked = True
                            self._event("look", f"USV {b.id:02d} at 500 m from {c.id}: bow "
                                                f"images taken, for the watch officer to review")
                    self._hold(b, b.pos, "SHADOWING")
            else:
                f = step / d
                b.pos = (b.pos[0] + (b.target[0] - b.pos[0]) * f,
                         b.pos[1] + (b.target[1] - b.pos[1]) * f)
                b.sog = self.v
        elif b.path is not None:
            b.u += self.v * dt
            self._place_on_path(b)
            b.sog = self.v
        elif b.station is not None:
            dx, dy = self._drift(b)
            p = (b.station[0] + dx, b.station[1] + dy)
            if dt > 0:
                b.hdg = bearing(b.pos, p) if dist(b.pos, p) > 0.5 else b.hdg
                b.sog = min(dist(b.pos, p) / dt, 0.3)
            b.pos = p

    def _move_ais(self, dt: float) -> None:
        for cid, (u0, sog, d) in self.ais_tracks.items():
            u = (u0 + d * sog * (self.t)) % self.lane_len
            p, h = point_at(self.lane, u)
            c = self.contacts[cid]
            c.pos, c.cog = p, h if d > 0 else (h + 180) % 360

    def _sense(self) -> None:
        r_det = self.sc.boat["r_detect_m"]
        ais_a = float(self.sc.boat["ais_class_a_m"])
        for c in self.contacts.values():
            if not c.active:
                continue
            seen = []
            for b in sorted(self.boats.values(), key=lambda b: b.id):
                if not b.radio_on:
                    continue
                d = dist(b.pos, c.pos)
                cam = d <= float(r_det.get(c.cls, 2000))
                if cam or (c.ais and d <= ais_a):
                    seen.append(b.id)
            c.seen_by = seen
            if seen:
                c.last_seen, c.seen_pos = self.t, c.pos
                if c.first_seen is None:
                    c.first_seen = self.t
                if not c.detected:
                    c.detected = True
                    if not c.ais:
                        self._on_detect(c, seen[0])
            if c.seen_pos is not None and self.t - c.trail_t >= 60:
                c.trail_t = self.t
                c.trail = (c.trail + [c.seen_pos])[-20:]

    def _camera(self, c: Contact) -> list[int]:
        r = float(self.sc.boat["r_detect_m"].get(c.cls, 2000))
        return [b.id for b in self.boats.values() if b.radio_on and dist(b.pos, c.pos) <= r]

    def _on_detect(self, c: Contact, by: int) -> None:
        self.event_times.append(self.t)
        self._event("detect", f"{c.id} seen by USV {by:02d} camera, no AIS match. Cue for a look.")
        self._alert(f"contact:{c.id}", "warning",
                    f"{c.id}: camera contact, no AIS match. Cue for a look.")
        self._claim(f"contact:{c.id}", by)
        scout = self.boats[by]
        if scout.path is not None:
            scout.saved = (scout.path, scout.u)
        self._hold(scout, scout.pos, "SHADOWING")
        # nearest free picket goes to stand-off
        pickets = [b for b in self.boats.values() if b.mode == "SENTINEL" and b.radio_on
                   and any(t.startswith("pick:") for t in self._tasks_of(b.id))]
        if not pickets:
            return
        k = min(pickets, key=lambda b: (dist(b.pos, c.pos), b.id))
        standoff = float(self.sc.boat["standoff_m"])
        brg = math.radians(bearing(c.pos, k.pos))
        sp = (c.pos[0] + math.sin(brg) * standoff, c.pos[1] + math.cos(brg) * standoff)
        for task in self._tasks_of(k.id):
            if task.startswith("pick:"):
                self._release(task)
                self._alert(task, "caution", f"Lane picket {task[-1]} uncovered")
        self._goto(k, sp, "hold", "SHADOWING")
        self._story = {"scout": by, "keeper": k.id, "contact": c.id, "handed": False}
        self._decision("delegated", f"USV {k.id:02d} keeping {c.id} in view at 1 nm. "
                       "Standing Order 2.", k.id, c.id, ["confirm", "stop"],
                       [k.pos, sp], "keep_in_view")

    def _contact_story(self) -> None:
        st = getattr(self, "_story", None)
        if not st:
            return
        c = self.contacts[st["contact"]]
        k = self.boats[st["keeper"]]
        keep = float(self.sc.boat["keep_in_view_m"])
        if not st["handed"] and k.station is not None and dist(k.pos, c.pos) <= keep + 200:
            st["handed"] = True
            s = self.boats[st["scout"]]
            if s.mode == "SHADOWING" and s.saved is not None:
                self._set_path(s, *s.saved)
                s.saved = None
            self._claim(f"contact:{c.id}", k.id)
            self._event("handover", f"USV {k.id:02d} has {c.id} in view; USV {s.id:02d} "
                                    "back to cable sweep")
            floor = float(self.sc.boat["standoff_floor_m"])
            brg = math.radians(bearing(c.pos, k.pos))
            close = (c.pos[0] + math.sin(brg) * floor, c.pos[1] + math.cos(brg) * floor)
            did = self._decision("held", f"Close to 500 m, photograph both bows ({c.id}, "
                                 f"USV {k.id:02d})", k.id, c.id, ["approve", "decline"],
                                 [k.pos, close], "close_look")
            st["held"] = did
        # unanswered held decisions escalate to alarm
        for d in self.decisions.values():
            if d["status"] == "waiting" and self.t - d["created"] >= UNANSWERED_ALARM_S:
                self._alert(f"decision:{d['id']}", "alarm",
                            f"{d['id']} waiting for watch officer: {d['text']}")
        # contact faster than the boat: cannot hold
        if c.sog > self.v and not st.get("cannot_hold") and k.mode == "SHADOWING":
            st["cannot_hold"] = True
            self.event_times.append(self.t)
            self._event("cannot_hold", f"Cannot hold {c.id}: {c.sog / KN:.1f} kn is above boat "
                                       f"speed. Report queued. Last course {c.cog:03.0f}°.")
            self._alert(f"contact:{c.id}", "warning", f"Cannot hold {c.id}: faster than USV. "
                                                      "Report queued.")
            self._release(f"contact:{c.id}")
            for d in self.decisions.values():
                if d["contact"] == c.id and d["status"] in ("waiting", "active"):
                    d["status"] = "expired"
                    self._clear(f"decision:{d['id']}")
            self._back_to_picket(k)

    def _ages(self, dt: float) -> None:
        for k in self.seg_age:
            self.seg_age[k] += dt
        for b in self.boats.values():
            if b.path is None or b.mode != "PATROL":
                continue
            for k, pts in self.sc.segments.items():
                if any(dist(b.pos, p) <= VISIT_M for p in pts[::3]):
                    self.seg_age[k] = 0.0

    def _boat_view(self, b: Boat, link: tuple[str, int | str | None]) -> dict:
        lat, lon = to_ll(*b.pos)
        home = dist(b.pos, self.sc.shore) / self.v
        tasks = self._tasks_of(b.id)
        via = link[1]
        return {
            "id": b.id, "x": round(b.pos[0]), "y": round(b.pos[1]), "lon": r6(lon), "lat": r6(lat),
            "mode": b.mode,
            "batt": round(1000 * b.endurance_s / float(self.sc.boat["endurance_s"])),
            "endurance_s": round(b.endurance_s),
            "must_return_by": round(self.t + max(0.0, b.endurance_s - self.reserve - home)),
            "link": LINK_WORD[link[0]], "tour": tasks, "roles": tasks,
            "last_heard": int(self.t),
            # console extras (not in contract yet)
            "hdg": round(b.hdg), "sog_kn": round(b.sog / KN, 1), "role_text": self._role(b, tasks),
            "via": 0 if via == "shore" else via, "heard": True,
        }

    def _role(self, b: Boat, tasks: list[str]) -> str:
        if b.mode == "RETURNING":
            return "Return to Korsør"
        if b.mode == "UNAVAILABLE":
            return "Unavailable"
        for t in tasks:
            if t.startswith("contact:"):
                return f"Keeping {t[8:]} in view"
        if "relay" in tasks:
            return "Relay"
        if any(t.startswith("seg:") for t in tasks):
            return "Cable sweep"
        if b.mode == "SHADOWING":
            return "Moving to keep contact in view"
        for t in tasks:
            if t.startswith("pick:"):
                return f"Lane picket {t[-1]}"
        return "Free"

    def _shore_update(self) -> None:
        self._last_links, status = self._links()
        self._status = status
        for b in self.boats.values():
            if status[b.id][0] != "none":
                self.shore_view[b.id] = self._boat_view(b, status[b.id])
            elif b.id in self.shore_view:
                self.shore_view[b.id] = {**self.shore_view[b.id], "link": "none", "via": None}
            else:  # never heard: contract needs an int, "heard" says it is not real data
                self.shore_view[b.id] = {**self._boat_view(b, status[b.id]), "last_heard": 0,
                                         "heard": False}

    # ---- output
    def speed(self) -> int:
        near = int(self.sc.ui["warp_near_events"])
        far = int(self.sc.ui["warp_between_events"])
        return near if any(e - 60 <= self.t <= e + 60 for e in self.event_times) else far

    def scene_msg(self) -> dict:
        return {
            "type": "scene", "schema_version": SCHEMA_VERSION, "source": "mock", "t0_utc": T0_UTC,
            "segments": {k: [lonlat(p) for p in v[::5] + [v[-1]]]
                         for k, v in self.sc.segments.items()},
            "stations": {k: lonlat(p) for k, p in self.sc.stations.items()},
            "shore": lonlat(self.sc.shore),
            "stale_after_s": self.sc.ui["stale_after_s"],
            "horizon_s": 14400,
        }

    def snapshot(self, channel: str = "shore", speed: int | None = None) -> dict:
        if not hasattr(self, "_status"):
            self._shore_update()
        truth = channel == "truth"
        if truth:
            boats = [self._boat_view(b, self._status[b.id]) for b in self.boats.values()]
        else:
            boats = [self.shore_view[i] for i in sorted(self.shore_view)]
        contacts = []
        for c in self.contacts.values():
            if not c.active or not (truth or c.detected):
                continue
            p = c.pos if truth else (c.seen_pos or c.pos)
            lat, lon = to_ll(*p)
            cam = self._camera(c)
            src = "camera" if not c.ais else ("fused" if cam else "ais")
            task = self.tasks.get(f"contact:{c.id}")
            st = getattr(self, "_story", None) or {}
            view = {
                "id": f"contact:{c.id}" if not c.ais else f"ais:{c.id}", "track": c.id,
                "x": round(p[0]), "y": round(p[1]), "lon": r6(lon), "lat": r6(lat),
                "sog": round(c.sog * 1000), "cog": round(c.cog), "ais": c.ais,
                "first_seen": int(c.first_seen or 0), "last_seen": int(c.last_seen or 0),
                "seen_by": c.seen_by,
                "watcher": task["owner"] if task and task["state"] == 1 else 0,
                "state": task["state"] if task else 0,
                "flags": {
                    "dwell": (not c.ais and c.first_seen is not None
                              and self.t - c.first_seen >= 180 and c.sog < 1.0),
                    "name": c.looked, "anchor": c.looked,
                    "cannot_hold": bool(st.get("cannot_hold")) and st.get("contact") == c.id,
                    "capped": False,
                },
                "course": round(c.cog) if st.get("cannot_hold") and st.get("contact") == c.id
                else None,
                # console extras (not in contract yet)
                "name": c.name, "source": src, "sog_kn": round(c.sog / KN, 1),
                "trail": [lonlat(q) for q in c.trail],
                "name_status": c.name_status if not c.ais else "AIS",
                "anchor_status": c.anchor_status,
            }
            if truth:
                view["detected"] = c.detected
            contacts.append(view)
        links = [{"a": 0 if lk["b"] == "shore" else lk["a"],
                  "b": lk["a"] if lk["b"] == "shore" else lk["b"],
                  "state": "up" if lk["ok"] else "cut", "m": lk["m"]} for lk in self._last_links]
        decisions = [{
            "id": d["id"], "task": f"contact:{d['contact']}" if d["contact"] else "",
            "dec": {"close_look": "close", "keep_in_view": "keep"}.get(d["kind"], d["kind"]),
            "text": d["text"], "state": DEC_STATE[d["status"]], "t": int(d["created"]),
            # console extras (not in contract yet)
            "tier": d["tier"], "actions": d["actions"], "status": d["status"],
            "boat": d["boat"], "route": d["route"], "answered": d.get("answered"),
        } for d in self.decisions.values()]
        alerts = [{"id": a["key"], "level": a["level"], "text": a["text"], "t": int(a["t"]),
                   "ack": a["acked"]} for a in self.alerts.values() if a["active"]]
        events = [{"t": int(e["t"]), "kind": e["kind"], "text": e["text"],
                   "exercise": e["exercise"]} for e in self.events[-40:]]
        return {
            "schema_version": SCHEMA_VERSION, "view": channel,
            "t": int(self.t),
            "speed": speed if speed is not None else self.speed(),
            "boats": boats,
            "tasks": dict(sorted(self.tasks.items())),
            "seg_age": {k: round(v) for k, v in sorted(self.seg_age.items())},
            "links": links,
            "contacts": contacts,
            "decisions": decisions,
            "alerts": alerts,
            "events": events,
            # console extras (not in contract yet)
            "type": "snapshot", "source": "mock", "seed": self.seed, "t_exact": round(self.t, 1),
            "t0_utc": T0_UTC,
        }


# ---------------------------------------------------------------- server

class Feed:
    """Owns one MockWorld, steps it at a fixed real rate and broadcasts to clients."""

    def __init__(self, seed: int, hz: float = 10.0):
        self.seed = seed
        self.hz = hz
        self.world = MockWorld(seed)
        self.clients: dict = {}  # connection -> channel
        self.paused = False
        self.speed_override: int | None = None

    def handle_command(self, msg: dict) -> dict:
        log.info("command t=%.1f %s", self.world.t, json.dumps(msg, sort_keys=True))
        cmd = msg.get("cmd")
        if cmd == "reset":
            self.world = MockWorld(int(msg.get("seed", self.seed)))
            return {"ok": True}
        if cmd == "pause":
            self.paused = bool(msg.get("on", not self.paused))
            return {"ok": True}
        if cmd == "speed":
            v = msg.get("value")
            self.speed_override = None if v in (None, "auto") else max(1, int(v))
            return {"ok": True}
        return self.world.command(msg)

    async def handler(self, ws) -> None:
        path = ws.request.path.rstrip("/") or "/shore"
        channel = "truth" if path == "/truth" else "shore"
        if path not in ("/shore", "/truth"):
            await ws.close(code=1008, reason="use /shore or /truth")
            return
        self.clients[ws] = channel
        log.info("client connected on /%s (%d total)", channel, len(self.clients))
        try:
            await ws.send(json.dumps(self.world.scene_msg()))
            await ws.send(json.dumps(self.world.snapshot(channel, self._speed())))
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    if not isinstance(msg, dict):
                        raise TypeError("command must be a JSON object")
                    res = self.handle_command(msg)
                except (ValueError, TypeError) as e:
                    msg, res = {}, {"ok": False, "error": f"bad JSON: {e}"}
                if not res["ok"]:
                    log.warning("rejected %s: %s", msg, res["error"])
                await ws.send(json.dumps({"type": "ack", "cmd": msg.get("cmd"),
                                          "id": msg.get("id"), **res}))
        finally:
            self.clients.pop(ws, None)
            log.info("client left /%s (%d total)", channel, len(self.clients))

    def _speed(self) -> int:
        return 0 if self.paused else (self.speed_override or self.world.speed())

    async def run(self) -> None:
        period = 1.0 / self.hz
        while True:
            speed = self._speed()
            self.world.step(int(speed * period * 1000))
            frames = {ch: json.dumps(self.world.snapshot(ch, speed)) for ch in ("shore", "truth")}
            for ws, ch in list(self.clients.items()):
                try:
                    await ws.send(frames[ch])
                except Exception:  # noqa: BLE001 - a dead client must not stop the feed
                    self.clients.pop(ws, None)
            await asyncio.sleep(period)


async def serve(host: str, port: int, seed: int, hz: float = 10.0, ready=None) -> None:
    from websockets.asyncio.server import serve as ws_serve

    feed = Feed(seed, hz)
    async with ws_serve(feed.handler, host, port) as server:
        bound = server.sockets[0].getsockname()[1]
        log.info("mock feed on ws://%s:%d/shore and /truth, seed %d", host, bound, seed)
        if ready is not None:
            ready.set_result((feed, bound))
        await feed.run()


def main() -> None:
    ap = argparse.ArgumentParser(description="Mock snapshot feed for the console (C).")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--hz", type=float, default=10.0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    try:
        asyncio.run(serve(args.host, args.port, args.seed, args.hz))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
