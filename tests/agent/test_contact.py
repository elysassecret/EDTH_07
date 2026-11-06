"""Phase 5 boat side: the scripted contact story on the scene-like mission (PLAN section 2)."""
from dataclasses import replace

from contract.constants import CLAIMED, RELEASED, SHADOWING
from contract.mission import load_params
from tests.agent.harness import Sim
from tests.agent.scene import C07, START, scene_mission

PARAMS = load_params()
TASK = "contact:C-07"


def story():
    s = Sim(scene_mission(), PARAMS, START)
    s.run_until(600_000)
    s.set_batt(1, 200)  # 01 heads home, 04 takes its cables, pick:S opens
    s.run_until(720_000)
    s.add_track("C-07", C07, sog=206, cog=0)  # 0.4 kn, no AIS, on the HVDC line
    return s


def test_scout_holds_free_picket_watches_scout_resumes_cannot_hold():
    s = story()
    seen = {}
    while s.t <= 3_000_000:
        s.tick()
        if s.t == 2_600_000:
            s.set_track("C-07", 3087, 255)  # departs at 6 kn, faster than the boat
        r = s.agents[3].table.recs.get(TASK)
        if s.agents[2].contacts.holding and "hold" not in seen:
            seen["hold"] = s.t
        if r and r.state == CLAIMED and "claim" not in seen:
            seen["claim"] = s.t
            assert r.owner == 3 and s.agents[3].table.held_by(3) == [TASK]  # pick:N released
        if "claim" in seen and "resume" not in seen and s.agents[2].contacts.holding is None:
            seen["resume"] = s.t
            assert s.agents[3].mode == SHADOWING
    assert seen["hold"] < seen["claim"] < seen["resume"]  # watching started with no operator
    f = s.agents[2].contacts.flags[TASK]
    assert f["dwell"] and f["cannot_hold"] and f["course"] == 255
    assert s.agents[3].table.recs[TASK].state == RELEASED
    assert s.agents[3].table.held_by(3) == ["pick:N"]  # back on its picket
    assert s.agents[2].table.held_by(2) == ["seg:H:0", "seg:H:1"]  # scout kept its cable


def test_stop_ends_the_watch():
    s = story()
    while not (TASK in s.agents[3].table.recs and s.agents[3].table.recs[TASK].owner == 3):
        s.tick()
    s.run_until(s.t + 60_000)
    assert s.shore.command(s.t, {"cmd": "stop", "id": TASK})
    s.run_until(s.t + 60_000)
    assert s.agents[3].contacts.watching() is None
    assert s.agents[3].mode != SHADOWING and s.agents[2].contacts.holding is None


def test_static_boats_report_the_contact_but_never_leave_station():
    """#19: static means fixed stations forever; detection and reports still run."""
    s = Sim(scene_mission(), replace(PARAMS, policy="static"), START)
    s.add_track("C-07", C07, sog=206, cog=0)
    modes = set()
    while s.t <= 3_000_000:
        s.tick()
        modes |= {a.mode for a in s.agents.values()}
    assert SHADOWING not in modes
    assert all(a.contacts.holding is None for a in s.agents.values())
    flags = [a.contacts.flags.get(TASK, {}) for a in s.agents.values()]
    assert any(f.get("dwell") for f in flags)  # it was seen and reported
    assert not any(f.get("capped") for f in flags)
