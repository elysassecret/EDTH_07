"""ShoreNode picture and watch-officer commands; relay election rules P7 and S6."""
from contract.constants import CLAIMED, SHORE_SILENCE, VETOED
from contract.mission import load_params
from contract.tasks import Rec
from contract.views import Snapshot
from tests.agent.harness import Sim
from tests.agent.scene import START, line_mission, scene_mission

PARAMS = load_params()


def scene():
    return Sim(scene_mission(), PARAMS, START)


def test_picture_shows_only_what_the_shore_received():
    s = scene()
    s.run_until(30_000)
    pic = s.shore.picture(s.t, speed=240)
    assert isinstance(pic, Snapshot) and pic.view == "shore"
    Snapshot.model_validate(pic.model_dump())  # round-trips through the contract
    links = {b.id: b.link for b in pic.boats}
    assert links == {1: "direct", 2: "peer", 3: "peer", 4: "direct", 5: "direct"}
    via = {b.id: b.via for b in pic.boats}
    assert via[1] == via[4] == via[5] == 0 and via[2] == via[3] == 5  # north talks via the relay
    assert pic.seg_age["seg:G:1"] <= 10 and pic.seg_age["seg:M:0"] >= 30  # M:0 not visited yet
    boat1 = next(b for b in pic.boats if b.id == 1)
    assert boat1.sog == PARAMS.speed_mm_s and boat1.mode == "PATROL"


def test_cut_boat_keeps_old_data_on_the_shore():
    s = scene()
    s.run_until(30_000)
    s.isolate(4)
    s.run_until(120_000)
    b4 = next(b for b in s.shore.picture(s.t).boats if b.id == 4)
    assert b4.link == "none" and b4.last_heard <= 31  # never refreshed from truth


def test_stop_is_delivered_to_the_watcher_and_sticks():
    s = scene()
    s.run_until(30_000)
    s.agents[3].publish(Rec("contact:C-07", 1, CLAIMED, 10, 3))  # pretend 03 is watching
    s.run_until(40_000)
    assert s.shore.command(s.t, {"cmd": "stop", "id": "contact:C-07"})
    s.run_until(60_000)
    for a in s.agents.values():
        assert a.table.recs["contact:C-07"].state == VETOED
    (d,) = s.shore.picture(s.t).decisions
    assert d.state == "delivered" and d.boat == 3 and d.tier == "delegated"
    assert s.shore.net.pending == {}  # retries stopped once 03 acknowledged
    assert any("Delivered to USV 03" in e["text"] for e in s.shore.events)


def test_approval_to_an_unreachable_boat_expires():
    s = scene()
    s.run_until(30_000)
    s.agents[3].publish(Rec("contact:C-07", 1, CLAIMED, 10, 3))
    s.run_until(40_000)
    s.isolate(3)
    s.shore.command(s.t, {"cmd": "approve", "id": "close:contact:C-07"})
    s.run_until(80_000)
    (d,) = s.shore.picture(s.t).decisions
    assert d.state == "expired" and d.tier == "held"  # others acked, but not the boat that acts
    assert not s.shore.command(s.t, {"cmd": "inject", "kind": "boat_off", "a": 2})


def test_p7_group_with_a_shore_path_elects_no_relay():
    s = scene()
    s.run_until(30_000)
    s.link(4, 0, False)  # 04 loses its direct shore link but still hears the shore via 05
    s.run_until(630_000)
    assert s.t - s.agents[4].shore_t <= SHORE_SILENCE
    for a in s.agents.values():
        assert a.table.recs["relay"] == Rec("relay", 1, CLAIMED, 0, 5)


def test_s6_relay_lost_nobody_cut_off_relay_stays_open():
    s = Sim(line_mission(), PARAMS, {1: (1500, 0), 2: (4500, 0), 3: (3000, 1000)})
    s.run_until(30_000)
    s.kill(3)
    s.run_until(600_000)
    for b in (1, 2):
        t = s.agents[b].table
        assert t.recs["relay"].owner == 3 and t.is_open("relay", s.t)  # open and visible
