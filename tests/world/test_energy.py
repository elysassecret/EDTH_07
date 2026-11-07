"""PR #12 review: motors-off hotel load versus conservative cruise load."""

from dataclasses import asdict
from pathlib import Path

import pytest

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import PATROL, SENTINEL
from contract.mission import Action
from world.motion import Boat
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


def test_stationary_sentinel_uses_hotel_load_not_cruise():
    sentinel = Boat.at(3, (0, 0), 10000)
    cruise = Boat.at(1, (0, 0), 10000)
    for _ in range(5):
        sentinel.advance(Action(SENTINEL, None, 2300), 1000, hotel_load_permille=100)
        cruise.advance(Action(PATROL, (10000, 0), 2300), 1000, hotel_load_permille=100)
    assert sentinel.charge_ms == 9500
    assert cruise.charge_ms == 5000
    assert sentinel.point == (0, 0)


def test_correction_costs_cruise_then_returns_to_hotel_load():
    boat = Boat.at(3, (0, 0), 10000)
    boat.advance(Action(SENTINEL, (100, 0), 2300), 1000, hotel_load_permille=100)
    assert boat.charge_ms == 9000
    boat.advance(Action(SENTINEL, None, 2300), 1000, hotel_load_permille=100)
    assert boat.charge_ms == 8900


@pytest.mark.parametrize("target,speed", [((0, 0), 2300), ((100, 0), 0), (None, 2300)])
def test_zero_propulsion_does_not_pay_cruise_load(target, speed):
    boat = Boat.at(3, (0, 0), 10000)
    boat.advance(Action(SENTINEL, target, speed), 1000, hotel_load_permille=100)
    assert boat.charge_ms == 9900


def test_fractional_drain_is_preserved_across_ticks_and_exhaustion_is_bounded():
    small = Boat.at(3, (0, 0), 100)
    large = Boat.at(3, (0, 0), 100)
    action = Action(SENTINEL, None, 0)
    for _ in range(10):
        small.advance(action, 1, hotel_load_permille=333)
    large.advance(action, 10, hotel_load_permille=333)
    assert asdict(small) == asdict(large)
    assert large.charge_ms == 97
    assert large.drain_remainder == 330
    large.advance(action, 1000, hotel_load_permille=333)
    assert large.charge_ms == 0
    assert large.drain_remainder == 0


@pytest.mark.parametrize("rate", [0, -1, 1001])
def test_invalid_hotel_load_is_rejected(rate):
    with pytest.raises(ValueError):
        Boat.at(3, (0, 0), 100).advance(Action(SENTINEL, None, 0), 1000, hotel_load_permille=rate)


def test_shore_console_picture_reflects_delivered_energy_not_truth():
    sim = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    while sim.next_tick_ms <= 30_000:
        sim.step()
    picture = sim.shore.picture(sim.t_ms, speed=240)
    assert picture.view == "shore"
    assert picture.t == 30  # contract view is seconds; world API is milliseconds
    for boat in picture.boats:
        tc, _, heartbeat = sim.shore.boats[boat.id]
        assert boat.batt == heartbeat["batt"]
        assert boat.endurance_s == heartbeat["batt"] * sim.params.endurance_ms // 1_000_000
        assert boat.last_heard == tc // 1000


def test_seed_one_picket_and_relay_stay_out_through_evaluate():
    # Retain the no-current seed-1 result from PR #14 as an explicit control case.
    sim = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode, current_enabled=False)
    assert sim.params.endurance_ms == 25_200_000  # retained seven-hour test input
    while sim.next_tick_ms <= 14_000_000:
        sim.step()
        if sim.t_ms == 7_200_000:
            assert sim.actions[3].mode == SENTINEL
            assert "pick:N" in sim.nodes[3].table.held_by(3)
    for boat in (3, 5):
        assert not sim.nodes[boat].returning
        assert sim.boats[boat].own().batt > 850  # 03 rounds C-07's 1 nm stand-off ring (PLAN 7.9)
    assert sim.actions[5].mode == SENTINEL
    assert "relay" in sim.nodes[5].table.held_by(5)
    # Hotel load does not hide the sweeper's genuine energy limit at seven hours.
    # The energy-rich north picket takes its segments, opening pick:N instead.
    assert sim.nodes[2].returning
    assert sim.actions[3].mode == PATROL
    north_tasks = {task.id for task in sim.mission.tasks if task.id.startswith("seg:H:")}
    # every north segment is swept by a boat at sea; since battery swaps (#116) the fleet shares
    # them (USV 01 is back from Korsør), so they are no longer all USV 03's
    at_sea = {k for b, n in sim.nodes.items() if not n.returning for k in n.table.held_by(b)}
    assert north_tasks <= at_sea
    assert set(sim.nodes[3].table.held_by(3)) & north_tasks
    assert "pick:N" not in sim.nodes[3].table.held_by(3)
    expected = sim.state_hash()
    sim.reset()
    while sim.next_tick_ms <= 14_000_000:
        sim.step()
    assert sim.state_hash() == expected
