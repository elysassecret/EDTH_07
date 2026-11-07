"""Phase 5 boat side: the scripted contact story on the scene-like mission (PLAN section 2)."""
from contract.constants import CLAIMED, DEPUTY_GRACE, LEASE, RELEASED, SHADOWING
from contract.mission import load_params
from contract.tasks import Rec
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


def test_p8_deputy_takes_the_watch_without_an_auction():
    """PLAN 7.10: the watcher goes silent; its named deputy claims at ver + 1 as soon as the
    lease ends, before the deputy grace would let a new auction start."""
    s = story()
    while s.t <= 3_000_000 and s.agents[3].table.recs.get(TASK, Rec(TASK, 0, 0, 0, 0)).state != CLAIMED:
        s.tick()
    r = s.agents[3].table.recs[TASK]
    assert r.owner == 3 and r.deputy not in (0, 3)
    s.kill(3)
    dead_at = s.t
    while s.t <= dead_at + LEASE + DEPUTY_GRACE:
        s.tick()
        new = s.agents[r.deputy].table.recs[TASK]
        if new.owner == r.deputy:
            break
    assert new == Rec(TASK, r.ver + 1, CLAIMED, new.bid, r.deputy, 0)
    assert s.t < dead_at + LEASE + DEPUTY_GRACE  # no auction needed
