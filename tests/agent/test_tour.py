"""G1: tour geometry, cheapest insertion, follower."""
from itertools import permutations, product

from agent.tour import Tours
from contract.geo import dist
from contract.mission import load_params
from tests.agent.harness import Sim
from tests.agent.scene import SEGS, line_mission

TOURS = Tours(SEGS)


def build(tasks):
    legs = []
    for k in sorted(tasks):
        legs = TOURS.insert(legs, k)
    return legs


def brute(tasks):
    return min(TOURS.cycle_m([(k, r) for k, r in zip(order, revs)])
               for order in permutations(tasks) for revs in product((False, True),
                                                                    repeat=len(tasks)))


def test_single_segment_is_swept_back_and_forth():
    assert TOURS.cycle_m([("seg:M:0", False)]) == 2 * TOURS.len["seg:M:0"]


def test_initial_tours_are_optimal_on_the_scene():
    for tasks in (["seg:G:0", "seg:G:1", "seg:G:2", "seg:M:0"], ["seg:H:0", "seg:H:1"]):
        assert TOURS.cycle_m(build(tasks)) == brute(tasks)
    v = load_params().speed_mm_s
    cyc_01 = TOURS.cycle_m(build(["seg:G:0", "seg:G:1", "seg:G:2", "seg:M:0"])) * 1000 // v
    assert 10_800 <= cyc_01 <= 11_100  # scratch model: 10,969 s


def test_insertion_is_deterministic():
    assert build(["seg:G:2", "seg:M:0", "seg:G:0"]) == build(["seg:G:0", "seg:M:0", "seg:G:2"])


def test_follower_sweeps_both_ends():
    s = Sim(line_mission(), load_params(), {1: (1500, 0), 2: (4500, 0), 3: (3000, 1000)})
    ends, best = ((0, 0), (3000, 0)), [10**9, 10**9]
    while s.t <= 2_800_000:  # one back-and-forth of 6 km at 2.3 m/s is about 2,609 s
        s.tick()
        for i, e in enumerate(ends):
            best[i] = min(best[i], dist(s.xy(1), e))
    assert max(best) <= 10
