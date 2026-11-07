"""Battery rules 11 and 12 use the water route home (agent/core.py, agent/auction.py). Owner: A."""

from itertools import pairwise
from pathlib import Path

from agent import water
from agent.core import Agent
from contract.geo import dist
from contract.mission import Own, load_params
from world.routes import load_scene

ROOT = Path(__file__).resolve().parents[2]
MISSION = load_scene(ROOT).mission
PARAMS = load_params(ROOT)


def length(pts):
    return sum(dist(a, b) for a, b in pairwise(pts))


def test_the_fast_home_route_is_the_same_as_the_full_planner():
    for a in [(797, 8644), (-2366, 7568), (-5528, 6491), (8221, -7535), (-2278, -7893), (0, 0)]:
        assert length(water.home_path(a, MISSION.shore)) == length(water.path(a, MISSION.shore))


def test_the_trip_home_is_timed_along_the_water_route_not_the_straight_line():
    agent = Agent(1, MISSION, PARAMS)
    north = (797, 8644)  # the way home goes round Zealand
    route = water.home_path(north, MISSION.shore)
    assert length(route) > dist(north, MISSION.shore)
    assert agent.return_ms(north) == agent.route_ms(route)
    assert agent.return_ms(north) > dist(north, MISSION.shore) * 1_000_000 // PARAMS.speed_mm_s


def test_a_fresh_boat_at_korsor_may_take_the_far_end_of_the_hvdc_cable():
    agent = Agent(1, MISSION, PARAMS)
    agent.step(0, Own(*MISSION.shore, 1000, 0, 0), (), [])
    out, back = agent.auction.need_parts("seg:H:0")
    # the margin is on the way home only, as in the return rule; the reserve stays
    assert agent.remaining_ms() - PARAMS.reserve_ms >= out + PARAMS.return_safety_permille * back // 1000
    assert agent.auction.energy_ok("seg:H:0")
    # and a half-empty boat at Korsør may not
    agent.step(1000, Own(*MISSION.shore, 500, 0, 0), (), [])
    assert not agent.auction.energy_ok("seg:H:0")
