"""Issue #8: world domain API for C's server, without touching server/ or web/."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import CLAIMED, RETURNING, UNAVAILABLE
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


def make_world():
    # Preserve the zero-current API/auction regression independently of physics inputs.
    sim = World(ROOT, seed=42, agent_factory=Agent, shore_factory=ShoreNode, current_enabled=False)
    sim.radio_config = replace(sim.radio_config, loss_permille=0)
    sim.reset()
    return sim


def run_until(sim, target):
    while sim.next_tick_ms <= target:
        sim.step(sim.next_tick_ms)


def test_explicit_tick_times_and_event_lookahead():
    sim = make_world()
    assert sim.t_ms == 0
    assert sim.next_tick_ms == 0
    assert sim.upcoming_event_times() == [0, 7200000, 7320000, 9200000, 10800000, 14000000]
    sim.step(0)
    assert sim.next_tick_ms == 1000
    assert sim.upcoming_event_times()[0] == 7200000
    with pytest.raises(ValueError):
        sim.step(0)
    with pytest.raises(ValueError):
        sim.step(2000)
    assert sim.t_ms == 0


def test_shore_view_empty_until_delivered_and_detached_from_truth():
    sim = make_world()
    sim.step()
    assert sim.shore_view()["boats"] == []
    run_until(sim, 30_000)
    report = next(b for b in sim.shore_view()["boats"] if b["id"] == 3)
    assert report["reported_ms"] < report["last_heard"] <= sim.t_ms
    assert report["hops"] > 0
    # Reads are detached; C cannot mutate the world or the shore's protocol payload.
    report["heartbeat"]["x"] = 999999
    assert sim.shore_reports[3]["heartbeat"]["x"] != 999999
    assert sim.shore.boats[3][2]["x"] != 999999
    for boat in sim.mission.boats:
        sim.inject({"kind": "link_off", "a": boat, "b": "shore"})
    run_until(sim, 45_000)
    stale = sim.shore_view()["boats"]
    run_until(sim, 70_000)
    assert sim.shore_view()["boats"] == stale
    # Moving truth must not refresh an isolated report.
    assert any(b["action"]["target"] is not None for b in sim.truth_view()["boats"])


def test_injections_use_console_a_alias_and_are_logged_as_exercise():
    sim = make_world()
    sim.step()
    sim.inject({"kind": "battery_low", "a": 4})
    sim.inject({"kind": "boat_off", "a": 2})
    sim.step()
    assert sim.nodes[4].returning
    assert not sim.boats[2].enabled
    assert all(
        event["exercise"] and event["origin"] == "injected" and event["t_ms"] == 1000
        for event in sim.events[-2:]
    )
    assert sim.events[-2]["a"] == 4
    assert sim.events[-2]["boat"] == 4


def test_reset_seed_reconstructs_reports_and_lookahead():
    sim = make_world()
    run_until(sim, 30_000)
    sim.reset(seed=7)
    assert sim.seed == 7
    assert sim.shore_view()["boats"] == []
    assert sim.upcoming_event_times()[0] == 0
    assert all(visit is None for visit in sim.sample_visit_ms)
    assert sim.next_tick_ms == 0


def test_truth_visits_are_from_sensors_not_assignment_and_links_are_directed():
    sim = make_world()
    sim.step()
    truth = sim.truth_view()
    assert all("hdg" in b and "sog" in b and "endurance_ms" in b for b in truth["boats"])
    assert any(age is None for age in truth["seg_age"].values())
    assert any(visit == 0 for visit in truth["sample_visit_ms"])
    visits = deepcopy(sim.sample_visit_ms)
    # Ownership alone cannot refresh unseen samples.
    sim.nodes[4].claim("seg:H:0", 0, 0)
    assert sim.sample_visit_ms == visits
    sim.inject({"kind": "link_off", "a": 4, "b": "shore"})
    sim.step()
    links = {(link["a"], link["b"]): link for link in sim.truth_view()["links"]}
    assert links[4, 0]["blocked"] and not links[4, 0]["up"]
    assert not links[0, 4]["blocked"]


def test_real_auction_reassigns_actual_scene_after_scripted_battery_event():
    sim = make_world()
    initial_cables = {task for task, owner in sim.mission.initial if owner == 1}
    run_until(sim, 7_300_000)
    assert sim.nodes[1].returning
    assert sim.actions[1].mode in (RETURNING, UNAVAILABLE)
    # Do not force the scratch-model winner: assert the real seven-segment mission repairs.
    for task in initial_cables:
        records = [node.table.recs[task] for boat, node in sim.nodes.items() if boat != 1]
        assert all(rec.state == CLAIMED and rec.owner != 1 for rec in records)
        assert len({rec.owner for rec in records}) == 1


def test_seed1_truth_and_shore_snapshots_carry_sensor_ranges_and_contact_standoff():
    sim = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    sim.radio_config = replace(sim.radio_config, loss_permille=0)
    sim.reset()
    sim.inject(
        {
            "kind": "contact_start",
            "id": "S-01",
            "lat": 55.3543,
            "lon": 11.0135,
            "ais": True,
            "class": "ship_day",
            "sog_kn": 5.0,
            "course": 180,
            "ship_type": "Cargo",
            "length_band_m": 150,
        }
    )
    sim.step()
    truth = sim.truth_view()
    assert all(
        b["detect_m"] == 5000 and b["keep_in_view_m"] == 2000 and b["verify_m"] == 500
        for b in truth["boats"]
    )
    assert truth["contacts"][0]["standoff_m"] == 1852
    assert truth["contacts"][0]["ship_type"] == "Cargo"
    assert truth["contacts"][0]["length_band_m"] == 150
    run_until(sim, 15_000)
    shore = sim.shore.picture(sim.t_ms)
    assert len(shore.boats) == 5
    assert all(
        b.detect_m == 5000 and b.keep_in_view_m == 2000 and b.verify_m == 500
        for b in shore.boats
    )
    # S-01 has AIS: the boats keep the 1 nm ring only round no-AIS contacts (Agent.avoid, #69),
    # so the shore reports 0 for it rather than a ring nobody keeps
    assert any(c.track == "S-01" and c.standoff_m == 0 for c in shore.contacts)
