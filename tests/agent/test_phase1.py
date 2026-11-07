"""Phase 1 energy management: dwell on the cable, economical speed home, cube-law power below
cruise (agent/core.py, world/motion.py, config/energy.toml). Owner: A, with B."""

import tomllib
from pathlib import Path

from agent import core
from agent.core import Agent
from contract.mission import Action, load_params
from world.motion import Boat, power_rate
from world.routes import load_scene

ROOT = Path(__file__).resolve().parents[2]
MISSION = load_scene(ROOT).mission
PARAMS = load_params(ROOT)


def cfg(name):
    return tomllib.loads((ROOT / name).read_text(encoding="utf-8"))


def test_the_agent_mirrors_of_config_values_match_their_files():
    assert core.REVISIT_TARGET_MS == cfg("config/run.toml")["revisit_target_s"] * 1000
    assert core.ECO_SPEED_PERMILLE == round(cfg("config/agent.toml")["eco_return_speed"] * 1000)
    energy = cfg("config/energy.toml")
    assert core.HOTEL_PERMILLE == energy["hotel_load_permille"]
    assert energy["power_exponent"] == 3
    v = PARAMS.speed_mm_s
    assert core.ECO_DRAIN_PERMILLE == power_rate(v * core.ECO_SPEED_PERMILLE // 1000, v,
                                                 core.HOTEL_PERMILLE)


def test_power_falls_with_the_cube_of_speed_below_cruise_and_is_unchanged_at_cruise():
    v, hotel = 2300, 100
    assert power_rate(v, v, hotel) == 1000
    assert power_rate(0, v, hotel) == hotel
    assert power_rate(v * 8 // 10, v, hotel) < 600  # 0.1 + 0.9 * 0.512

    def drained(speed):
        b = Boat.at(1, (0, 0), 25_200_000)
        b.advance(Action("RETURNING", (10_000_000, 0), speed), 60_000, hotel_load_permille=hotel,
                  cruise_mm_s=v)
        return 25_200_000 - b.charge_ms

    assert drained(v) == 60_000  # one minute at cruise costs one minute of battery, as before
    assert drained(v * 8 // 10) < 36_000


def test_the_way_home_costs_less_battery_at_the_economical_speed():
    agent = Agent(1, MISSION, PARAMS)
    north = (797, 8644)
    route = agent.home_route(north)
    at_cruise = agent.route_ms(route)
    assert agent.return_ms(north) < at_cruise  # battery, not time
    assert agent.return_ms(north) == agent.route_ms(route, agent.eco_mm_s()) * core.ECO_DRAIN_PERMILLE // 1000


def test_a_sweeper_dwells_only_while_its_cables_are_fresh():
    agent = Agent(1, MISSION, PARAMS)
    agent.follow.set_legs([("seg:M:0", False)], MISSION.shore)
    n = len(agent.visits.seen["seg:M:0"])
    agent.t = 10_000_000
    agent.visits.seen["seg:M:0"] = [agent.t - 60_000] * n  # every sample seen a minute ago
    assert agent.dwell_ok()
    agent.visits.seen["seg:M:0"] = [agent.t - 3 * 3_600_000] * n  # three hours ago
    assert not agent.dwell_ok()
    agent.visits.seen["seg:M:0"] = [-1] * n  # never seen: sweep
    assert not agent.dwell_ok()
