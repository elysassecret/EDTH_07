"""Bridge from the real simulator to the console. Owner: C. BUILD_PLAN step 13.

    uv run python -m server               # real sim on ws://localhost:8765/shore and /truth
    uv run python -m server --serve-web   # same, plus the built console on http://localhost:8765/
    uv run python -m server --mock        # the mock feed instead (no sim needed)

Who does what (agreed with B and A):
- world/ (Simeone) owns the ticks: World.step() processes exactly one sim tick.
- agent/ (Javier) builds the shore picture: ShoreNode.picture() is a contract Snapshot made
  only from what the shore station received. That goes out on /shore unchanged.
- This file only schedules ticks (warp), maps truth to a contract Snapshot for /truth,
  routes commands (answers to ShoreNode, failure injections to World) and adds what the
  console itself legitimately knows: the exercise script and the injections it sent.

Never fill /shore from truth: a boat whose link is down must stay old on /shore.
The only changes to the shore picture are console knowledge: exercise events, exercise link
cuts drawn crossed, and no "down" shore line for a boat the shore never heard directly.
"""

from __future__ import annotations

import json
import tomllib
from collections import deque
from pathlib import Path

from agent.core import HOME_M, Agent
from agent.shore import ShoreNode
from contract.constants import SHORE
from contract.geo import to_lonlat, to_xy
from contract.tasks import from_wire, merge
from contract.views import Boat, Contact, ContactFlags, Event, Link, Snapshot, TaskView
from server.alerts import AlertBook
from server.feed import ROOT
from server.runlog import HASH_MS, SNAPSHOT_MS, RunLog, replay_digest
from world.sim import World

INJECT_KINDS = ("battery_low", "boat_off", "link_off", "link_on")
ANSWER_CMDS = ("confirm", "stop", "approve", "decline")
EVENT_WINDOW_MS = 60_000  # slow to warp_near for 60 sim-s either side of each event


def _toml(rel: str) -> dict:
    return tomllib.loads((ROOT / rel).read_text(encoding="utf-8"))


def _event_text(e: dict) -> str:
    """Plain words for a world event. Wording rule: no intent claims."""
    k = e.get("kind")
    a = e.get("a", e.get("boat"))
    usv = f"USV {int(a):02d}" if isinstance(a, int) or str(a).isdigit() else str(a)
    b = e.get("b")
    other = "shore" if b in (None, "shore", 0) else f"USV {int(b):02d}"
    src = "operator injection" if e.get("origin") == "injected" else "exercise script"
    words = {
        "reset": "Reset: new run",
        "battery_low": f"{usv} battery low: returns to Korsør (automatic safety)",
        "boat_off": f"{usv} switched off",
        "link_off": f"Link {usv} → {other} cut",
        "link_on": f"Link {usv} → {other} restored",
        "contact_start": f"Synthetic contact {e.get('id', '')} placed (truth only)",
        "contact_depart": f"Synthetic contact {e.get('id', '')} departs (truth only)",
        "evaluate": "Evaluation point reached (scorecard comes from eval/)",
    }
    text = words.get(k, str(k))
    if e.get("exercise"):
        text = f"EXERCISE: {text} [{src}]"
    return text


