"""World sensor-and-radio bus for separate per-boat and shore runtimes (#105).

Owner: B (world/). Keeps World strictly as physical/sensor/radio test infrastructure
while each boat's Agent and the ShoreNode execute across an explicit serialized
wire boundary (or separate subprocesses). Supports stopping the shore service,
isolating a boat from peers, stopping one boat runtime, and restoring everything
without restarting the surviving boat runtimes.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from contract.constants import SHORE, UNAVAILABLE
from contract.mission import Action, Detection, Own
from world.sensors import observe
from world.sim import AgentFactory, ShoreFactory, World


def encode_sensor_frame(
    t_ms: int, own: Own, seen: tuple[Detection, ...], inbox: list[bytes]
) -> str:
    """Serialize one boat's tick inputs (t_ms, Own, Detections, radio inbox) to JSON."""
    return json.dumps(
        {
            "t_ms": t_ms,
            "own": asdict(own),
            "seen": [asdict(d) for d in seen],
            "inbox": [raw.hex() for raw in inbox],
        },
        separators=(",", ":"),
    )


def decode_sensor_frame(frame_json: str) -> tuple[int, Own, tuple[Detection, ...], list[bytes]]:
    """Deserialize one boat's tick inputs from JSON."""
    d = json.loads(frame_json)
    own = Own(**d["own"])
    seen = tuple(Detection(**item) for item in d["seen"])
    inbox = [bytes.fromhex(h) for h in d["inbox"]]
    return int(d["t_ms"]), own, seen, inbox


def encode_actuation_frame(action: Action, outbox: list[bytes]) -> str:
    """Serialize one boat's Action and radio outbox to JSON."""
    return json.dumps(
        {
            "action": {
                "mode": action.mode,
                "target": list(action.target) if action.target is not None else None,
                "speed_mm_s": action.speed_mm_s,
            },
            "outbox": [raw.hex() for raw in outbox],
        },
        separators=(",", ":"),
    )


def decode_actuation_frame(frame_json: str) -> tuple[Action, list[bytes]]:
    """Deserialize one boat's Action and radio outbox from JSON."""
    d = json.loads(frame_json)
    act = d["action"]
    target = tuple(act["target"]) if act["target"] is not None else None
    return Action(act["mode"], target, int(act["speed_mm_s"])), [
        bytes.fromhex(h) for h in d["outbox"]
    ]


class BoatRuntimeEndpoint:
    """Isolated per-boat runtime endpoint communicating only via serialized frames."""

    def __init__(self, boat_id: int, node):
        self.boat_id = boat_id
        self.node = node
        self.running: bool = True

    def step_wire(self, frame_json: str) -> str:
        t_ms, own, seen, inbox = decode_sensor_frame(frame_json)
        action, outbox = self.node.step(t_ms, own, seen, inbox)
        return encode_actuation_frame(action, outbox)


class ShoreRuntimeEndpoint:
    """Isolated shore service endpoint that can stop and restart without affecting boats."""

    def __init__(self, shore_node):
        self.node = shore_node
        self.running: bool = True

    def step_wire(self, t_ms: int, inbox_hex: list[str]) -> list[str]:
        if not self.running:
            return []
        inbox = [bytes.fromhex(h) for h in inbox_hex]
        outbox = self.node.step(t_ms, inbox)
        return [raw.hex() for raw in outbox]


