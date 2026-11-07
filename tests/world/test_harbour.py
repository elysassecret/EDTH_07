"""Water-side launch checks include the quay: no land-exclusion circle."""

from dataclasses import replace
from itertools import combinations
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import SENTINEL
from contract.mission import Action
from world.harbour import coastline
from world.sim import World, launch_order

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def land():
    return coastline(ROOT)


def make_world(seed=1, **kwargs):
    return World(ROOT, seed=seed, launch=True, agent_factory=Agent,
                 shore_factory=ShoreNode, **kwargs)


def test_water_berths_are_separate_from_the_station_and_each_other(land):
    w = make_world()
    assert land.contains(Point(w.mission.shore))  # the radio station still belongs on land
    assert w.harbour.station == w.mission.shore
    for boat in w.boats.values():
        assert Point(boat.point).buffer(w.harbour.clearance).disjoint(land)
        assert Point(boat.point).distance(Point(w.mission.shore)) <= w.dock_m
        assert w.telemetry[boat.id]["hdg"] == 270
    for a, b in combinations(w.boats.values(), 2):
        assert Point(a.point).distance(Point(b.point)) > 2 * w.harbour.clearance


def test_invalid_land_berths_are_rejected_instead_of_hidden(land):
    w = make_world()
    bad = replace(w.harbour, berths=(w.mission.shore, *w.harbour.berths[1:]))
    with pytest.raises(ValueError, match="intersects land"):
        bad.validate(land, w.mission.shore, 5, w.dock_m)
    overlap = replace(w.harbour, berths=(w.harbour.berths[1], *w.harbour.berths[1:]))
    with pytest.raises(ValueError, match="overlap"):
        overlap.validate(land, w.mission.shore, 5, w.dock_m)


def test_idle_switched_on_boats_stay_moored_but_still_consume_hotel_energy():
    class IdleBoat:
        def __init__(self, *_):
            pass

        def step(self, *_):
            return Action(SENTINEL, None, 0), []

    w = World(ROOT, launch=True, agent_factory=IdleBoat)
    starts = {b: state.point for b, state in w.boats.items()}
    while w.t < 300_000:
        w.step()
    assert all(state.point == starts[b] for b, state in w.boats.items())
    first = launch_order(w.mission.boats, w.seed)[0]
    assert w.boats[first].charge_ms < w.params.endurance_ms
    assert w.moored == set(w.mission.boats)


@pytest.mark.parametrize("seed", [1, 3, 8])
def test_real_departures_clear_the_coast_including_hull_and_entire_tick_path(seed, land):
    w = make_world(seed)
    previous = {b: state.point for b, state in w.boats.items()}
    while w.t < 1_800_000:
        w.step()
        for boat, state in w.boats.items():
            swept = LineString([previous[boat], state.point]).buffer(w.harbour.clearance)
            assert swept.disjoint(land), (seed, w.t, boat, state.point)
            previous[boat] = state.point
        for a, b in combinations(w.boats.values(), 2):
            assert Point(a.point).distance(Point(b.point)) > 2 * w.harbour.clearance, (
                seed, w.t, a.id, b.id,
            )
    assert not w.moored, "every boat must eventually leave its berth under agent control"


def test_real_return_swap_and_rejoin_clear_the_harbour_coast(land):
    w = make_world()
    while w.t < 120_000:
        w.step()
    boat = launch_order(w.mission.boats, w.seed)[0]
    w.inject({"kind": "battery_low", "boat": boat})
    previous = w.boats[boat].point
    saw_swap = False
    while w.t < 1_800_000:
        w.step()
        point = w.boats[boat].point
        assert LineString([previous, point]).buffer(w.harbour.clearance).disjoint(land)
        previous = point
        saw_swap |= boat in w.swapping
        if saw_swap and boat not in w.swapping and boat not in w.moored:
            break
    else:
        pytest.fail("boat did not return, swap and depart within the test budget")
    assert saw_swap


def test_reset_restores_berths_moorings_heading_and_physical_hash():
    w = make_world()
    initial = w.state_hash()
    while w.t < 300_000:
        w.step()
    w.reset()
    assert w.state_hash() == initial
