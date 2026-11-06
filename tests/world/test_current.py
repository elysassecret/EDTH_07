"""Uniform-current physics and actual-agent drift/correction integration."""

from pathlib import Path

import pytest

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import CLAIMED, SENTINEL
from contract.geo import dist
from world.current import Current
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


def test_current_navigation_bearing_and_exact_reversal():
    field = Current.from_config({"current_mps": 0.5, "current_dir_deg": 345, "tide_flip_s": 9000})
    assert field.at(0) == (-129, 483)
    assert field.at(8_999_999) == (-129, 483)
    assert field.at(9_000_000) == (129, -483)
    assert field.at(14_400_000) == (129, -483)


def test_motion_interval_uses_old_current_up_to_flip_not_after_it():
    field = Current((1000, 0), 1500)
    assert field.intervals(0, 1500) == ((1500, (1000, 0)),)
    assert field.intervals(1000, 2000) == ((500, (1000, 0)), (500, (-1000, 0)))
    assert field.intervals(1500, 2000) == ((500, (-1000, 0)),)


@pytest.mark.parametrize(
    "config",
    [
        {"current_mps": -1, "current_dir_deg": 0, "tide_flip_s": 1},
        {"current_mps": 1, "current_dir_deg": 360, "tide_flip_s": 1},
        {"current_mps": 1, "current_dir_deg": 0, "tide_flip_s": -1},
    ],
)
def test_invalid_current_inputs(config):
    with pytest.raises(ValueError):
        Current.from_config(config)


def test_world_drifts_with_motors_off_and_splits_non_aligned_flip():
    sim = World(ROOT)
    sim.current = Current((1000, 0), 1500)
    x = sim.boats[3].x_mm
    sim.step(0)
    assert sim.boats[3].x_mm == x
    sim.step(1000)
    assert sim.boats[3].x_mm == x + 1000
    sim.step(2000)
    assert sim.boats[3].x_mm == x + 1000
    sim.step(3000)
    assert sim.boats[3].x_mm == x
    assert sim.snapshot()["boats"][2]["cur_x"] == -1000


def test_zero_current_control_is_explicit_and_survives_reset():
    sim = World(ROOT, current_enabled=False)
    before = sim.boats[3].point
    for _ in range(10):
        sim.step()
    assert sim.boats[3].point == before
    assert sim.current.at(sim.t_ms) == (0, 0)
    sim.reset(seed=2)
    assert sim.current.at(0) == (0, 0)


def test_low_battery_injection_matches_real_agents_current_aware_safety_rule():
    for current in ((0, 0), (400, -300), (-400, 300)):
        sim = World(ROOT, agent_factory=Agent, shore_factory=ShoreNode)
        sim.current = Current(current, 9_000_000)
        sim.inject({"kind": "battery_low", "a": 3})
        sim.step(0)
        node = sim.nodes[3]
        assert node.cur == current
        assert node.returning
        assert (
            node.remaining_ms()
            <= (node.return_ms(node.pos) + sim.params.reserve_ms)
            * sim.params.return_safety_permille
            // 1000
        )


def test_real_picket_drifts_then_corrects_with_energy_cost_and_stays_near_station():
    sim = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    station = next(task.pts[0] for task in sim.mission.tasks if task.id == "pick:N")
    saw_idle = saw_correction = False
    previous_charge = sim.boats[3].charge_ms
    for _ in range(2001):
        previous_action = sim.actions[3]
        sim.step()
        node = sim.nodes[3]
        assert node.cur == sim.current.at(sim.t_ms)
        assert sim.actions[3].mode == SENTINEL
        assert dist(sim.boats[3].point, station) <= sim.params.sentinel_radius_m + 3
        if sim.t_ms > 0:
            spent = previous_charge - sim.boats[3].charge_ms
            if previous_action.target is None:
                saw_idle = True
                assert spent == sim.hotel_load_permille  # one-second tick
            else:
                saw_correction = True
                assert spent == 1000
        previous_charge = sim.boats[3].charge_ms
    assert saw_idle and saw_correction


def test_full_real_agent_current_run_keeps_tide_and_sensor_inputs_consistent():
    sim = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    local_detectors = set()
    watchers = set()
    contact_flags = set()
    for _ in range(14_001):
        sim.step()
        for boat, node in sim.nodes.items():
            if any(obs["track"] == "C-07" for obs in node.contacts.own_obs):
                local_detectors.add(boat)
            record = node.table.recs.get("contact:C-07")
            if record is not None and record.state == CLAIMED:
                watchers.add(record.owner)
            contact_flags.update(
                flag
                for flag, value in node.contacts.flags.get("contact:C-07", {}).items()
                if value is True
            )
        if sim.t_ms in (8_999_000, 9_000_000, 9_001_000):
            for boat, node in sim.nodes.items():
                if boat in sim.positions():
                    assert node.cur == sim.current.at(sim.t_ms)
    assert sim.current.at(sim.t_ms) == (129, -483)
    assert len(sim.events) == 7
    assert sim.nodes[1].returning
    assert not sim.nodes[5].returning
    assert 2 in local_detectors  # actual local camera observation, not a forwarded track
    assert 3 in watchers
    assert {"dwell", "cannot_hold"} <= contact_flags
    assert all(node.contacts.watching() is None for node in sim.nodes.values())
    # Every rendered shore battery value still comes from its delivered HB, not truth.
    for boat in sim.shore.picture(sim.t_ms).boats:
        assert boat.batt == sim.shore.boats[boat.id][2]["batt"]
