"""Feature 3: revisit age per cable segment and km overdue, from sensor visits only."""
from eval.metrics import Window, coverage, sample_ages

TASKS = ["seg:A:0", "seg:A:0", "seg:A:0", "seg:B:0"]


def test_never_visited_is_aged_from_zero():
    assert sample_ages([None, 5_000], 10_000) == [10_000, 5_000]


def test_segment_age_is_its_worst_sample():
    cov = coverage(TASKS, [9_000, 2_000, 8_000, 9_500], 10_000, 5_000, 100)
    assert cov.seg_age_ms == {"seg:A:0": 8_000, "seg:B:0": 500}
    assert cov.worst_age_ms == 8_000


def test_km_overdue_counts_samples_strictly_older_than_target():
    # ages 5000 (equal to target, not overdue), 8000, 9000 (overdue), never visited (10000)
    cov = coverage(TASKS, [5_000, 2_000, 1_000, None], 10_000, 5_000, 100)
    assert cov.overdue_m == 300
    assert cov.km_overdue == 0.3
    assert cov.seg_overdue_m == {"seg:A:0": 200, "seg:B:0": 100}
    assert cov.never_m == 100 and cov.seg_never_m == {"seg:A:0": 0, "seg:B:0": 100}


def test_assignment_alone_never_closes_the_gap():
    # S5: coverage() takes no ownership input at all; a segment someone claims but nobody
    # has visited stays fully overdue and fully never-visited.
    cov = coverage(["seg:A:0"] * 3, [None] * 3, 20_000, 5_000, 100)
    assert cov.km_overdue == cov.km_never == 0.3


def test_row_is_in_seconds_and_km():
    row = coverage(TASKS, [9_000, 2_000, 8_000, 9_500], 10_000, 5_000, 100).row()
    assert row["seg_age_s"] == {"seg:A:0": 8, "seg:B:0": 0}
    assert row["km_overdue"] == 0.1 and row["t_s"] == 10 and row["target_s"] == 5


def test_window_mean_only_inside_bounds():
    w = Window(1_000, 3_000)
    for t, visits in ((0, [None]), (1_000, [None]), (3_000, [2_900]), (4_000, [None])):
        w.add(coverage(["seg:A:0"], visits, t, 500, 100))
    assert w.count == 2 and w.mean_km == 0.05
    assert Window(0, 1).mean_km is None
