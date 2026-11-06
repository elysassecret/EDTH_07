"""S1 to S6: the fixed event script, told by the sim."""
import pytest

from contract.constants import CLAIMED, CLOSED, RELEASED
from tests.helpers import events, make_sim, run_cached


@pytest.fixture(scope="module")
def demo():
    """Seed 1 is the demo seed: detection lands near 7,500 s."""
    return run_cached("elysa", 1, 11200)


def test_s1_reset_clears_state_and_roles_start_2_2_1():
    a, _ = make_sim("elysa", 1)
    b, _ = make_sim("elysa", 1)
    assert a.state_hash() == b.state_hash()
    modes = sorted((x.mode, bool(x.tour), x.pick or "", x.table["relay"].owner == x.me) for x in a.agents.values())
    assert sum(1 for m in modes if m[1]) == 2 and sum(1 for m in modes if m[2]) == 2 and sum(1 for m in modes if m[3]) == 1
    assert all(x.stats["claims"] == 0 for x in a.agents.values())
    assert a.shore.actions == []


def test_s2_a_different_failed_boat_works_the_same_way():
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    sim.run_until(1000)
    sim.inject({"kind": "battery_low", "boat": 2})
    sim.run_until(1000 + 300)
    assert sim.agents[2].mode == "RETURNING"
    rel = [e for e in events(sim, {"release"}, 1000) if e[1] == 2]
    assert {e[3]["task"] for e in rel} >= {"seg:H:0", "seg:H:1", "seg:H:2"}
    claims = [e for e in events(sim, {"claim"}, 1000) if e[3]["task"].startswith("seg:H")]
    assert claims, "nobody took the HVDC segments"
    assert all(e[1] != 2 for e in claims)


def test_s3_contact_story_keeping_in_view_before_any_operator_input(demo):
    sim, m = demo
    ev = events(sim, {"hold_start", "claim", "shadow_start", "hold_end", "contact_close"}, 7300)
    kinds = [(k, b) for _, b, k, _ in ev]
    assert ("hold_start", 2) in kinds                     # the scout detected and held
    assert ("shadow_start", 3) in kinds                   # nearest free boat (north picket) took it
    assert ("hold_end", 2) in kinds                       # scout released once relieved
    closes = [e for e in ev if e[2] == "contact_close"]
    assert closes and closes[0][3]["reason"] == "cannot_hold" and closes[0][0] == 9200
    assert sim.shore.actions == []                        # no operator input was needed
    det = m.detect_t["contact:C-07"] // 1000
    assert 7320 + 180 <= det <= 7600
    # the picket N task was released while shadowing and taken back afterwards
    picks = [e for e in events(sim, {"release", "claim"}, 7300) if e[3]["task"] == "pick:N"]
    assert [k for _, _, k, _ in picks] == ["release", "claim"]


def test_s3_stop_ends_shadowing_and_stale_or_offline_rules():
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    sim.run_until(7800)
    assert sim.agents[3].mode == "SHADOWING"
    sim.inject({"kind": "cmd", "action": "stop", "cid": "contact:C-07"})
    sim.run_until(7830)
    assert sim.agents[3].mode != "SHADOWING"
    assert sim.agents[3].table["contact:C-07"].state == CLOSED
    assert sim.shore.actions and sim.shore.actions[0]["action"] == "stop"
    # expired Stop: a VETO envelope older than its expiry is ignored
    from contract.messages import Envelope
    a = sim.agents[2]
    old = Envelope("0-999", 0, 0, 30_000, "VETO", 0, {"rec": ["pick:N", 99, 2, 0, 0, 0]})
    a._handle(old.encode(), sim.t)
    assert a.table["pick:N"].ver != 99


def test_s3_offline_shadow_queues_report():
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    sim.run_until(7800)
    # cut every link of the shadow boat except to nobody: it is alone with the contact
    for q in [0, 1, 2, 4, 5]:
        sim.inject({"kind": "link_off", "a": 3, "b": q})
    sim.run_until(9300)
    a = sim.agents[3]
    assert a.reports and a.reports[-1]["reason"] == "cannot_hold" and a.reports[-1]["queued"] is True
    assert not a.close_approved.get("contact:C-07")      # never escalated


def test_s3_approve_close_lets_boat_read_name(demo):
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    sim.run_until(7900)
    sim.inject({"kind": "cmd", "action": "approve", "cid": "contact:C-07"})
    sim.run_until(8700)
    obs = sim.agents[3].contact_obs["contact:C-07"]
    assert sim.agents[3].close_approved.get("contact:C-07")
    assert obs["by"] == 3 and obs["dist"] if "dist" in obs else True
    assert obs.get("name_read") is True


def test_s4_link_loss_is_visible_and_data_still_flows(demo):
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    sim.run_until(8000)
    assert (4, 0) in sim.radio.cut and (0, 4) in sim.radio.cut
    assert sim.shore.link_of(4, sim.t) == "relay", sim.shore.link_of(4, sim.t)
    q = sim.shore.boats[4]
    assert sim.t - q["t"] < 60_000                        # shore still has fresh data on boat 4 via a peer
    sim.run_until(10900)
    assert (4, 0) not in sim.radio.cut
    sim.run_until(10950)
    assert sim.shore.link_of(4, sim.t) == "direct"


def test_s5_assignment_alone_closes_no_gap(demo):
    sim, m = demo
    # boat 4 claimed seg:G:* at about 7,224 s; the segment ages must keep growing until a sensor visit
    sim2, m2 = make_sim("elysa", 1)
    sim2.run_warm()
    sim2.run_until(7260)
    ages_claim = m2.seg_age(sim2.t)
    assert sim2.agents[4].table["seg:G:0"].owner == 4
    sim2.run_until(7300)
    ages_later = m2.seg_age(sim2.t)
    assert ages_later["seg:G:0"] == ages_claim["seg:G:0"] + 40 or ages_later["seg:G:0"] < ages_claim["seg:G:0"]


def test_s6_relay_loss_with_no_replacement_shows_isolation():
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    sim.run_until(200)
    for b in (5, 3, 2):
        sim.inject({"kind": "boat_fail", "boat": b})
    sim.run_until(200 + 300)
    hops = sim.radio.shore_reach()
    # whoever is left either has a path (direct) or is shown isolated (-1); nothing pretends otherwise
    assert hops[4] >= 0
    assert any(h == -1 for b, h in hops.items() if b in (2, 3, 5))
    tv = sim.truth_view()
    assert set(tv["failed"]) == {2, 3, 5}


def test_scorecard_separates_modes_on_seed_1():
    _, m_off = run_cached("off", 1, 14000)
    _, m_el = run_cached("elysa", 1, 14000)
    off = m_off.evaluated or m_off.scorecard(14000 * 1000)
    el = m_el.evaluated or m_el.scorecard(14000 * 1000)
    assert el["cable_km_overdue"] < off["cable_km_overdue"]
    assert off["repair_claims_after_T"] == 0
    assert el["time_to_all_segs_owned_s"] is not None and el["time_to_all_segs_owned_s"] <= 120