class DetachedWorldHarness:
    """Runs World purely as sensor/radio/physics infrastructure for independent boat runtimes."""

    def __init__(
        self,
        root: str | Path = ".",
        seed: int = 1,
        agent_factory: AgentFactory | None = None,
        shore_factory: ShoreFactory | None = None,
    ):
        self.world = World(root, seed=seed, agent_factory=None, shore_factory=None)
        self.boat_endpoints: dict[int, BoatRuntimeEndpoint] = {}
        if agent_factory is not None:
            for boat in self.world.mission.boats:
                self.boat_endpoints[boat] = BoatRuntimeEndpoint(
                    boat, agent_factory(boat, self.world.mission, self.world.params)
                )
        self.shore_endpoint: ShoreRuntimeEndpoint | None = (
            ShoreRuntimeEndpoint(shore_factory(self.world.mission, self.world.params))
            if shore_factory is not None
            else None
        )
        self.isolated_boats: set[int] = set()

    def stop_shore(self) -> None:
        """Stop the shore runtime and cut radio links to shore without touching boat runtimes."""
        if self.shore_endpoint is not None:
            self.shore_endpoint.running = False
        for boat in self.world.mission.boats:
            self.world.radio.link(boat, SHORE, False)

    def start_shore(self) -> None:
        """Restore the shore runtime and radio links to non-isolated boats."""
        if self.shore_endpoint is not None:
            self.shore_endpoint.running = True
        for boat in self.world.mission.boats:
            if boat not in self.isolated_boats:
                self.world.radio.link(boat, SHORE, True)

    def isolate_boat(self, boat: int) -> None:
        """Cut all radio links between `boat` and peers/shore while keeping its runtime alive."""
        self.isolated_boats.add(boat)
        self.world.radio.link(boat, SHORE, False)
        for other in self.world.mission.boats:
            if other != boat:
                self.world.radio.link(boat, other, False)

    def stop_boat_runtime(self, boat: int) -> None:
        """Stop one boat's runtime process and physical thruster output."""
        if boat in self.boat_endpoints:
            self.boat_endpoints[boat].running = False
        self.world.boats[boat].enabled = False

    def restore_all(self) -> None:
        """Reconnect isolated boats, restart stopped boat runtimes, and restore shore without resetting agents."""
        self.isolated_boats.clear()
        if self.shore_endpoint is not None:
            self.shore_endpoint.running = True
        for boat, ep in self.boat_endpoints.items():
            ep.running = True
            self.world.boats[boat].enabled = True
            self.world.radio.link(boat, SHORE, True)
            for other in self.world.mission.boats:
                if other != boat:
                    self.world.radio.link(boat, other, True)

    def step(self) -> dict:
        """Advance World physics by one tick and serve sensors/radio over the wire boundary."""
        w = self.world
        if w.started:
            w.t += w.tick_ms
        dt = w.tick_ms if w.started else 0
        while w.pending and w.pending[0][0] <= w.t:
            _, _, event = w.pending.pop(0)
            w._apply(event)
        for boat, state in sorted(w.boats.items()):
            prop = w.propulsion_permille.get(boat, 1000)
            for duration, current in w.current.intervals(w.t - dt, w.t):
                state.advance(
                    w.actions[boat],
                    duration,
                    current=w.boat_currents.get(boat, current),
                    hotel_load_permille=w.hotel_load_permille,
                    propulsion_permille=prop,
                )
        for _, contact in sorted(w.contacts.items()):
            contact.advance(w.t)
        positions = w.positions()
        inbox = w.radio.deliver(w.t, positions)
        broadcasts: list[tuple[int, bytes]] = []

        for boat, state in sorted(w.boats.items()):
            ep = self.boat_endpoints.get(boat)
            if boat not in positions or ep is None or not ep.running:
                w.actions[boat] = Action(UNAVAILABLE, None, 0)
                continue
            ais_seen = w._ais_detections_for_point(state.point, dt)
            seen = observe(state.point, w.contacts, w.boat_config["r_detect_m"], ais_seen)
            frame_in = encode_sensor_frame(
                w.t, w.observed_own(boat, w.t), seen, inbox.get(boat, [])
            )
            frame_out = ep.step_wire(frame_in)
            action, outbox = decode_actuation_frame(frame_out)
            w.actions[boat] = action
            broadcasts.extend((boat, raw) for raw in outbox)

        if self.shore_endpoint is not None and self.shore_endpoint.running:
            shore_out_hex = self.shore_endpoint.step_wire(
                w.t, [raw.hex() for raw in inbox.get(SHORE, [])]
            )
            broadcasts.extend((SHORE, bytes.fromhex(h)) for h in shore_out_hex)

        for src, raw in broadcasts:
            w.radio.broadcast(w.t, src, raw, positions)
        w._credit_visits()
        w.started = True
        return w.snapshot()
