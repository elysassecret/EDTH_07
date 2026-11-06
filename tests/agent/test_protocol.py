"""Protocol tests from agent/PLAN.md section 8.2: P0-P3, P6, return home, baseline policies."""
from dataclasses import replace

import pytest

from agent.table import Table
from contract.constants import CLAIMED, RELEASED, RETURNING, UNAVAILABLE
from contract.mission import Mission, TaskSpec, load_params
from contract.tasks import Rec, kind
from tests.agent.harness import Sim
from tests.agent.scene import START, scene_mission

PARAMS = load_params()


def three_lines(owners: dict[str, int]) -> Mission:
    """seg:X between two other segments; shore 18+ km away, out of radio range."""
    tasks = (TaskSpec("seg:X", ((0, 0), (1000, 0))), TaskSpec("seg:Y", ((0, 2000), (1000, 2000))),
             TaskSpec("seg:Z", ((0, -2000), (1000, -2000))))
    boats = tuple(sorted({1, 2, 3} & ({*owners.values()} | {2, 3})))
    return Mission(boats=boats, tasks=tasks, initial=tuple(owners.items()), shore=(0, 20_000),
                   lane=((0, 50_000), (1000, 50_000)), lane_half_m=650)


def owners(s: Sim, task: str) -> set[tuple[int, int]]:
    return {(a.table.recs[task].owner, a.table.recs[task].state)
            for b, a in s.agents.items() if s.alive[b]}


def test_p1_lost_bid_cheaper_boat_wins_after_merge():
    s = Sim(three_lines({"seg:Y": 2, "seg:Z": 3}), PARAMS, {2: (0, 2000), 3: (0, -3000)})
    s.link(2, 3, False)  # neither hears the other's bid: both claim
    s.run_until(13_000)
    assert s.agents[2].table.recs["seg:X"].owner == 2
    assert s.agents[3].table.recs["seg:X"].owner == 3
    s.link(2, 3, True)
    s.run_until(70_000)  # whole-table re-advertise every 30 s
    assert owners(s, "seg:X") == {(2, CLAIMED)}  # 2 was closer, so its bid was lower
    assert all(leg[0] != "seg:X" for leg in s.agents[3].legs())


def test_p2_winner_dies_mid_round_task_reauctioned():
    s = Sim(three_lines({"seg:Y": 2, "seg:Z": 3}), PARAMS, {2: (0, 2000), 3: (0, -3000)})
    s.run_until(5_000)
    s.kill(2)  # 2 bid at t = 0 and would have won at 12 s
    s.run_until(23_000)
    assert s.agents[3].table.recs["seg:X"].state == RELEASED
    s.run_until(30_000)
    assert s.agents[3].table.recs["seg:X"].owner == 3


def test_p3_heartbeat_mid_round_cancels_takeover():
    p = replace(PARAMS, seg_lease_ms=30_000)
    s = Sim(three_lines({"seg:X": 1, "seg:Y": 2, "seg:Z": 3}), p,
            {1: (0, 0), 2: (0, 2000), 3: (0, -2000)})
    s.run_until(9_000)
    s.isolate(1)  # last heartbeat heard from 1 was created at 9 s: lease ends at 39 s
    s.run_until(48_000)  # 2 and 3 bid on seg:X in the 48 s slot
    s.isolate(1, on=True)  # 1's heartbeat at 49 s arrives before the round closes at 60 s
    s.run_until(65_000)
    assert owners(s, "seg:X") == {(1, CLAIMED)}
    assert {a.table.recs["seg:X"].ver for a in s.agents.values()} == {1}


def test_p6_claim_beats_release_at_equal_version():
    for first, second in ((RELEASED, CLAIMED), (CLAIMED, RELEASED)):
        t = Table(1, PARAMS.seg_lease_ms, scene_mission())
        for state in (first, second):
            t.apply(Rec("pick:N", 2, state, 0 if state == RELEASED else 50, 3))
        assert t.recs["pick:N"].state == CLAIMED


