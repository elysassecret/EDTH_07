"""World-owned replay checks for seeded starts, cuts and off/restore together.

These tests replay World.inject payloads. Bridge command-log restore replay is now
covered separately by tests/server/test_bridge.py after #70 resolved #63.
"""

from pathlib import Path

from agent.core import Agent
from agent.shore import ShoreNode
from server.runlog import replay_digest
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]
PLAN = (
    (30_000, {"kind": "boat_off", "a": 3}),
    (60_000, {"kind": "boat_restore", "a": 3}),
    (75_000, {"kind": "link_off", "a": 4, "b": "shore"}),
    (95_000, {"kind": "link_on", "a": 4, "b": "shore"}),
    (110_000, {"kind": "battery_low", "a": 1}),
)


def make_world():
    return World(ROOT, seed=4, agent_factory=Agent, shore_factory=ShoreNode)


def exercise(world, plan):
    for t_ms, event in plan:
        world.inject(event, t_ms=t_ms)
    hashes = {}
    while world.next_tick_ms <= 120_000:
        world.step()
        if world.t_ms % 30_000 == 0:
            hashes[world.t_ms] = replay_digest(world)
    return hashes


def test_seeded_world_injection_replay_and_reset_preserve_protocol_and_shore():
    original = make_world()
    expected = exercise(original, PLAN)
    applied = [event for event in original.events if event["origin"] == "injected"]
    assert len(applied) == len(PLAN)
    replay_plan = [
        (
            event["t_ms"],
            {
                key: value
                for key, value in event.items()
                if key not in ("t_ms", "origin", "exercise")
            },
        )
        for event in applied
    ]
    fresh = make_world()
    assert exercise(fresh, replay_plan) == expected
    original.reset(seed=4)
    assert exercise(original, PLAN) == expected
    assert original.boats[3].enabled
    assert original.shore_reports[3]["reported_ms"] > 60_000
    assert (4, 0) not in original.radio.blocked
    assert original.nodes[1].returning