class SimSource:
    """World + ShoreNode adapted to the Feed source interface (see server/feed.py)."""

    def __init__(self, seed: int = 1, runs_dir: Path | None = None, demo: dict | None = None):
        self.seed = seed
        # demo preset (server/demo.toml, --demo): warp, extra slow windows, scheduled
        # injections and a fast-forward start. None = the normal console behaviour.
        self.demo = demo or {}
        self.world = World(root=ROOT, seed=seed, agent_factory=Agent, shore_factory=ShoreNode)
        self.ui = json.loads((ROOT / "config" / "ui.json").read_text(encoding="utf-8"))
        run = _toml("config/run.toml")
        self.horizon_ms = int(run["horizon_s"]) * 1000
        self.revisit_target_s = int(run["revisit_target_s"])  # D's number, "confirm Friday"
        tape = _toml("scenarios/fixed.toml").get("event", [])
        t0 = next((e.get("ais_t0") for e in tape if e.get("kind") == "reset"), None)
        self.t0_utc = f"{t0}Z" if t0 and not str(t0).endswith("Z") else (t0 or "")
        self.past_events: deque[int] = deque(maxlen=64)  # ms of events already applied
        # sim time requested so far; can sit between ticks at slow warp (5x at 10 Hz = 0.5 s)
        self.clock_ms = 0
        self.alerts = AlertBook(int(self.ui["stale_after_s"]), self.t0_utc, self.revisit_target_s)
        schema = Snapshot.model_fields["schema_version"].default
        self.log = RunLog.open_new(runs_dir, seed, schema, self.t0_utc) if runs_dir else None
        self._logged_events = 0
        self._placed = 0  # synthetic contacts placed from the console (X-01, X-02, ...)
        self._sample_m = self._sample_lengths()
        self._contact_defaults = next(
            (e for e in tape if e.get("kind") == "contact_start"), {"ais": False, "sog_kn": 0.0,
                                                                     "class": "unknown"})
        self.world.step()  # t = 0 processed, so every view is defined from the first frame
        self._after_tick()
        self._flush()
        if self.demo:
            self._start_demo()

    def _start_demo(self) -> None:
        """Scheduled injections go through command(), so the run log can replay them."""
        for inj in self.demo.get("inject", []):
            msg = {"cmd": "inject", "kind": inj["kind"], "a": inj["a"], "at_s": inj["t"]}
            if "b" in inj:
                msg["b"] = inj["b"]
            res = self.command(msg)
            if not res["ok"]:
                raise ValueError(f"demo injection {inj}: {res['error']}")
        self.step(int(self.demo.get("start_s", 0)) * 1000)

    # ---- Feed source interface
    @property
    def t(self) -> float:
        return self.world.t_ms / 1000.0

    def step(self, dt_ms: int) -> None:
        self.clock_ms = min(self.clock_ms + max(0, dt_ms), self.horizon_ms)
        while self.world.next_tick_ms <= self.clock_ms:
            self.world.step()
            self._after_tick()
        self._flush()

    def _after_tick(self) -> None:
        """Bookkeeping after every sim tick: event times for auto-warp, and the run log."""
        new = self.world.events[self._logged_events:]
        self._logged_events = len(self.world.events)
        for e in new:
            self.past_events.append(int(e["t_ms"]))
        if self.log is None:
            return
        t = self.world.t_ms
        for e in new:
            self.log.write({"type": "event", "t_ms": int(e["t_ms"]), "event": e})
        if t % SNAPSHOT_MS == 0:
            speed = self.speed()
            self.log.write({"type": "snapshot", "t_ms": t, "shore": self.snapshot("shore", speed),
                            "truth": self.snapshot("truth", speed)})
        if t % HASH_MS == 0:
            self.log.write({"type": "hash", "t_ms": t, "hash": replay_digest(self.world)})

    def _flush(self) -> None:
        if self.log is not None:
            self.log.flush()

    def close(self) -> None:
        if self.log is not None:
            self.log.close()

    def near_event(self) -> bool:
        t = self.world.t_ms
        times = [*self.past_events, *self.world.upcoming_event_times()]
        if any(abs(t - e) <= EVENT_WINDOW_MS for e in times if e > 0):
            return True
        return any(a * 1000 <= t <= b * 1000 for a, b in self.demo.get("slow", []))

    def speed(self) -> int:
        near = self.demo.get("warp_near", self.ui["warp_near_events"])
        far = self.demo.get("warp_between", self.ui["warp_between_events"])
        return int(near if self.near_event() else far)

    def scene_msg(self) -> dict:
        m = self.world.mission
        def ll(p):
            return list(to_lonlat(*p))

        return {
            "type": "scene", "schema_version": Snapshot.model_fields["schema_version"].default,
            "source": "sim", "t0_utc": self.t0_utc,
            "segments": {t.id: [ll(p) for p in t.pts] for t in m.tasks if t.id.startswith("seg:")},
            "stations": {t.id: ll(t.pts[0]) for t in m.tasks if not t.id.startswith("seg:")},
            "shore": ll(m.shore),
            "stale_after_s": self.ui["stale_after_s"],
            "horizon_s": self.horizon_ms // 1000,
            "revisit_target_s": self.revisit_target_s,
            "home_m": HOME_M,  # agent's "at the shore station" radius: docked boats sit inside it
        }

    def snapshot(self, channel: str = "shore", speed: int | None = None) -> dict:
        speed = self.speed() if speed is None else speed
        snap = self._truth(speed) if channel == "truth" else self._shore(speed)
        out = snap.model_dump(mode="json")
        # console extras (not contract fields): framing, source label, wall-clock origin
        if channel == "truth":
            out["cable_overdue"] = self.cable_overdue()
        out.update(type="snapshot", source="sim", seed=self.seed, t_exact=self.t,
                   t0_utc=self.t0_utc)
        return out

    def command(self, msg: dict) -> dict:
        res = self._command(msg)
        if self.log is not None:
            self.log.write({"type": "cmd", "t_ms": self.world.t_ms, "msg": msg, "ok": res["ok"]})
            self.log.flush()
        return res

    def _command(self, msg: dict) -> dict:
        cmd = msg.get("cmd")
        try:
            if cmd in ANSWER_CMDS:
                if not isinstance(msg.get("id"), str) or not msg["id"]:
                    return {"ok": False, "error": "decision id missing"}
                ok = self.world.shore.command(self.world.t_ms, {"cmd": cmd, "id": msg["id"]})
                return {"ok": bool(ok)} if ok else {"ok": False, "error": "not a shore command"}
            if cmd == "inject" and msg.get("kind") == "contact_start":
                return self._place_contact(msg)
            if cmd == "inject" and msg.get("kind") == "boat_restore":
                return {"ok": False, "error": "boat_restore needs world support (issue #34)"}
            if cmd == "inject":
                kind, a = msg.get("kind"), int(msg["a"])
                if kind not in INJECT_KINDS:
                    return {"ok": False, "error": f"unknown inject kind {kind!r}"}
                if a not in self.world.mission.boats:
                    return {"ok": False, "error": f"no boat {a}"}
                event = {"kind": kind, "a": a}
                if kind in ("link_off", "link_on"):
                    b = msg.get("b")
                    event["b"] = "shore" if b in (None, "shore", SHORE) else int(b)
                    if event["b"] != "shore" and event["b"] not in self.world.mission.boats:
                        return {"ok": False, "error": f"no boat {event['b']}"}
                    if event["b"] == a:
                        return {"ok": False, "error": "a link needs two different ends"}
                # console extra: "at_s" schedules it for a later tick (demo preset)
                at = msg.get("at_s")
                self.world.inject(event, None if at is None else int(at) * 1000)
                return {"ok": True}
            if cmd == "ack":
                if not isinstance(msg.get("id"), str):
                    return {"ok": False, "error": "alert id missing"}
                ok = self.alerts.ack(msg["id"])
                return {"ok": True} if ok else {"ok": False, "error": f"no alert {msg['id']}"}
        except (KeyError, ValueError, TypeError) as e:
            return {"ok": False, "error": f"bad command: {e}"}
        return {"ok": False, "error": f"unknown cmd {cmd!r}"}

    def _sample_lengths(self) -> list[int]:
        """Metres of cable each sample stands for: up to the next sample on the same task,
        and the last one up to the end of its line (world/routes.py samples every step_m)."""
        from shapely.geometry import LineString

        ends = {t.id: LineString(t.pts).length for t in self.world.mission.tasks
                if t.id.startswith("seg:")}
        samples = self.world.scene.samples
        out = []
        for i, sm in enumerate(samples):
            nxt = samples[i + 1] if i + 1 < len(samples) else None
            stop = nxt.offset_m if nxt is not None and nxt.task == sm.task else ends[sm.task]
            out.append(max(0, round(stop - sm.offset_m)))
        return out

    def cable_overdue(self) -> dict:
        """Evaluator only: true cable km past the revisit target, from each sample's real
        visit time. A console estimate; the scored metric comes from eval/ (D)."""
        t = self.world.t_ms
        target_ms = self.revisit_target_s * 1000
        visits = self.world.truth_view()["sample_visit_ms"]
        never = sum(m for m, v in zip(self._sample_m, visits, strict=True) if v is None)
        over = sum(m for m, v in zip(self._sample_m, visits, strict=True)
                   if v is not None and t - v > target_ms)
        return {"target_s": self.revisit_target_s, "overdue_km": round(over / 1000, 2),
                "never_visited_km": round(never / 1000, 2),
                "total_km": round(sum(self._sample_m) / 1000, 2)}

    def _place_contact(self, msg: dict) -> dict:
        """Feature 13: a synthetic contact where the judge clicked, snapped to the nearest
        cable sample. Speed, class and AIS default to the scripted C-07's (scenarios/fixed.toml).
        Truth only: the shore learns of it only if a boat sees it."""
        lat, lon = float(msg["lat"]), float(msg["lon"])
        x, y = to_xy(lat, lon)
        samples = self.world.scene.samples
        i = min(range(len(samples)),
                key=lambda k: ((samples[k].point[0] - x) ** 2 + (samples[k].point[1] - y) ** 2, k))
        s = samples[i]
        slon, slat = to_lonlat(*s.point)
        self._placed += 1
        d = self._contact_defaults
        cid = f"X-{self._placed:02d}"
        self.world.inject({"kind": "contact_start", "id": cid, "lat": slat, "lon": slon,
                           "ais": bool(msg.get("ais", d.get("ais", False))),
                           "sog_kn": float(d.get("sog_kn", 0.0)), "class": str(d.get("class")),
                           "course": 0})
        return {"ok": True, "placed": cid, "on": s.task, "offset_m": s.offset_m}

    # ---- views
    def _exercise_events(self) -> list[Event]:
        """The console knows its own exercise script and the injections it sent: failures
        only. Synthetic contacts are truth and must never appear on /shore."""
        return [Event(t=int(e["t_ms"]) // 1000, kind=str(e["kind"]), text=_event_text(e),
                      exercise=bool(e.get("exercise")))
                for e in self.world.events if e.get("exercise") and e["kind"] in INJECT_KINDS]

    @staticmethod
    def _pair(e: dict) -> tuple[int, int]:
        b = e.get("b")
        a, b = int(e["a"]), SHORE if b in (None, "shore") else int(b)
        return (min(a, b), max(a, b))

    def _exercise_cuts(self) -> set[tuple[int, int]]:
        """Pairs (low id, high id; shore = 0) the exercise has cut and not yet restored.
        The console sent or scripted these itself, so it may show them on /shore."""
        cuts: set[tuple[int, int]] = set()
        for e in self.world.events:
            if e.get("exercise") and e["kind"] in ("link_off", "link_on"):
                (cuts.add if e["kind"] == "link_off" else cuts.discard)(self._pair(e))
        return cuts

    def _exercise_failures(self) -> list[dict]:
        """Exercise events in order, with their console text (and link pair) for alerts."""
        return [{"kind": e["kind"], "text": _event_text(e),
                 "pair": self._pair(e) if e["kind"] == "link_off" else None}
                for e in self.world.events if e.get("exercise") and e["kind"] in INJECT_KINDS]

    def _shore_links(self, links: list[Link], cuts: set[tuple[int, int]]) -> list[Link]:
        """Two console fixes on the shore's link list (no truth used):
        - a shore 'down' link is drawn only for a boat the shore once heard directly; a boat
          that always talked through a peer never had a shore link to lose;
        - a link the exercise cut is shown as 'cut' (crossed), not just 'down'."""
        ever_direct = self.world.shore.direct  # boat -> time of last direct heartbeat
        out = []
        for lk in links:
            pair = (min(lk.a, lk.b), max(lk.a, lk.b))
            if pair in cuts:
                continue  # re-added below as cut
            if lk.a == SHORE and lk.state == "down" and lk.b not in ever_direct:
                continue
            out.append(lk)
        out.extend(Link(a=a, b=b, state="cut") for a, b in sorted(cuts))
        return out

    def _shore(self, speed: int) -> Snapshot:
        pic = self.world.shore.picture(self.world.t_ms, speed)
        events = sorted([*pic.events, *self._exercise_events()], key=lambda e: e.t)[-60:]
        cuts = self._exercise_cuts()
        self.alerts.update(pic, self._exercise_failures(), cuts)
        return pic.model_copy(update={"t0_utc": self.t0_utc or pic.t0_utc, "events": events,
                                      "links": self._shore_links(pic.links, cuts),
                                      "alerts": self.alerts.alerts()})

    def _merged_tasks(self) -> dict[str, TaskView]:
        recs = {}
        for node in self.world.nodes.values():
            for k, w in node.view()["tasks"].items():
                r = from_wire(w)
                recs[k] = merge(recs[k], r) if k in recs else r
        return {k: TaskView(v=r.ver, owner=r.owner, deputy=r.deputy, state=r.state)
                for k, r in sorted(recs.items())}

    def _truth(self, speed: int) -> Snapshot:
        tv = self.world.truth_view()
        t_ms = tv["t"]
        up = {(lk["a"], lk["b"]) for lk in tv["links"] if lk["up"] and not lk["blocked"]}
        blocked = {(lk["a"], lk["b"]) for lk in tv["links"] if lk["blocked"]}
        # next hop toward shore over links that work both ways (breadth-first from shore)
        via: dict[int, int] = {}
        frontier = [SHORE]
        while frontier:
            nxt = []
            for n in frontier:
                for b in self.world.mission.boats:
                    if b not in via and (b, n) in up and (n, b) in up:
                        via[b] = n
                        nxt.append(b)
            frontier = nxt
        tasks = self._merged_tasks()
        boats = []
        for b in tv["boats"]:
            i = b["id"]
            view = self.world.nodes[i].view()
            boats.append(Boat(
                id=i, x=b["x"], y=b["y"], lon=b["lon"], lat=b["lat"], mode=b["mode"],
                batt=b["batt"], endurance_s=int(b["endurance_ms"]) // 1000,
                link="direct" if via.get(i) == SHORE else "peer" if i in via else "none",
                tour=[leg[0] for leg in view["tour"]],
                roles=sorted(k for k, r in tasks.items() if r.owner == i and r.state == 1),
                last_heard=t_ms // 1000, hdg=b["hdg"], sog=b["sog"], via=via.get(i)))
        links = []
        nodes = (SHORE, *self.world.mission.boats)
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                if (a, b) in blocked or (b, a) in blocked:
                    links.append(Link(a=a, b=b, state="cut"))
                elif (a, b) in up and (b, a) in up:
                    links.append(Link(a=a, b=b, state="up"))
        contacts = [Contact(
            id=f"contact:{c['track']}" if not c["ais"] else f"ais:{c['track']}", track=c["track"],
            x=c["x"], y=c["y"], lon=to_lonlat(c["x"], c["y"])[0], lat=to_lonlat(c["x"], c["y"])[1],
            sog=c["sog"], cog=c["cog"], ais=c["ais"], first_seen=0, last_seen=t_ms // 1000,
            seen_by=[], watcher=0, state=0, flags=ContactFlags(),
            source="ais" if c["ais"] else "camera") for c in tv["contacts"]]
        world_events = [Event(t=int(e["t_ms"]) // 1000, kind=str(e["kind"]), text=_event_text(e),
                              exercise=bool(e.get("exercise"))) for e in tv["events"]][-60:]
        return Snapshot(
            view="truth", t=t_ms // 1000, speed=speed, t0_utc=self.t0_utc or Snapshot.model_fields[
                "t0_utc"].default, boats=boats, tasks=tasks,
            # truth ages are ms or None (never visited); the contract wants int seconds
            seg_age={k: v // 1000 for k, v in sorted(tv["seg_age"].items()) if v is not None},
            links=links, contacts=contacts,
            # decisions and alerts are the shore's: the operator acts on them in either view
            decisions=self.world.shore.picture(t_ms, speed).decisions,
            alerts=self.alerts.alerts(),
            events=world_events)


async def serve(host: str, port: int, seed: int, hz: float = 10.0, ready=None,
                serve_web: bool = False, runs_dir: Path | None = None,
                demo: dict | None = None) -> None:
    from server.feed import serve as feed_serve

    def factory(s: int) -> SimSource:
        return SimSource(s, runs_dir=runs_dir, demo=demo)

    await feed_serve(factory, host, port, seed, hz, ready, serve_web,
                     name="sim bridge (demo preset)" if demo else "sim bridge",
                     start_paused=bool(demo and demo.get("start_paused")))
