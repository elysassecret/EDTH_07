"""Issue #28: reproducible spatial phases, no fabricated history or policy advantage."""

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from shapely.geometry import LineString, Point

from agent.core import Agent
from agent.shore import ShoreNode
from world.phase import placements
from world.routes import load_mission
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


def test_seeds_vary_sweepers_but_not_stationary_roles():
    mission = load_mission(ROOT)
    phases = [placements(mission, seed) for seed in range(1, 6)]
    for boat in (1, 2):
        assert len({phase[boat].point for phase in phases}) == 5
        for phase in phases:
            place = phase[boat]
            assert 0 <= place.offset_m < place.route_length_m
            cable = next(task for task in mission.tasks if task.id == place.task)
            assert dict(mission.initial)[place.task] == boat
            assert LineString(cable.pts).distance(Point(place.point)) < 2
    for boat in (3, 4, 5):
        assert all(phase[boat] == phases[0][boat] for phase in phases)
        assert phases[0][boat].offset_m == phases[0][boat].route_length_m == 0


def test_seed_one_and_explicit_control_retain_original_demo_positions():
    mission = load_mission(ROOT)
    original = placements(mission, 1)
    assert placements(mission, 99, enabled=False) == original
    for boat, placement in original.items():
        first_id = next(task for task, owner in mission.initial if owner == boat)
        assert placement.point == next(task.pts[0] for task in mission.tasks if task.id == first_id)


def make_world(seed, policy="elysa", speed=2300):
    sim = World(ROOT, seed=seed, agent_factory=Agent, shore_factory=ShoreNode)
    sim.params = replace(sim.params, policy=policy, speed_mm_s=speed)
    sim.reset()
    return sim


def test_initial_placement_independent_of_policy_and_speed_and_has_no_fake_visits():
    baseline = make_world(3)
    for policy in ("elysa", "off", "static"):
        for speed in (2300, 3000):
            sim = make_world(3, policy, speed)
            assert sim.start_placements == baseline.start_placements
            assert sim.positions() == baseline.positions()
            assert all(boat.charge_ms == sim.params.endurance_ms for boat in sim.boats.values())
            assert all(visit is None for visit in sim.sample_visit_ms)
            assert sim.shore_reports == {}
            assert sim.snapshot()["initial_phase"] == baseline.snapshot()["initial_phase"]


def test_reset_seed_repositions_deterministically_without_reusing_old_agents():
    sim = make_world(2)
    for _ in range(31):
        sim.step()
    expected = sim.state_hash()
    old_agent = sim.nodes[1]
    sim.reset(seed=4)
    assert sim.start_placements != placements(sim.mission, 2)
    sim.reset(seed=2)
    assert sim.nodes[1] is not old_agent
    for _ in range(31):
        sim.step()
    assert sim.state_hash() == expected


def test_short_off_and_elysa_runs_have_identical_physical_history():
    on, off = make_world(4, "elysa"), make_world(4, "off")
    for _ in range(101):
        on.step()
        off.step()
        assert on.state_hash() == off.state_hash()


def test_phase_is_independent_of_python_hash_seed():
    code = (
        "import json; from world.sim import World; "
        "print(json.dumps(World(seed=5).snapshot(), sort_keys=True))"
    )
    values = [
        subprocess.check_output(
            [sys.executable, "-c", code], cwd=ROOT, env={**os.environ, "PYTHONHASHSEED": seed}
        )
        for seed in ("0", "4242")
    ]
    assert values[0] == values[1]


def test_explicit_phase_control_survives_reset():
    sim = World(ROOT, seed=5, vary_start_phase=False)
    before = sim.positions()
    sim.reset(seed=2)
    assert sim.positions() == before
    assert not sim.snapshot()["initial_phase"]["enabled"]
