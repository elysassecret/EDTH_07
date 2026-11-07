"""Issue #108: adverse-current scenario, positioning uncertainty, and propulsion-fault injections."""

from dataclasses import replace
from pathlib import Path

import pytest

from agent.core import Agent
from agent.shore import ShoreNode
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


def test_adverse_current_scenario_raises_boat_return_cost_mid_task():
    sim = World(
        ROOT,
        seed=1,
        agent_factory=Agent,
        shore_factory=ShoreNode,
        scenario="scenarios/adverse_current.toml",
    )
    assert 3_600_000 in sim.upcoming_event_times()

    # Step up to just before the adverse_current event at t = 3600 s.
    while sim.next_tick_ms < 3_600_000:
        sim.step()
    node1 = sim.nodes[1]
    pos_before = node1.pos
    return_before_ms = node1.return_ms(pos_before)
    cur_before = node1.cur

    # Step through t = 3600 s where adverse_current hits Boat 1.
    sim.step()
    assert sim.t_ms == 3_600_000
    assert sim.events[-1]["kind"] == "adverse_current"
    assert sim.events[-1]["boat"] == 1
    assert node1.cur != cur_before

    # The boat's own energy return estimate rises substantially under the stronger opposing current.
    return_after_ms = node1.return_ms(node1.pos)
    assert return_after_ms > return_before_ms + 2_000_000


def test_positioning_uncertainty_noise_and_dropout_injections():
    sim = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    sim.radio_config = replace(sim.radio_config, loss_permille=0)
    sim.reset()

    sim.step()
    assert sim.position_error_m(3) == 0

    # Inject GPS positioning noise on Boat 3.
    sim.inject({"kind": "position_error", "a": 3, "noise_m": 45})
    sim.step()
    assert sim.position_error_m(3) == 45
    truth_b3 = next(b for b in sim.truth_view()["boats"] if b["id"] == 3)
    assert truth_b3["pos_err_m"] == 45
    assert (truth_b3["obs_x"], truth_b3["obs_y"]) != (truth_b3["x"], truth_b3["y"])
    # Agent 3 sees the noisy position, while physical truth stays separate.
    assert sim.nodes[3].pos == (truth_b3["obs_x"], truth_b3["obs_y"])

    # Run until shore receives Boat 3's heartbeat and verify pos_err_m is attached.
    while 3 not in sim.shore_reports and sim.t_ms < 25_000:
        sim.step()
    assert sim.shore_reports[3]["pos_err_m"] == 45
    assert sim.shore_reports[3]["heartbeat"]["pos_err_m"] == 45

    # Switch to GPS dropout: reported fix freezes and error estimate grows with drift rate.
    sim.inject({"kind": "gps_degrade", "boat": 3, "noise_m": 30, "dropout": True, "drift_mps": 1.0})
    sim.step()
    frozen_pos = sim.nodes[3].pos
    err_t0 = sim.position_error_m(3)
    for _ in range(10):
        sim.step()
    assert sim.nodes[3].pos == frozen_pos
    assert sim.boats[3].point != frozen_pos
    assert sim.position_error_m(3) == err_t0 + 10

    # Restore GPS fix.
    sim.inject({"kind": "position_restore", "boat": 3})
    sim.step()
    assert sim.position_error_m(3) == 0
    assert sim.nodes[3].pos == sim.boats[3].point


def test_propulsion_fault_lowers_speed_while_drawing_cruise_power():
    healthy = World(ROOT, seed=1, agent_factory=Agent, current_enabled=False)
    faulted = World(ROOT, seed=1, agent_factory=Agent, current_enabled=False)

    healthy.step()
    faulted.step()
    faulted.inject({"kind": "propulsion_fault", "a": 1, "effectiveness_permille": 300})

    start_pt = faulted.boats[1].point
    for _ in range(20):
        healthy.step()
        faulted.step()

    healthy_dist = (
        (healthy.boats[1].point[0] - start_pt[0]) ** 2
        + (healthy.boats[1].point[1] - start_pt[1]) ** 2
    ) ** 0.5
    faulted_dist = (
        (faulted.boats[1].point[0] - start_pt[0]) ** 2
        + (faulted.boats[1].point[1] - start_pt[1]) ** 2
    ) ** 0.5

    # Propulsion effectiveness is 30%, so distance covered is ~30% of healthy,
    # while battery drain remains identical (full cruise load).
    assert faulted_dist < healthy_dist * 0.45
    assert faulted.boats[1].charge_ms == healthy.boats[1].charge_ms
    truth_b1 = next(b for b in faulted.truth_view()["boats"] if b["id"] == 1)
    assert truth_b1["propulsion_permille"] == 300

    # Restore propulsion and verify validation on invalid permille.
    faulted.inject({"kind": "propulsion_restore", "boat": 1})
    faulted.step()
    assert 1 not in faulted.propulsion_permille

    with pytest.raises(ValueError):
        faulted.inject({"kind": "propulsion_fault", "boat": 1, "effectiveness_permille": 1500})
        faulted.step()
