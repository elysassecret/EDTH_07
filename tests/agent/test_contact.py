"""Phase 5 boat side: the scripted contact story on the scene-like mission (PLAN section 2)."""
from dataclasses import replace

from contract.constants import CLAIMED, DEPUTY_GRACE, LEASE, PATROL, RELEASED, SENTINEL, SHADOWING
from contract.geo import dist
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


def test_patrol_keeps_out_of_the_standoff_ring_once_the_contact_is_known():
    """PLAN 7.9: after the watcher relieves the scout, the scout's sweep goes round the 1 nm ring
    instead of over the contact (a closer look waits for the watch officer). No AIS only."""
    s = story()
    closest = None
    while s.t <= 2_590_000:  # C-07 still loitering
        s.tick()
        a = s.agents[2]
        if a.mode in (PATROL, SENTINEL) and "C-07" in a.contacts.tracks:
            d = dist(s.xy(2), C07)
            closest = d if closest is None else min(closest, d)
    assert closest is not None and closest >= PARAMS.standoff_m
    assert s.agents[2].mode == PATROL  # still sweeping, not stuck on the ring


def test_a_crossing_ais_ship_makes_the_sweeper_go_round():
    """#118: a ship with AIS crossing USV 01's straight line at 5 m/s; from its course and speed
    the boat sees the closest point of approach would be inside the clearance and plans round it.
    Without this rule the two pass about 700 m apart."""
    s = Sim(scene_mission(), PARAMS, START, detect_m=10_000)  # AIS reaches further than a camera
    s.run_until(60_000)
    x0, y0 = s.xy(1)
    s.add_track("S-01", (x0 + 2000, y0 - 2600), sog=5000, cog=0, ais=True)
    closest = None
    while s.t <= 1_200_000:
        s.tick()
        tr = s.tracks["S-01"]
        d = dist(s.xy(1), (tr["x"] // 1000, tr["y"] // 1000))
        closest = d if closest is None else min(closest, d)
    assert closest >= PARAMS.ship_clearance_m, closest
    assert s.agents[1].mode == PATROL  # it went round and carried on sweeping
