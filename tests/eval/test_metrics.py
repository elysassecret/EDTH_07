"""Metric arithmetic on small stand-ins, plus the km total on the real scene."""
import pytest

from contract.mission import TaskSpec
from eval.ais_observer import AisObserver, Crossing, cut, find_crossings
from eval.metrics import (
    interval_lengths_m,
    km_overdue,
    never_visited_km,
    seg_ages_s,
    task_lengths_m,
    worst_age_ms,
)
from eval.report import console_scorecard, fairness, fmt_stat, table
from eval.warm import build_world, seed_phases, tour_point
from world.routes import RouteSample, load_scene


def sample(task, offset):
    return RouteSample(task, offset, (0, 0))


def test_interval_lengths_use_the_short_last_interval():
    samples = [sample("seg:A:0", 0), sample("seg:A:0", 100), sample("seg:B:0", 0)]
    assert interval_lengths_m(samples, {"seg:A:0": 130.0, "seg:B:0": 40.0}) == [100, 30, 40]


def test_real_scene_km_sum_to_the_route_not_to_100_m_per_sample():
    scene = load_scene(".")
    km = interval_lengths_m(scene.samples, task_lengths_m(scene.mission.tasks))
    assert len(km) == 241
    assert sum(km) / 1000 == pytest.approx(23.6, abs=0.05)
    assert 241 * 0.1 - sum(km) / 1000 > 0.4  # the error the flat rule would have made


def test_task_lengths_skip_stations():
    tasks = [TaskSpec("seg:A:0", ((0, 0), (3, 4))), TaskSpec("relay", ((1, 1),))]
    assert task_lengths_m(tasks) == {"seg:A:0": 5.0}


def test_overdue_is_strict_and_never_visited_stays_out():
    visits = [5_000, 2_000, None, 1_000]
    km = [0.1, 0.1, 0.1, 0.05]
    assert km_overdue(visits, km, 10_000, 5_000) == pytest.approx(0.15)
    assert never_visited_km(visits, km) == pytest.approx(0.1)


def test_worst_age_ignores_none_and_is_none_when_nothing_was_visited():
    assert worst_age_ms([9_000, None, 4_000], 10_000) == 6_000
    assert worst_age_ms([None, None], 10_000) is None


def test_segment_with_any_unvisited_sample_has_no_age_in_either_order():
    samples = [sample("seg:A:0", 0), sample("seg:A:0", 100), sample("seg:B:0", 0),
               sample("seg:B:0", 100)]
    ages = seg_ages_s(samples, [None, 8_000, 8_000, None], 10_000)
    assert ages == {"seg:A:0": None, "seg:B:0": None}
    assert seg_ages_s(samples[2:], [8_000, 9_000], 10_000) == {"seg:B:0": 2}


def test_report_counts_runs_that_never_reached_a_value():
    assert fmt_stat([1.0, 5.0, 3.0, 9.0, 2.0], "{:.1f}") == "3.0 (1.0 to 9.0)"
    assert fmt_stat([60, None, 80], "{:.0f}") == "70 (60 to 80), reached in 2 of 3"
    assert fmt_stat([None, None], "{:.0f}") == "not reached"


def card(mode, **kw):
    base = {"mode": mode, "seed": 1, "contacts": [], "ais_present": False,
            "warm_hash": "w", "ages_hash_T1": "a", "state_hash_T1": "s",
            "repair_claims_after_T": 0, "params": {"policy": mode, "speed_mm_s": 2300}}
    return {**base, **kw}


def test_missing_ais_is_said_not_shown_as_zero():
    assert "AIS clip not present" in table([card("off", cable_km_overdue=1.0)])


def test_fairness_passes_identical_inputs_and_catches_each_difference():
    good = [card(m, seed=s, seg_age_s={"seg:A:0": s}) for m in ("off", "elysa") for s in range(1, 6)]
    assert all(c["ok"] for c in fairness(good))
    bad = [card("off", repair_claims_after_T=2, warm_hash="x"),
           card("elysa", ages_hash_T1="b", params={"policy": "elysa", "speed_mm_s": 3000})]
    assert {c["check"] for c in fairness(bad) if not c["ok"]} >= {"F1", "F2", "F3", "F4"}


def test_console_scorecard_matches_the_typed_hook_and_says_when_it_is_preliminary():
    cards = [card("off", seed=s, cable_km_overdue=float(s), seg_age_s={"a": s}) for s in range(1, 6)]
    out = console_scorecard(cards)
    assert out["seeds"] == [1, 2, 3, 4, 5]
    row = out["rows"][0]
    assert (row["mode"], row["unit"], row["median"], row["min"], row["max"]) == ("off", "km", 3, 1, 5)
    assert out["preliminary"] is False
    gap = {"ok": False, "max_hidden_s": 99}
    assert console_scorecard([{**c, "gap": gap} for c in cards])["preliminary"] is True


def test_phases_depend_on_the_seed_and_repeat():
    assert seed_phases(1, (1, 2)) == seed_phases(1, (1, 2))
    assert seed_phases(1, (1, 2)) != seed_phases(2, (1, 2))


def test_tour_point_walks_the_polyline_in_mm():
    pts = [(0, 0), (10, 0), (10, 10)]
    assert tour_point(pts, 0.0) == (0, 0)
    assert tour_point(pts, 0.75) == (10_000, 5_000)
    assert tour_point(pts, 1.0) == (10_000, 10_000)


def test_phases_spread_round_the_tour_instead_of_snapping_to_waypoints():
    """Regression: `start_nearest` alone collapsed every seed onto a few cable vertices."""
    spots = set()
    for seed in range(1, 11):
        world = build_world(".", "off", seed, warm_s=60)
        x, y = world.boats[2].point
        node = world.nodes[2]
        spots.add((x // 500, y // 500))
        way = node.tours.way(node.follow.legs[node.follow.i])
        assert way[node.follow.j] != (x, y)  # heading for a waypoint ahead, not sat on one
    assert len(spots) >= 8


def test_cut_finds_the_crossing_and_its_place_along_the_ship_step():
    assert cut((0, -1), (0, 3), (-1, 0), (1, 0)) == (0.25, 0.0, 0.0)
    assert cut((5, -1), (5, 1), (-1, 0), (1, 0)) is None


def test_crossings_need_one_track_and_a_short_gap_and_dedupe_jitter():
    cables = {"H": [((-100, 0), (100, 0))]}
    across = [("a", 0, 0, -10), ("a", 10_000, 0, 10)]
    assert [c.t_ms for c in find_crossings(across, cables)] == [5_000]
    other = [("a", 0, 0, -10), ("b", 10_000, 0, 10)]
    assert find_crossings(other, cables) == []
    gap = [("a", 0, 0, -10), ("a", 4_000_000, 0, 10)]
    assert find_crossings(gap, cables) == []
    jitter = across + [("a", 20_000, 0, -10)]
    assert len(find_crossings(jitter, cables)) == 1


def test_observer_scores_in_view_at_the_crossing_time_only_inside_the_window():
    crossings = [Crossing(50, "a", "H", 0, 0), Crossing(150, "a", "H", 0, 0),
                 Crossing(160, "b", "H", 0, 0), Crossing(500, "c", "H", 0, 0)]
    obs = AisObserver(crossings, 2_000, 100, 400)
    obs.on_tick(150, [(1_000, 0)])
    obs.on_tick(160, [(5_000, 0)])
    assert obs.summary() == {"ais_present": True, "crossings_after_T": 2, "crossings_in_view": 1}


def test_absent_clip_reports_absence():
    assert AisObserver([], 2_000, 0, 1, present=False).summary() == {"ais_present": False}
