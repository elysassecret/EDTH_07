"""Phase 5 boat side: the scripted contact story on the scene-like mission (PLAN section 2)."""
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


def test_shore_shows_the_contact_and_cards_from_delivered_messages_only():
    """#17: contact, seen-by, watcher and both cards on the shore; approval reaches the watcher."""
    s = story()
    while s.t <= 3_000_000 and "close:" + TASK not in s.shore.decisions:
        s.tick()
    pic = s.shore.picture(s.t)
    (c,) = pic.contacts
    assert c.id == TASK and c.source == "camera" and c.watcher == 3 and c.flags.dwell
    assert c.seen_by and c.first_seen <= c.last_seen and c.trail
    cards = {d.id: d for d in pic.decisions}
    assert cards[TASK].tier == "delegated" and cards[TASK].actions == ["confirm", "stop"]
    assert cards["close:" + TASK].tier == "held" and cards["close:" + TASK].state == "pending"
    assert cards["close:" + TASK].boat == 3 and cards["close:" + TASK].route
    s.shore.command(s.t, {"cmd": "approve", "id": "close:" + TASK})
    while s.t <= 3_000_000 and not s.shore.contacts.flags[TASK]["name"]:
        s.tick()
    pic = s.shore.picture(s.t)
    assert {d.id: d.state for d in pic.decisions}["close:" + TASK] == "delivered"
    assert pic.contacts[0].flags.name  # the look within 500 m, as reported by 03
    assert any(e.kind == "contact_name" for e in pic.events)

