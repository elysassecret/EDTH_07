"""Deterministic headless tick loop. Server supplies agent/shore factories.

Snapshots here are evaluator truth, NOT a delivered shore picture. No network I/O.
"""

import hashlib
import json
import tomllib
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, replace
from math import atan2, degrees, isqrt
from pathlib import Path
from typing import Protocol

from ais.replay import DEFAULT_CLIP, DEFAULT_T0, AisPing, AisReplay
from contract.constants import PATROL, UNAVAILABLE
from contract.geo import dist, to_lonlat, to_xy
from contract.mission import Action, Detection, Mission, Own, Params, Point, load_params
from world.current import Current
from world.motion import Boat
from world.phase import STRATEGY, placements
from world.radio import Radio, RadioConfig
from world.routes import load_scene
from world.sensors import Contact, observe, velocity


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
        current_enabled: bool = True,
        vary_start_phase: bool = True,
        ais_enabled: bool = False,
        ais_clip: str | Path | None = None,
        scenario: str | Path = "scenarios/fixed.toml",
        launch: bool = False,
    ):
        self.root = Path(root)
        self.seed = seed
        self.agent_factory = agent_factory
        self.shore_factory = shore_factory
        self.vary_start_phase = vary_start_phase
        self.ais_enabled = ais_enabled or ais_clip is not None
        self.scenario = str(scenario)
        self.scene = load_scene(self.root)
        # launch=True: every boat starts docked at the shore with no task, is switched on one by
        # one, and the swarm decides who goes where (no initial owners). Off = the placed start.
        self.launch = launch
        self.mission = replace(self.scene.mission, initial=()) if launch else self.scene.mission
        self.params = load_params(self.root, scenario=self.scenario)

        def config(name):
            with (self.root / name).open("rb") as handle:
                return tomllib.load(handle)

        self.boat_config = config("config/boat.toml")
        energy = config("config/energy.toml")
        self._base_current = Current.from_config(energy)
        if not current_enabled:
            self._base_current = Current((0, 0), self._base_current.flip_ms)
        self.current = self._base_current
        self.hotel_load_permille = energy["hotel_load_permille"]
        self.power_exponent = int(energy.get("power_exponent", 0))  # 3: cube law below cruise
        self.launch_gap_ms = round(energy.get("launch_gap_s", 60) * 1000)
        self.dock_m = int(energy.get("dock_m", 50))
        self.swap_ms = round(energy.get("swap_s", 600) * 1000)
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
        self.script = config(self.scenario).get("event", [])
        self.ais_t0 = next(
            (event.get("ais_t0", DEFAULT_T0) for event in self.script if event.get("kind") == "reset"),
            DEFAULT_T0,
        )
        clip_path = Path(ais_clip) if ais_clip is not None else self.root / DEFAULT_CLIP
        self._ais_clip = AisReplay(clip_path, self.ais_t0)
        self.ais: AisReplay | None = self._ais_clip if self.ais_enabled else None
        self.reset()

    def reset(self, seed: int | None = None) -> None:
        """Reconstruct physical state and supplied nodes; optionally change seed."""
        if seed is not None:
            self.seed = seed
        self.t = 0
        self.started = False
        self.current = self._base_current
        self.boat_currents: dict[int, Point] = {}
        self.propulsion_permille: dict[int, int] = {}
        self.position_faults: dict[int, dict] = {}
        self.radio = Radio(self.radio_config, self.seed)
        self.swapping: dict[int, int] = {}  # docked boat -> when its battery swap began (ms)
        launches: list[tuple[int, int, dict]] = []
        if self.launch:
            self.start_placements = {}
            order = launch_order(self.mission.boats, self.seed)
            self.boats = {}
            for rank, boat in enumerate(order):
                # side by side along the quay, all inside the dock radius
                point = (self.mission.shore[0] + (rank - len(order) // 2) * 8, self.mission.shore[1])
                self.boats[boat] = Boat.at(boat, point, self.params.endurance_ms)
                self.boats[boat].enabled = rank == 0
                if rank:
                    launches.append((rank * self.launch_gap_ms, -1, {"kind": "launch", "boat": boat, "origin": "world"}))
        else:
            self.start_placements = placements(self.mission, self.seed, enabled=self.vary_start_phase)
            self.boats = {
                boat: Boat.at(boat, placement.point, self.params.endurance_ms)
                for boat, placement in self.start_placements.items()
            }
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
        self.pending += launches
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
        if (
            queued.get("kind")
            in (
                "battery_low",
                "boat_off",
                "boat_restore",
                "adverse_current",
                "current_change",
                "position_error",
                "positioning_error",
                "gps_degrade",
                "position_restore",
                "gps_restore",
                "propulsion_fault",
                "propulsion_restore",
            )
            and "boat" not in queued
            and "a" in queued
        ):
            queued["boat"] = queued["a"]
        self.pending.append((when, self.event_seq, queued))
        self.pending.sort(key=lambda item: (item[0], item[1]))

    def current_for_boat(self, boat: int, t_ms: int | None = None) -> Point:
        when = self.t if t_ms is None else t_ms
        if boat in self.boat_currents:
            return self.boat_currents[boat]
        return self.current.at(when)

    def position_error_m(self, boat: int, t_ms: int | None = None) -> int:
        fault = self.position_faults.get(boat)
        if not fault:
            return 0
        when = self.t if t_ms is None else t_ms
        noise_m = int(fault.get("noise_m", self.boat_config.get("pos_noise_m", 30)))
        if fault.get("dropout"):
            drift_mps = float(
                fault.get("drift_mps", self.boat_config.get("pos_dropout_drift_mps", 0.5))
            )
            elapsed_ms = max(0, when - int(fault.get("since_ms", when)))
            return noise_m + round(elapsed_ms * drift_mps / 1000.0)
        return noise_m

    def observed_own(self, boat: int, t_ms: int | None = None) -> Own:
        when = self.t if t_ms is None else t_ms
        cur = self.current_for_boat(boat, when)
        base = self.boats[boat].own(cur)
        fault = self.position_faults.get(boat)
        if not fault:
            return base
        if fault.get("dropout"):
            fix_x, fix_y = fault["fix_point"]
            return Own(fix_x, fix_y, base.batt, base.cur_x, base.cur_y)
        dx_m = int(fault.get("dx_m", 0))
        dy_m = int(fault.get("dy_m", 0))
        return Own(base.x + dx_m, base.y + dy_m, base.batt, base.cur_x, base.cur_y)

    def _apply(self, event: dict) -> None:
        kind = event["kind"]
        if kind == "reset":
            # Tape origin marker, not a recursive reset of a running loop.
            if self.t != 0:
                raise ValueError("reset marker is valid only at time zero")
        elif kind == "battery_low":
            boat = self.boats[event["boat"]]
            distance = dist(boat.point, self.mission.shore)
            current = self.current_for_boat(event["boat"], self.t)
            along = (
                (
                    current[0] * (self.mission.shore[0] - boat.point[0])
                    + current[1] * (self.mission.shore[1] - boat.point[1])
                )
                // distance
                if distance
                else 0
            )
            ground = max(self.params.speed_mm_s + along, self.params.speed_mm_s // 4)
            home_ms = distance * 1_000_000 // ground
            threshold = (
                (home_ms + self.params.reserve_ms) * self.params.return_safety_permille // 1000
            )
            # Same measured-current rule as the agent; this remains a chosen injection.
            boat.charge_ms = min(boat.charge_ms, threshold)
        elif kind in ("adverse_current", "current_change"):
            speed_mps = float(event.get("current_mps", event.get("speed_mps", 1.5)))
            dir_deg = int(event.get("current_dir_deg", event.get("dir_deg", 325))) % 360
            vec = velocity(round(speed_mps * 1000), dir_deg)
            target_boat = event.get("boat", event.get("a"))
            if target_boat is not None:
                self.boat_currents[int(target_boat)] = vec
            else:
                self.current = Current(vec, self.current.flip_ms)
        elif kind in ("position_error", "positioning_error", "gps_degrade"):
            target_boat = int(event.get("boat", event.get("a")))
            noise_m = int(event.get("noise_m", self.boat_config.get("pos_noise_m", 30)))
            dropout = bool(event.get("dropout", False))
            drift_mps = float(
                event.get("drift_mps", self.boat_config.get("pos_dropout_drift_mps", 0.5))
            )
            # Deterministic offset from seed + boat + time when dx_m/dy_m not explicitly given.
            sign_x = -1 if ((self.seed + target_boat) % 2) else 1
            sign_y = -1 if ((self.seed + target_boat * 3) % 2) else 1
            dx_m = int(event.get("dx_m", sign_x * (noise_m * 4 // 5)))
            dy_m = int(event.get("dy_m", sign_y * (noise_m * 3 // 5)))
            self.position_faults[target_boat] = {
                "noise_m": noise_m,
                "dropout": dropout,
                "drift_mps": drift_mps,
                "dx_m": dx_m,
                "dy_m": dy_m,
                "since_ms": self.t,
                "fix_point": self.boats[target_boat].point,
            }
        elif kind in ("position_restore", "gps_restore"):
            target_boat = int(event.get("boat", event.get("a")))
            self.position_faults.pop(target_boat, None)
        elif kind == "propulsion_fault":
            target_boat = int(event.get("boat", event.get("a")))
            if "effectiveness" in event:
                permille = round(float(event["effectiveness"]) * 1000)
            else:
                permille = int(
                    event.get(
                        "effectiveness_permille",
                        self.boat_config.get("propulsion_fault_permille", 350),
                    )
                )
            if not 0 <= permille <= 1000:
                raise ValueError("propulsion effectiveness must be between 0 and 1000 permille")
            self.propulsion_permille[target_boat] = permille
        elif kind == "propulsion_restore":
            target_boat = int(event.get("boat", event.get("a")))
            self.propulsion_permille.pop(target_boat, None)
        elif kind == "launch":
            # Shore launch: a mechanic or the operator switches this boat on at the dock.
            self.boats[event["boat"]].enabled = True
        elif kind == "battery_swap":
            # #116: fresh battery fitted at the dock; the swap time has passed.
            boat = self.boats[event["boat"]]
            boat.charge_ms, boat.drain_remainder = boat.endurance_ms, 0
        elif kind in ("boat_off", "boat_restore"):
            self.boats[event.get("boat", event.get("a"))].enabled = kind == "boat_restore"
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
                ship_type=event.get("ship_type"),
                length_band_m=event.get("length_band_m"),
            )
            contact.set_velocity(round(event["sog_kn"] * 514.444), event.get("course", 0))
            self.contacts[contact.id] = contact
        elif kind == "contact_depart":
            contact = self.contacts[event["id"]]
            contact.advance(self.t)
            contact.set_velocity(round(event["sog_kn"] * 514.444), event["course"])
        elif kind not in ("evaluate", "launch", "battery_swap"):
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
                        "boat_restore",
                        "link_off",
                        "link_on",
                        "contact_start",
                        "contact_depart",
                        "adverse_current",
                        "current_change",
                        "position_error",
                        "positioning_error",
                        "gps_degrade",
                        "position_restore",
                        "gps_restore",
                        "propulsion_fault",
                        "propulsion_restore",
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

    def ais_pings_for_boat(
        self, boat: int, t_from_ms: int | None = None, t_to_ms: int | None = None
    ) -> tuple[AisPing, ...]:
        """In-range AIS pings for one boat in mission-time window (t_from_ms, t_to_ms]."""
        if self.ais is None or not self.ais.available or boat not in self.boats:
            return ()
        warm_ms = getattr(self, "warm_ms", 0)
        end_ms = (self.t - warm_ms) if t_to_ms is None else t_to_ms
        start_ms = (end_ms - self.tick_ms) if t_from_ms is None else t_from_ms
        if end_ms <= 0 or end_ms <= start_ms:
            return ()
        return self.ais.for_boat(
            self.boats[boat].point,
            max(0, start_ms),
            end_ms,
            self.boat_config["ais_class_a_m"],
            self.boat_config["ais_class_b_m"],
        )

    def _ais_detections_for_point(self, point: Point, dt: int) -> tuple[Detection, ...]:
        if self.ais is None or not self.ais.available or dt <= 0:
            return ()
        end_ms = self.t - getattr(self, "warm_ms", 0)
        start_ms = end_ms - dt
        if end_ms <= 0:
            return ()
        return self.ais.detections_for_boat(
            point,
            max(0, start_ms),
            end_ms,
            self.boat_config["ais_class_a_m"],
            self.boat_config["ais_class_b_m"],
        )

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
            prop = self.propulsion_permille.get(boat, 1000)
            for duration, current in self.current.intervals(self.t - dt, self.t):
                state.advance(
                    self.actions[boat],
                    duration,
                    current=self.boat_currents.get(boat, current),
                    hotel_load_permille=self.hotel_load_permille,
                    cruise_mm_s=self.params.speed_mm_s if self.power_exponent == 3 else None,
                    propulsion_permille=prop,
                )
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
                ais_seen = self._ais_detections_for_point(state.point, dt)
                action, outbox = self.nodes[boat].step(
                    self.t,
                    self.observed_own(boat, self.t),
                    observe(
                        state.point,
                        self.contacts,
                        self.boat_config["r_detect_m"],
                        ais_seen,
                    ),
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
                    hb = deepcopy(payload)
                    err_m = self.position_error_m(boat, created)
                    if err_m > 0:
                        hb["pos_err_m"] = err_m
                    self.shore_reports[boat] = {
                        "id": boat,
                        "reported_ms": created,
                        "last_heard": self.t,
                        "hops": hops,
                        "heartbeat": hb,
                        **({"pos_err_m": err_m} if err_m > 0 else {}),
                    }
        for src, raw in broadcasts:
            self.radio.broadcast(self.t, src, raw, positions)
        self._swap_batteries()
        self._credit_visits()
        self.started = True
        return self.snapshot()

    def _swap_batteries(self) -> None:
        """#116: a boat docked at the shore (agent mode UNAVAILABLE within dock_m) with a used
        battery gets a fresh one after swap_s. Leaving the dock or being switched off stops the
        swap. Logged as world events (not exercise): swap_start, then battery_swap."""
        for boat, state in sorted(self.boats.items()):
            docked = (
                state.enabled
                and self.actions[boat].mode == UNAVAILABLE
                and dist(state.point, self.mission.shore) <= self.dock_m
                and state.charge_ms < state.endurance_ms
            )
            if not docked:
                self.swapping.pop(boat, None)
                continue
            if boat not in self.swapping:
                self.swapping[boat] = self.t
                self._log({"kind": "swap_start", "boat": boat, "swap_s": self.swap_ms // 1000})
            elif self.t - self.swapping[boat] >= self.swap_ms:
                del self.swapping[boat]
                self._apply({"kind": "battery_swap", "boat": boat, "origin": "world"})

    def _log(self, event: dict) -> None:
        self.events.append({**event, "t_ms": self.t, "origin": "world", "exercise": False})

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

    def ais_contacts_view(self, window_ms: int = 180_000) -> list[dict]:
        """Active AIS vessels in the Great Belt box for console /truth and /shore display."""
        if not self._ais_clip.available:
            return []
        t_ms = max(0, self.t - getattr(self, "warm_ms", 0))
        end_ms = t_ms
        start_ms = t_ms - window_ms
        pings = self._ais_clip.between(start_ms, end_ms)
        if not pings:
            return []
        first_seen: dict[str, int] = {}
        latest: dict[str, AisPing] = {}
        trails: dict[str, list[tuple[float, float]]] = {}
        for ping in pings:
            first_seen.setdefault(ping.track, max(0, ping.t_ms))
            prev = latest.get(ping.track)
            if prev is None or ping.t_ms >= prev.t_ms:
                latest[ping.track] = ping
            trails.setdefault(ping.track, []).append(to_lonlat(ping.x, ping.y))
        class_a_m = self.boat_config["ais_class_a_m"]
        class_b_m = self.boat_config["ais_class_b_m"]
        active_boats = {
            boat: state.point
            for boat, state in sorted(self.boats.items())
            if state.enabled and state.charge_ms > 0
        }
        out = []
        for track in sorted(latest):
            if track in self.contacts:
                continue
            ping = latest[track]
            dt = max(0, min(t_ms - ping.t_ms, 60_000))
            vx, vy = velocity(ping.sog, ping.cog)
            x = ping.x + round(vx * dt / 1_000_000)
            y = ping.y + round(vy * dt / 1_000_000)
            rng = class_a_m if ping.ais_class == "Class A" else class_b_m
            seen_by = [
                boat for boat, b_pt in active_boats.items() if dist(b_pt, (x, y)) <= rng
            ]
            shore_ok = dist(self.mission.shore, (x, y)) <= rng
            out.append(
                {
                    "track": track,
                    "x": x,
                    "y": y,
                    "sog": ping.sog,
                    "cog": ping.cog,
                    "ais": True,
                    "standoff_m": self.params.standoff_m,
                    "ship_type": ping.ship_type or None,
                    "length_band_m": ping.length_band_m,
                    "first_seen_s": first_seen[track] // 1000,
                    "last_seen_s": max(0, min(t_ms, max(0, ping.t_ms))) // 1000,
                    "seen_by": seen_by,
                    "shore_in_range": shore_ok,
                    "trail": trails.get(track, [])[-15:],
                }
            )
        return out

    def truth_view(self) -> dict:
        """Detached domain data, not a contract Snapshot or a shore data source."""
        result = self.snapshot()
        for b in result["boats"]:
            bid = b["id"]
            err_m = self.position_error_m(bid, self.t)
            if err_m > 0:
                b["pos_err_m"] = err_m
                obs = self.observed_own(bid, self.t)
                b["obs_x"], b["obs_y"] = obs.x, obs.y
            if bid in self.propulsion_permille:
                b["propulsion_permille"] = self.propulsion_permille[bid]
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
            "initial_phase": {
                "strategy": STRATEGY,
                "enabled": self.vary_start_phase,
                "placements": {
                    str(boat): asdict(placement)
                    for boat, placement in sorted(self.start_placements.items())
                },
            },
            "boats": [
                {
                    "id": boat,
                    **asdict(state.own(self.current.at(self.t))),
                    "enabled": state.enabled,
                    "action": asdict(self.actions[boat]),
                    "mode": self.actions[boat].mode,
                    **self.telemetry[boat],
                    "lon": to_lonlat(*state.point)[0],
                    "lat": to_lonlat(*state.point)[1],
                    "endurance_ms": state.charge_ms,
                    "detect_m": self.boat_config["r_detect_m"]["ship_day"],
                    "keep_in_view_m": self.params.keep_in_view_m,
                    "verify_m": self.params.r_verify_m,
                }
                for boat, state in sorted(self.boats.items())
            ],
            "contacts": [
                contact.snapshot(self.params.standoff_m)
                for _, contact in sorted(self.contacts.items())
            ],
            "events": deepcopy(self.events),
            "launch": self.launch,
            "swapping": {str(b): self.swap_ms - (self.t - since) for b, since in sorted(self.swapping.items())},
            "current": {
                "east_mm_s": self.current.at(self.t)[0],
                "north_mm_s": self.current.at(self.t)[1],
                "flip_ms": self.current.flip_ms,
            },
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
            "swapping": self.swapping,
            "shore_reports": self.shore_reports,
            "sample_visit_ms": self.sample_visit_ms,
            "telemetry": self.telemetry,
            "current_config": asdict(self.current),
        }
        return hashlib.sha256(
            json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def launch_order(boats, seed: int) -> list[int]:
    """Seeded switch-on order for a shore launch: which boat the crew starts first is not a plan
    the swarm can rely on. Deterministic per seed."""
    return sorted(boats, key=lambda b: hashlib.sha256(f"launch:{seed}:{b}".encode()).digest())
