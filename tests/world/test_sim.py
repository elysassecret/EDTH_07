"""Loop integration with explicit stand-ins, not the real swarm implementation."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from contract.constants import PATROL
from contract.mission import Action
from world.motion import Boat
from world.radio import Radio, RadioConfig
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


class TestNode:
    __test__ = False

    def __init__(self, me, mission, params):
        self.me, self.mission, self.params = me, mission, params
        self.received = []
        self.seen = []
        self.inputs = []

    def step(self, t, own, seen, inbox):
        self.inputs.append((t, own))
        self.received.extend((t, raw) for raw in inbox)
        self.seen.extend(seen)
        return Action(PATROL, (own.x + 1000, own.y), 2300), [f"{self.me}:{t}".encode()]


class TestShore:
    __test__ = False

    def __init__(self, mission, params):
        self.received = []

    def step(self, t, inbox):
        self.received.extend((t, raw) for raw in inbox)
        return [f"shore:{t}".encode()]


def world():
    return World(ROOT, seed=42, agent_factory=TestNode, shore_factory=TestShore)


def test_motion_retains_fractional_metres_and_does_not_overshoot():
    boat = Boat.at(1, (0, 0), 100_000)
    for _ in range(10):
        boat.advance(Action(PATROL, (100, 0), 2300), 1000)
    assert boat.x_mm == 23000
    assert boat.charge_ms == 90000
    boat.advance(Action(PATROL, (24, 0), 2300), 1000)
    assert boat.point == (24, 0)
    boat.advance(Action("SENTINEL", None, 0), 1000, (500, 0))
    assert boat.x_mm == 24500
    charge = boat.charge_ms
    boat.advance(Action("UNAVAILABLE", None, 0), 1000)
    assert boat.charge_ms == charge


def test_motion_cannot_spend_more_charge_than_remains():
    boat = Boat.at(1, (0, 0), 100)
    boat.advance(Action(PATROL, (100, 0), 2300), 1000)
    assert boat.charge_ms == 0
    assert boat.x_mm == 230


def test_radio_no_loopback_no_same_tick_and_byte_order():
    radio = Radio(RadioConfig(loss_permille=0), 1)
    positions = {0: (0, 0), 1: (1000, 0), 2: (2000, 0)}
    radio.broadcast(0, 1, b"first", positions)
    radio.broadcast(0, 1, b"second", positions)
    assert radio.deliver(0, positions) == {}
    inbox = radio.deliver(1000, positions)
    assert 1 not in inbox
    assert sorted(inbox[0]) == [b"first", b"second"]
    assert sorted(inbox[2]) == [b"first", b"second"]


def test_radio_range_at_send_and_delivery_and_directed_link():
    radio = Radio(RadioConfig(loss_permille=0), 1)
    positions = {1: (0, 0), 2: (8001, 0)}
    radio.broadcast(0, 1, b"outside", positions)
    assert radio.queue == []
    positions[2] = (8000, 0)
    radio.broadcast(0, 1, b"at-boundary", positions)
    positions[2] = (8001, 0)
    assert radio.deliver(1000, positions) == {}
    positions[2] = (1000, 0)
    radio.broadcast(2000, 1, b"inflight", positions)
    radio.link(1, 2, False)
    assert radio.deliver(3000, positions) == {}
    radio.broadcast(4000, 2, b"reverse", positions)
    assert radio.deliver(5000, positions)[1] == [b"reverse"]
    radio.link(1, 2, True)
    radio.broadcast(6000, 1, b"restored", positions)
    assert radio.deliver(7000, positions)[2] == [b"restored"]


def test_radio_bytes_only_and_total_loss():
    radio = Radio(RadioConfig(loss_permille=1000), 1)
    with pytest.raises(TypeError):
        radio.broadcast(0, 1, {}, {1: (0, 0)})
    radio.broadcast(0, 1, b"lost", {1: (0, 0), 2: (0, 0)})
    assert radio.queue == []


def test_loop_moves_all_five_and_does_not_deliver_in_send_tick():
    sim = world()
    initial = sim.step()
    assert all(not node.received for node in sim.nodes.values())
    assert not sim.shore.received
    for _ in range(10):
        final = sim.step()
    for start, end in zip(initial["boats"], final["boats"], strict=True):
        assert end["x"] - start["x"] == 23
        assert end["y"] == start["y"]
    assert any(node.received for node in sim.nodes.values())
    assert all(t >= 1000 for node in sim.nodes.values() for t, _ in node.received)


def test_contact_visibility_low_battery_and_arbitrary_boat_failure():
    sim = world()
    lat, lon = 55.4578, 10.9081
    sim.inject(
        {
            "kind": "contact_start",
            "id": "test",
            "lat": lat,
            "lon": lon,
            "ais": False,
            "class": "dusk",
            "sog_kn": 0,
        }
    )
    sim.inject({"kind": "battery_low", "boat": 3})
    sim.step()
    assert [d.track for d in sim.nodes[3].seen] == ["test"]
    assert not sim.nodes[1].seen
    assert sim.nodes[3].inputs[0][1].batt < 1000
    sim.inject({"kind": "boat_off", "boat": 2})
    sim.step()
    assert len(sim.nodes[2].inputs) == 1
    assert 2 not in sim.positions()


def test_reset_recreates_nodes_queues_and_injections():
    sim = world()
    for _ in range(20):
        sim.step()
    expected = sim.state_hash()
    sim.inject({"kind": "boat_off", "boat": 5})
    sim.step()
    sim.reset()
    for _ in range(20):
        sim.step()
    assert sim.state_hash() == expected
    fresh = world()
    for _ in range(20):
        fresh.step()
    assert fresh.state_hash() == expected


def test_fixed_tape_through_evaluation_is_deterministic():
    # With no agent factory, boats hold position. This tests the world tape, not allocation.
    a, b = World(ROOT, seed=5), World(ROOT, seed=5)
    for _ in range(14001):
        a.step()
        b.step()
    assert a.t == 14_000_000
    assert [e["kind"] for e in a.events] == [
        "reset",
        "battery_low",
        "link_off",
        "contact_start",
        "contact_depart",
        "link_on",
        "evaluate",
    ]
    assert (4, 0) not in a.radio.blocked
    assert a.contacts["C-07"].speed_mm_s == round(6 * 514.444)
    assert a.state_hash() == b.state_hash()


def test_world_hash_is_independent_of_hash_seed():
    code = (
        "from world.sim import World; "
        "from world.__main__ import ExerciseBoat; "
        "w = World(seed=42, agent_factory=ExerciseBoat); "
        "[w.step() for _ in range(100)]; print(w.state_hash())"
    )
    outputs = [
        subprocess.check_output(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env={**os.environ, "PYTHONHASHSEED": seed},
        )
        for seed in ("1", "99")
    ]
    assert outputs[0] == outputs[1]


def test_contact_range_boundary_and_navigation_course():
    from world.sensors import Contact, observe

    contact = Contact("test", 2_000_000, 0, 0, 0, False, "dusk")
    assert len(observe((0, 0), {"test": contact}, {"dusk": 2000})) == 1
    assert observe((-1, 0), {"test": contact}, {"dusk": 2000}) == ()
    contact.set_velocity(1000, 90)
    contact.advance(1000)
    assert contact.point == (2001, 0)


def test_counter_keyed_channel_not_affected_by_unrelated_node():
    positions = {1: (0, 0), 2: (1, 0), 3: (2, 0)}
    a, b = Radio(RadioConfig(), 42), Radio(RadioConfig(), 42)
    a.broadcast(0, 1, b"same", positions)
    b.broadcast(0, 3, b"unrelated", positions)
    b.broadcast(0, 1, b"same", positions)
    assert [(t, src, dst, raw) for t, _, src, dst, raw in a.queue] == [
        (t, src, dst, raw) for t, _, src, dst, raw in sorted(b.queue) if src == 1
    ]


def test_rejects_past_or_off_tick_injections():
    sim = world()
    with pytest.raises(ValueError):
        sim.inject({"kind": "evaluate"}, 1)
    sim.step()
    with pytest.raises(ValueError):
        sim.inject({"kind": "evaluate"}, 0)
