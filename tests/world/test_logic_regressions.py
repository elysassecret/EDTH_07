"""Cross-layer invariants from world/LOGIC_AUDIT.md.

These were the audit's strict-xfail red baseline. Each assertion now represents
required behaviour after the repairs; no known-failure markers remain.
"""

import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from agent.core import Agent
from agent.shore import ShoreNode
from agent.tour import dist_to_line
from ais.replay import AisReplay
from contract.constants import CLAIMED, CONTACT_DWELL, PATROL, RELEASED, RETURNING, SLOT
from contract.geo import dist, to_lonlat
from contract.mission import Action, Detection, Own, load_params
from contract.tasks import Rec
from eval.report import headline_ok
from eval.warm import build_world
from server.bridge import SimSource
from tests.agent.scene import line_mission
from tests.world.test_ais_replay import _write_clip
from world.routes import load_scene

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def params():
    return load_params(ROOT)


def test_coast_detour_preserves_the_contact_standoff(params):
    mission = load_scene(ROOT).mission
    agent = Agent(1, mission, params)
    agent.t, agent.pos = 1_000_000, (-1971, -8069)
    contact = (-4578, -8501)
    goal = next(task.pts[0] for task in mission.tasks if task.id == "seg:G:0")
    assert dist(agent.pos, contact) > params.standoff_m
    agent.contacts.tracks["AUDIT"] = {
        "x": contact[0], "y": contact[1], "ais": False, "to": agent.t,
    }
    action = agent.avoid(Action(PATROL, goal, params.speed_mm_s))
    # A safe hold is permissible; a new path inside the unapproved ring is not.
    assert action.target is None or dist_to_line(contact, (agent.pos, action.target)) >= params.standoff_m


def bidding_agent(params):
    agent = Agent(2, line_mission(), params)
    agent.table.apply(Rec("seg:A:0", 2, RELEASED, 0, 1))
    agent.step(0, Own(3000, 1000, 1000), (), [])
    assert "seg:A:0" in agent.auction.bids[0], "the real slot logic must make the initial bid"
    return agent


def test_returning_boat_cannot_win_its_pre_return_bid(params):
    agent = bidding_agent(params)
    action, _ = agent.step(SLOT, Own(3000, 1000, 1), (), [])
    assert agent.returning and action.mode == RETURNING
    assert agent.table.held_by(agent.me) == []


def test_repair_off_cutoff_invalidates_outstanding_bids(params):
    agent = bidding_agent(replace(params, policy="off", repair_off_after_ms=SLOT))
    agent.step(SLOT, Own(3000, 1000, 1000), (), [])
    assert not agent.may_bid(SLOT)
    assert not agent.holds_task("seg:A:0")


def test_isolated_boat_range_is_not_an_ais_report_delivered_to_shore(tmp_path):
    source = SimSource(launch=False)
    try:
        boat = 3
        lon, lat = to_lonlat(*source.world.boats[boat].point)
        clip = _write_clip(tmp_path / "synthetic-ais.csv", [{
            "ts_file": "2026-11-03T10:15:01", "vessel_hash": "AUDIT-SYNTHETIC",
            "lat": lat, "lon": lon, "sog_kn": 0, "cog_deg": 0,
            "ship_type": "Fishing", "ais_class": "Class B",
        }])
        source.world._ais_clip = AisReplay(clip, "2026-11-03T10:15:00")
        for peer in (0, 1, 2, 4, 5):
            source.world.radio.blocked.add((boat, peer))
            source.world.radio.blocked.add((peer, boat))
        for peer, state in source.world.boats.items():
            if peer != boat:
                state.enabled = False
        source.step(1000)
        track = next(c for c in source.world.ais_contacts_view()
                     if c["track"] == "AUDIT-SYNTHETIC")
        assert not track["shore_in_range"] and track["seen_by"] == [boat]
        assert source.world.ais is None
        assert "AUDIT-SYNTHETIC" not in source.world.shore.contacts.tracks
        assert all(c["track"] != "AUDIT-SYNTHETIC"
                   for c in source.snapshot("shore")["contacts"])
    finally:
        source.close()


def test_warmed_world_keeps_the_mission_relative_tide_time():
    world = build_world(ROOT, "elysa", 1)
    energy = tomllib.loads((ROOT / "config/energy.toml").read_text())
    configured_flip_ms = round(energy["tide_flip_s"] * 1000)
    assert world.current.flip_ms == configured_flip_ms + world.warm_ms


def test_first_slow_observation_does_not_claim_three_minutes_of_slow_dwell(params):
    agent = Agent(1, line_mission(), params)
    agent.step(0, Own(0, 0, 1000), (Detection("AUDIT", 1000, 0, 2000, 0, False),), [])
    agent.step(CONTACT_DWELL, Own(0, 0, 1000),
               (Detection("AUDIT", 1000, 0, 100, 0, False),), [])
    assert "contact:AUDIT" not in agent.table.recs
    assert not agent.contacts.flags.get("contact:AUDIT", {}).get("dwell")


@pytest.mark.parametrize("modes", [("elysa",), ("static", "off", "elysa")])
def test_pre_failure_batches_are_not_accepted_headlines(modes):
    # Explicit fixture data: varied outcomes must not compensate for a missing
    # failure/scoring checkpoint. This is not a simulated performance result.
    cards = [{
        "mode": mode, "seed": seed, "warm_hash": f"same-within-seed-{seed}",
        "params": {"policy": mode}, "seg_age_s": {"seg:X": seed},
        "ages_hash_T1": None, "state_hash_T1": None,
        "repair_claims_after_T": 0, "t_s": 60, "gap": {"ok": True},
    } for mode in modes for seed in range(1, 6)]
    assert not headline_ok(cards)


def test_released_stale_contact_has_no_pending_operator_proposals(params):
    shore = ShoreNode(line_mission(), params)
    shore.contacts.on_obs({
        "track": "AUDIT", "x": 1000, "y": 0, "sog": 100, "cog": 0,
        "ais": False, "to": 0, "by": 1, "dist": 1000,
    })
    shore.table.apply(Rec("contact:AUDIT", 1, CLAIMED, 1, 1))
    shore.offer(0)
    assert len(shore.decisions) == 2
    shore.table.apply(Rec("contact:AUDIT", 2, RELEASED, 0, 1))
    shore.offer(120_000)
    assert all(d["state"] != "pending" for d in shore.decisions.values())


def test_cancelled_battery_swap_disappears_from_the_shared_feed():
    source = SimSource(launch=True)
    try:
        boat = next(b for b, state in source.world.boats.items() if state.enabled)
        assert source.command({"cmd": "inject", "kind": "battery_low", "a": boat})["ok"]
        source.step(1000)
        assert boat in source.world.swapping
        assert str(boat) in source.swaps()
        assert source.command({"cmd": "inject", "kind": "boat_off", "a": boat})["ok"]
        source.step(1000)
        assert boat not in source.world.swapping
        assert str(boat) not in source.snapshot("truth")["swaps"]
        assert str(boat) not in source.snapshot("shore")["swaps"]
    finally:
        source.close()
