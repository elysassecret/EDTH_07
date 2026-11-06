"""Deterministic headless tick loop. Server supplies agent/shore factories.

Snapshots here are evaluator truth, NOT a delivered shore picture. No network I/O.
"""

import hashlib
import json
import tomllib
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict
from math import atan2, degrees, isqrt
from pathlib import Path
from typing import Protocol

from contract.constants import PATROL, UNAVAILABLE
from contract.geo import dist, to_lonlat, to_xy
from contract.mission import Action, Detection, Mission, Own, Params, load_params
from world.motion import Boat
from world.radio import Radio, RadioConfig
from world.routes import load_scene
from world.sensors import Contact, observe


class BoatNode(Protocol):
    def step(
        self, t: int, own: Own, seen: tuple[Detection, ...], inbox: list[bytes]
    ) -> tuple[Action, list[bytes]]: ...


class ShoreNode(Protocol):
    def step(self, t: int, inbox: list[bytes]) -> list[bytes]: ...


AgentFactory = Callable[[int, Mission, Params], BoatNode]
ShoreFactory = Callable[[Mission, Params], ShoreNode]


class World:
    def __init__(
        self,
        root: str | Path = ".",
        seed: int = 1,
        agent_factory: AgentFactory | None = None,
        shore_factory: ShoreFactory | None = None,
    ):
        self.root = Path(root)
        self.seed = seed
        self.agent_factory = agent_factory
        self.shore_factory = shore_factory
        self.scene = load_scene(self.root)
        self.mission = self.scene.mission
        self.params = load_params(self.root)

        def config(name):
            with (self.root / name).open("rb") as handle:
                return tomllib.load(handle)

        self.boat_config = config("config/boat.toml")
        self.hotel_load_permille = config("config/energy.toml")["hotel_load_permille"]
        if (
            not isinstance(self.hotel_load_permille, int)
            or not 1 <= self.hotel_load_permille <= 1000
        ):
            raise ValueError("hotel_load_permille must be an integer between 1 and 1000")
        radio = config("config/radio.toml")
        self.radio_config = RadioConfig(
            radio["boat_m"],
            radio["shore_m"],
            round(radio["delay_s"][0] * 1000),
            round(radio["delay_s"][1] * 1000),
            round(radio["loss"] * 1000),
        )
        self.tick_ms = round(config("config/run.toml")["tick_s"] * 1000)
        if self.tick_ms <= 0:
            raise ValueError("tick must be positive")
        self.script = config("scenarios/fixed.toml").get("event", [])
        self.reset()

    def reset(self, seed: int | None = None) -> None:
        """Reconstruct physical state and supplied nodes; optionally change seed."""
        if seed is not None:
            self.seed = seed
        self.t = 0
        self.started = False
        self.radio = Radio(self.radio_config, self.seed)
        tasks = {task.id: task for task in self.mission.tasks}
        self.boats = {}
        for boat in self.mission.boats:
            first = next(task for task, owner in self.mission.initial if owner == boat)
            self.boats[boat] = Boat.at(boat, tasks[first].pts[0], self.params.endurance_ms)
        self.nodes = (
            {
                boat: self.agent_factory(boat, self.mission, self.params)
                for boat in self.mission.boats
            }
            if self.agent_factory
            else {}
        )
        self.shore = self.shore_factory(self.mission, self.params) if self.shore_factory else None
        self.actions = {boat: Action(PATROL, None, 0) for boat in self.mission.boats}
        self.contacts: dict[str, Contact] = {}
        self.events: list[dict] = []
        self.shore_reports: dict[int, dict] = {}
        self.telemetry = {boat: {"hdg": 0, "sog": 0} for boat in self.mission.boats}
        self.sample_visit_ms: list[int | None] = [None] * len(self.scene.samples)
        self.pending = [
            (int(event["t"] * 1000), index, dict(event)) for index, event in enumerate(self.script)
        ]
        self.pending.sort(key=lambda item: (item[0], item[1]))
        self.event_seq = len(self.pending)

    @property
    def t_ms(self) -> int:
        return self.t

    @property
    def next_tick_ms(self) -> int:
        return self.t + self.tick_ms if self.started else 0

    def upcoming_event_times(self) -> list[int]:
        """Unprocessed scripted and injected event times, sorted unique, in sim ms."""
        return sorted({when for when, _, _ in self.pending})

    def inject(self, event: dict, t_ms: int | None = None) -> None:
        """Queue an injection for a tick boundary, leaving the original script intact."""
        when = self.t if not self.started else self.t + self.tick_ms
        if t_ms is not None:
            when = t_ms
        earliest = self.t + self.tick_ms if self.started else 0
        if when < earliest or when % self.tick_ms:
            raise ValueError("injection time must be an unprocessed tick boundary")
        self.event_seq += 1
        queued = {**deepcopy(event), "origin": "injected", "exercise": True}
        if queued.get("kind") in ("battery_low", "boat_off") and "boat" not in queued:
            queued["boat"] = queued["a"]
        self.pending.append((when, self.event_seq, queued))
        self.pending.sort(key=lambda item: (item[0], item[1]))

    def _apply(self, event: dict) -> None:
        kind = event["kind"]
        if kind == "reset":
            # Tape origin marker, not a recursive reset of a running loop.
            if self.t != 0:
                raise ValueError("reset marker is valid only at time zero")
        elif kind == "battery_low":
            boat = self.boats[event["boat"]]
            home_ms = dist(boat.point, self.mission.shore) * 1_000_000 // self.params.speed_mm_s
            threshold = (
                (home_ms + self.params.reserve_ms) * self.params.return_safety_permille // 1000
            )
            # Match the current zero-current safety rule, retaining a feasible home budget.
            boat.charge_ms = min(boat.charge_ms, threshold)
        elif kind == "boat_off":
            self.boats[event.get("boat", event.get("a"))].enabled = False
        elif kind in ("link_off", "link_on"):
            dst = 0 if event["b"] == "shore" else int(event["b"])
            self.radio.link(int(event["a"]), dst, kind == "link_on")
        elif kind == "contact_start":
            point = to_xy(event["lat"], event["lon"])
            contact = Contact(
                event["id"],
                point[0] * 1000,
                point[1] * 1000,
                0,
                0,
                event["ais"],
                event["class"],
                updated_ms=self.t,
            )
            contact.set_velocity(round(event["sog_kn"] * 514.444), event.get("course", 0))
            self.contacts[contact.id] = contact
        elif kind == "contact_depart":
            contact = self.contacts[event["id"]]
            contact.advance(self.t)
            contact.set_velocity(round(event["sog_kn"] * 514.444), event["course"])
        elif kind != "evaluate":
            raise ValueError(f"unsupported event kind: {kind}")
        self.events.append(
            {
                **deepcopy(event),
                "t_ms": self.t,
                "origin": event.get("origin", "scripted"),
                "exercise": event.get(
                    "exercise",
                    kind
                    in (
                        "battery_low",
                        "boat_off",
                        "link_off",
                        "link_on",
                        "contact_start",
                        "contact_depart",
                    ),
                ),
            }
        )

    def positions(self):
        return {
            0: self.mission.shore,
            **{
                boat: state.point
                for boat, state in sorted(self.boats.items())
                if state.enabled and state.charge_ms > 0
            },
        }

    def step(self, t_ms: int | None = None) -> dict:
        """Process exactly one tick; an explicit time must equal next_tick_ms."""
        if t_ms is not None and t_ms != self.next_tick_ms:
            raise ValueError(f"expected next tick {self.next_tick_ms} ms, got {t_ms}")
        if self.started:
            self.t += self.tick_ms
        dt = self.tick_ms if self.started else 0
        while self.pending and self.pending[0][0] <= self.t:
            _, _, event = self.pending.pop(0)
            self._apply(event)
        for boat, state in sorted(self.boats.items()):
            before = (state.x_mm, state.y_mm)
            state.advance(self.actions[boat], dt, hotel_load_permille=self.hotel_load_permille)
            dx, dy = state.x_mm - before[0], state.y_mm - before[1]
            self.telemetry[boat]["sog"] = isqrt(dx * dx + dy * dy) * 1000 // dt if dt else 0
            if dx or dy:
                self.telemetry[boat]["hdg"] = round(degrees(atan2(dx, dy))) % 360
        for _, contact in sorted(self.contacts.items()):
            contact.advance(self.t)
        positions = self.positions()
        inbox = self.radio.deliver(self.t, positions)
        broadcasts = []
        for boat, state in sorted(self.boats.items()):
            if boat not in positions:
                self.actions[boat] = Action(UNAVAILABLE, None, 0)
                continue
            if boat in self.nodes:
                action, outbox = self.nodes[boat].step(
                    self.t,
                    state.own(),
                    observe(state.point, self.contacts, self.boat_config["r_detect_m"]),
                    inbox.get(boat, []),
                )
                self.actions[boat] = action
                broadcasts.extend((boat, raw) for raw in outbox)
        if self.shore is not None:
            broadcasts.extend((0, raw) for raw in self.shore.step(self.t, inbox.get(0, [])))
            # Only reports accepted by the shore protocol may refresh this view.
            for boat, (created, hops, payload) in sorted(getattr(self.shore, "boats", {}).items()):
                previous = self.shore_reports.get(boat)
                if previous is None or created > previous["reported_ms"]:
                    self.shore_reports[boat] = {
                        "id": boat,
                        "reported_ms": created,
                        "last_heard": self.t,
                        "hops": hops,
                        "heartbeat": deepcopy(payload),
                    }
        for src, raw in broadcasts:
            self.radio.broadcast(self.t, src, raw, positions)
        self._credit_visits()
        self.started = True
        return self.snapshot()

    def _credit_visits(self) -> None:
        radius_sq = self.params.r_verify_m**2
        active = [
            state.point
            for _, state in sorted(self.boats.items())
            if state.enabled and state.charge_ms > 0
        ]
        for index, sample in enumerate(self.scene.samples):
            if any(
                (x - sample.point[0]) ** 2 + (y - sample.point[1]) ** 2 <= radius_sq
                for x, y in active
            ):
                self.sample_visit_ms[index] = self.t

    def truth_view(self) -> dict:
        """Detached domain data, not a contract Snapshot or a shore data source."""
        result = self.snapshot()
        ages: dict[str, int | None] = {}
        for sample, visited in zip(self.scene.samples, self.sample_visit_ms, strict=True):
            if visited is None:
                ages[sample.task] = None
            elif sample.task not in ages or ages[sample.task] is not None:
                ages[sample.task] = max(ages.get(sample.task, 0), self.t - visited)
        result["seg_age"] = ages
        result["sample_visit_ms"] = list(self.sample_visit_ms)
        result["links"] = self.link_view()
        return result

    def shore_view(self) -> dict:
        """Delivered reports only; missing boats stay absent, old data stays old.

        last_heard is local receipt time; reported_ms is original heartbeat creation.
        Neither positions nor data age are filled from current world truth.
        """
        return {
            "t": self.t,
            "boats": deepcopy([report for _, report in sorted(self.shore_reports.items())]),
        }

    def link_view(self) -> list[dict]:
        """Truth-only directed radio feasibility, not an inferred live shore graph."""
        positions = self.positions()
        return [
            {
                "a": src,
                "b": dst,
                "up": self.radio.reachable(src, dst, positions),
                "blocked": (src, dst) in self.radio.blocked,
            }
            for src in (0, *self.mission.boats)
            for dst in (0, *self.mission.boats)
            if src != dst
        ]

    def snapshot(self) -> dict:
        """JSON-safe truth only. Server must use ShoreNode.picture for /shore."""
        return {
            "t": self.t,
            "seed": self.seed,
            "boats": [
                {
                    "id": boat,
                    **asdict(state.own()),
                    "enabled": state.enabled,
                    "action": asdict(self.actions[boat]),
                    "mode": self.actions[boat].mode,
                    **self.telemetry[boat],
                    "lon": to_lonlat(*state.point)[0],
                    "lat": to_lonlat(*state.point)[1],
                    "endurance_ms": state.charge_ms,
                }
                for boat, state in sorted(self.boats.items())
            ],
            "contacts": [
                asdict(contact.detection()) for _, contact in sorted(self.contacts.items())
            ],
            "events": deepcopy(self.events),
        }

    def state_hash(self) -> str:
        """Physical/queue digest for reset checks, not a complete agent replay digest."""
        state = {
            "truth": self.snapshot(),
            "boats_mm": [asdict(state) for _, state in sorted(self.boats.items())],
            "radio_seq": self.radio.seq,
            "radio_queue": [
                (t, seq, src, dst, raw.hex()) for t, seq, src, dst, raw in sorted(self.radio.queue)
            ],
            "blocked": sorted(self.radio.blocked),
            "pending": self.pending,
            "contacts_mm": [asdict(contact) for _, contact in sorted(self.contacts.items())],
            "started": self.started,
            "shore_reports": self.shore_reports,
            "sample_visit_ms": self.sample_visit_ms,
            "telemetry": self.telemetry,
        }
        return hashlib.sha256(
            json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
