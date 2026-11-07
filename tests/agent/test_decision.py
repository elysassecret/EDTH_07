"""#123: one score per option; hand-built situations with a known right answer."""
from dataclasses import replace

from agent.core import Agent
from contract.constants import CLAIMED, RELEASED, SHADOWING
from contract.mission import Detection, Own, load_params
from contract.tasks import Rec
from tests.agent.harness import Sim
from tests.agent.scene import C07, START, scene_mission
from tests.agent.test_contact import TASK, story

PARAMS = load_params()


def opened(a: Agent, *tasks: str) -> None:
    for k in tasks:
        a.table.apply(Rec(k, a.table.max_ver(k) + 1, RELEASED, 0, 1, 0))


def test_ship_anchored_on_the_hvdc_nearest_free_boat_watches_the_sweeper_keeps_its_cables():
    """No-AIS ship loitering on the HVDC: the free picket (03) watches it, the sweeper that found
    it (02) goes back to its cables, and the shore shows what 03 compared before claiming."""
    s = story()
    while s.t <= 2_400_000 and not (s.agents[3].mode == SHADOWING
                                    and s.agents[2].contacts.holding is None):
        s.tick()
    assert s.agents[3].table.recs[TASK].owner == 3
    hvdc = sorted(k for k in s.agents[2].table.recs if k.startswith("seg:H:"))
    assert s.agents[2].table.held_by(2) == hvdc  # the sweeper is back on all its HVDC cable
    opts = s.shore.picture(s.t).tasks[TASK].options
    assert opts and opts[0][0] == TASK  # the contact was its best option


def test_low_battery_boat_does_not_even_consider_the_far_task():
    """Same spot, 300 permille: the near cable is an option, the far one is not (#104 limits are
    hard limits, never traded for score)."""
    a = Agent(4, scene_mission(), PARAMS)
    a.step(0, Own(1021, -5087, 300), (), [])
    opened(a, "seg:G:2", "seg:M:0")
    a.auction.on_slot(12_000)
    tasks = [k for _, k in a.auction.options]
    assert "seg:G:2" in tasks and "seg:M:0" not in tasks


def test_equal_situations_give_the_same_choice_on_every_run():
    def run():
        s = Sim(scene_mission(), PARAMS, START)
        s.run_until(600_000)
        s.set_batt(1, 200)
        s.run_until(900_000)
        pic = s.shore.picture(s.t)
        return {k: (v.owner, v.why, v.options) for k, v in pic.tasks.items()}
    assert run() == run()


def test_cable_risk_term_is_off_by_default_and_ranks_a_threatened_cable_first_when_on():
    """Off (config default): the score is the measured bid time, nothing else. On: a segment with
    a slow no-AIS ship next to it scores better than the same segment without one."""
    def scored(params, ship: bool) -> tuple[int, dict]:
        a = Agent(4, scene_mission(), params)
        seen = (Detection("X-1", *C07, 200, 0, False),) if ship else ()
        a.step(0, Own(1021, -5087, 1000), seen, [])
        opened(a, "seg:H:0")
        return a.auction.score("seg:H:0", 1_000)
    total, terms = scored(PARAMS, ship=True)
    assert list(terms) == ["time"] and total == terms["time"]
    on = replace(PARAMS, score_risk_permille=100, score_ships_permille=2000)
    assert scored(on, ship=True)[0] < scored(on, ship=False)[0]
    assert scored(on, ship=False)[1]["cable risk"] < 0  # age alone already counts


def test_a_claim_carries_its_options_to_the_shore_while_its_owner_holds_it():
    s = Sim(scene_mission(), PARAMS, START)
    s.run_until(600_000)
    s.set_batt(1, 200)
    s.run_until(900_000)
    tv = s.shore.picture(s.t).tasks["seg:G:0"]
    assert tv.state == CLAIMED and tv.owner == 4
    assert tv.options and all(isinstance(k, str) and isinstance(v, int) for k, v in tv.options)
    assert s.shore.picture(s.t).tasks["pick:S"].options == []  # released: nothing claimed
