"""Features 15-16: SENTINEL drift-and-correct and the current-aware return rule."""
from agent.core import Agent
from contract.constants import SENTINEL
from contract.mission import Own, load_params
from tests.agent.harness import Sim
from tests.agent.scene import PICK_N, START, scene_mission

PARAMS = load_params()


def test_picket_drifts_with_motors_off_and_corrects_past_300_m():
    s = Sim(scene_mission(), PARAMS, START)
    s.run_until(30_000)
    assert s.actions[3].mode == SENTINEL and s.actions[3].target is None  # motors off
    s.pos[3] = ((PICK_N[0] + 250) * 1000, PICK_N[1] * 1000)  # current pushed it 250 m
    s.run_until(40_000)
    assert s.actions[3].target is None  # still inside the 300 m radius: keep drifting
    s.pos[3] = ((PICK_N[0] + 400) * 1000, PICK_N[1] * 1000)  # now 400 m off station
    s.run_until(42_000)
    assert s.actions[3].target == PICK_N  # pulse the motors back
    s.run_until(200_000)
    assert s.actions[3].target is None and abs(s.xy(3)[0] - PICK_N[0]) <= 100  # and stop again


def test_return_time_depends_on_the_current():
    a = Agent(1, scene_mission(), PARAMS)
    a.step(0, Own(-2381, -5197, 1000), (), [])
    still = a.return_ms(a.pos)
    a.step(1_000, Own(-2381, -5197, 1000, cur_x=500), (), [])  # 0.5 m/s towards Korsør (east)
    helped = a.return_ms(a.pos)
    a.step(2_000, Own(-2381, -5197, 1000, cur_x=-500), (), [])  # against
    against = a.return_ms(a.pos)
    assert helped < still < against


def test_return_rule_fires_with_safety_margin():
    a = Agent(1, scene_mission(), PARAMS)
    # 10.9 km from Korsør: 4,734 s home + 1,800 s reserve, x 1.2 = 7,840 s needed
    a.step(0, Own(-2381, -5197, 330), (), [])  # 8,316 s left at cruise
    assert not a.returning
    a.step(1_000, Own(-2381, -5197, 300), (), [])  # 7,560 s left
    assert a.returning and a.table.held_by(1) == []


def test_no_bid_on_a_task_that_does_not_fit_the_battery():
    """#104 admission: the same boat at the same place bids on a near cable but not on a far one
    once the trip there, one pass and the trip home (x 1.2, plus the reserve) no longer fit."""
    a = Agent(4, scene_mission(), PARAMS)
    a.step(0, Own(1021, -5087, 1000), (), [])  # at the G:1/G:2 joint, full battery
    assert a.auction.energy_ok("seg:G:2") and a.auction.energy_ok("seg:M:0")
    a.step(1_000, Own(1021, -5087, 300), (), [])  # 2 h 06 m left: G:2 needs 238, M:0 495
    assert a.auction.energy_ok("seg:G:2")  # next to it, close to Korsør
    assert not a.auction.energy_ok("seg:M:0")  # far south-west: it would eat the reserve


def test_adverse_current_sends_the_boat_home_before_the_reserve():
    """#104 handover: the return cost uses the current the boat measures every tick, so a current
    against it moves the decision earlier; it releases its tasks with the reserve untouched."""
    a = Agent(1, scene_mission(), PARAMS)
    a.step(0, Own(-2381, -5197, 400), (), [])  # 10.9 km from Korsør, still water: fine
    assert not a.returning and a.table.held_by(1)
    a.step(1_000, Own(-2381, -5197, 400, cur_x=-1_200), (), [])  # 1.2 m/s against the way home
    assert a.returning and a.table.held_by(1) == []  # handed over: everything released
    assert a.remaining_ms() > PARAMS.reserve_ms  # and the 30 min reserve is still there



def health_lines(s: Sim) -> list[str]:
    return [e["text"] for e in s.shore.events if e["kind"] == "health"]


def test_weak_propulsion_is_reported_replanned_then_the_boat_goes_home():
    """#106: with 70 % of its propulsion gone, the sweeper sees its progress fall below the
    prediction from its own command and current, tells the shore in plain words and plans with
    the speed it really makes; after the bounded attempts it releases everything and goes home.
    The healthy boats report nothing."""
    s = Sim(scene_mission(), PARAMS, START)
    s.run_until(600_000)
    s.slow[1] = 300  # unknown to USV 01
    s.run_until(1_000_000)
    first = health_lines(s)
    assert len(first) == 1 and first[0].startswith("USV 01: progress below plan"), first
    assert "possible propulsion fault or strong current (model estimate)" in first[0]
    a = s.agents[1]
    assert 250 <= a.speed_permille <= 350 and a.v_plan() < PARAMS.speed_mm_s
    assert any(r["kind"] == "health" for r in a.chain.records)  # also in its own signed log
    s.run_until(1_800_000)
    assert health_lines(s)[-1] == "USV 01: no recovery after 5 checks: releasing everything and going home"
    assert a.returning and a.table.held_by(1) == []
    assert all(e["text"].startswith("USV 01") for e in s.shore.events if e["kind"] == "health")


def test_a_short_fault_clears_and_the_boat_plans_at_cruise_again():
    s = Sim(scene_mission(), PARAMS, START)
    s.run_until(600_000)
    s.slow[1] = 300
    s.run_until(1_000_000)
    assert s.agents[1].speed_permille < 1000
    s.slow[1] = 1000  # the fault clears before the attempts run out
    s.run_until(1_400_000)
    a = s.agents[1]
    assert a.speed_permille == 1000 and not a.returning
    assert health_lines(s)[-1] == "USV 01: progress back to plan"
