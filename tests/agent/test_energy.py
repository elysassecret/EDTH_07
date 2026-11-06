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
