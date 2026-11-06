"""Issue #34: restoring radio availability resumes the same boat, not a fresh one."""

from dataclasses import replace
from pathlib import Path

import pytest

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import PATROL, UNAVAILABLE
from contract.mission import Action
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


class MovingNode:
    def __init__(self, me, mission, params):
        self.steps = 0

    def step(self, t, own, seen, inbox):
        self.steps += 1
        return Action(PATROL, (own.x + 1000, own.y), 2300), []


@pytest.mark.parametrize("alias", ["a", "boat"])
def test_restore_preserves_state_and_resumes_same_node(alias):
    sim = World(ROOT, agent_factory=MovingNode)
    for _ in range(5):
        sim.step()
    boat, node = sim.boats[3], sim.nodes[3]
    sim.inject({"kind": "boat_off", alias: 3})
    sim.step()
    state = (boat.x_mm, boat.y_mm, boat.charge_ms, boat.drain_remainder)
    steps = node.steps
    for _ in range(10):
        sim.step()
    assert node.steps == steps
    assert (boat.x_mm, boat.y_mm, boat.charge_ms, boat.drain_remainder) == state
    assert sim.actions[3].mode == UNAVAILABLE
    sim.inject({"kind": "boat_restore", alias: 3})
    sim.step()
    assert sim.boats[3] is boat and sim.nodes[3] is node
    assert boat.enabled
    assert (boat.x_mm, boat.y_mm, boat.charge_ms, boat.drain_remainder) == state
    assert node.steps == steps + 1
    assert sim.events[-1]["kind"] == "boat_restore"
    assert sim.events[-1]["boat"] == 3
    assert sim.events[-1]["origin"] == "injected"
    assert sim.events[-1]["exercise"] is True
    sim.step()
    assert (boat.x_mm, boat.y_mm) != state[:2]
    assert boat.charge_ms < state[2]


def test_real_heartbeats_resume_after_restore_without_reinitializing_agent():
    sim = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    sim.radio_config = replace(sim.radio_config, loss_permille=0)
    sim.reset()
    for _ in range(31):
        sim.step()
    node = sim.nodes[4]
    sim.inject({"kind": "boat_off", "a": 4})
    for _ in range(31):
        sim.step()
    old_report = sim.shore_reports[4]["reported_ms"]
    old_seq = node.net.seq
    sim.inject({"kind": "boat_restore", "a": 4})
    for _ in range(16):
        sim.step()
    assert sim.nodes[4] is node
    assert node.net.seq > old_seq
    assert sim.shore_reports[4]["reported_ms"] > old_report
    assert sim.shore_reports[4]["last_heard"] > old_report


def test_restore_does_not_recharge_exhausted_boat():
    sim = World(ROOT, agent_factory=MovingNode)
    sim.boats[3].charge_ms = 0
    sim.inject({"kind": "boat_off", "boat": 3})
    sim.step()
    sim.inject({"kind": "boat_restore", "boat": 3})
    sim.step()
    assert sim.boats[3].enabled
    assert sim.boats[3].charge_ms == 0
    assert 3 not in sim.positions()
    assert sim.nodes[3].steps == 0


def test_scripted_restore_is_exercise_and_reset_clears_runtime_restores():
    sim = World(ROOT)
    sim.script = [
        {"t": 0, "kind": "boat_off", "boat": 3},
        {"t": 1, "kind": "boat_restore", "boat": 3},
    ]
    sim.reset()
    sim.step()
    sim.step()
    assert sim.events[-1]["origin"] == "scripted"
    assert sim.events[-1]["exercise"] is True
    sim.inject({"kind": "boat_restore", "a": 4})
    sim.reset()
    assert sim.events == []
    assert all(event.get("a") != 4 for _, _, event in sim.pending)