@pytest.mark.parametrize("dead", [1, 2, 3, 4, 5])
def test_p0_any_boat_can_die(dead):
    """Real leases: segments reopen after 3,600 s of silence, the relay after 60 s. Killing the
    relay splits the fleet north/south until the new relay reaches the station."""
    s = Sim(scene_mission(), PARAMS, START)
    s.run_until(300_000)
    lost = s.agents[dead].table.held_by(dead)
    s.kill(dead)
    s.run_until(5_000_000)
    for task in s.agents[1 if dead != 1 else 2].table.recs:
        assert len(owners(s, task)) == 1, task  # every live boat agrees on every task
    for task in lost:
        if kind(task) == "pick":
            continue  # lowest priority: stays open while every boat is busy, and shows so
        ((owner, state),) = owners(s, task)
        assert state == CLAIMED and owner != dead and s.alive[owner], (task, owner)


def test_p4_isolated_boat_claims_nothing_majority_takes_over():
    s = Sim(scene_mission(), replace(PARAMS, seg_lease_ms=600_000), START)
    s.run_until(300_000)
    s.isolate(1)
    s.run_until(1_500_000)  # everyone's lease has expired in 1's view, and 1's in theirs
    assert sorted(s.agents[1].table.held_by(1)) == ["seg:G:0", "seg:G:1", "seg:G:2", "seg:M:0"]
    assert s.agents[4].table.held_by(4) == ["seg:G:0", "seg:G:1", "seg:G:2", "seg:M:0"]
    s.isolate(1, on=True)
    s.run_until(1_600_000)  # rejoin: the majority's higher versions win, 1 drops its copy
    assert s.agents[1].legs() == []
    assert s.agents[1].table.held_by(1) == ["pick:S"]  # and takes the picket 04 left open
    for task in ("seg:G:0", "seg:M:0"):
        assert owners(s, task) == {(4, CLAIMED)}


def test_p9_boat_out_of_range_under_the_seg_lease_keeps_its_work():
    """PLAN F4: 04 can be out of range for ~57 min after taking 01's tour."""
    s = Sim(scene_mission(), PARAMS, START)
    s.run_until(300_000)
    s.isolate(1)
    s.run_until(3_300_000)  # 50 min of silence, under the 60 min seg lease
    s.isolate(1, on=True)
    s.run_until(3_400_000)
    for task in ("seg:G:0", "seg:G:1", "seg:G:2", "seg:M:0"):
        assert owners(s, task) == {(1, CLAIMED)}
        assert {a.table.recs[task].ver for a in s.agents.values()} == {1}  # no churn


def test_battery_low_04_takes_the_cables_03_keeps_its_picket():
    """Scene story at 7,200 s, compressed (PLAN F3)."""
    s = Sim(scene_mission(), PARAMS, START)
    s.run_until(600_000)
    s.set_batt(1, 200)
    s.run_until(900_000)
    assert s.agents[1].mode == RETURNING
    for task in ("seg:G:0", "seg:G:1", "seg:G:2", "seg:M:0"):
        assert owners(s, task) == {(4, CLAIMED)}, task
    assert owners(s, "pick:S") == {(4, RELEASED)}  # lane picket S stays visibly uncovered
    assert owners(s, "pick:N") == {(3, CLAIMED)}  # 03 is still free for a contact
    s.run_until(6_000_000)
    assert s.agents[1].mode == UNAVAILABLE  # reached Korsør


def test_policy_off_repairs_nothing_after_the_event():
    p = replace(PARAMS, policy="off", repair_off_after_ms=500_000)
    s = Sim(scene_mission(), p, START)
    s.run_until(600_000)
    s.set_batt(1, 200)
    s.run_until(900_000)
    for task in ("seg:G:0", "seg:G:1", "seg:G:2", "seg:M:0"):
        assert owners(s, task) == {(1, RELEASED)}, task


def test_policy_static_parks_every_boat():
    s = Sim(scene_mission(), replace(PARAMS, policy="static"), START)
    s.run_until(4_000_000)
    for b in (1, 2):
        a = s.agents[b]
        x, y = a.static_point
        assert abs(s.xy(b)[0] - x) <= 300 and abs(s.xy(b)[1] - y) <= 300, b
