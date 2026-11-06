"""Feature 11: the remaining gap stays visible on the console and is never hidden."""
import pytest

from eval.gap import SLACK_S, GapAudit, hidden_s
from eval.metrics import coverage

TASKS = ["seg:A:0", "seg:A:0", "seg:B:0"]


def truth(t_ms=10_000):
    # seg:A:0 worst sample never visited (10 s); seg:B:0 visited at 6 s (4 s old)
    return coverage(TASKS, [9_000, None, 6_000], t_ms, 5_000, 100)


def test_older_on_shore_is_fine_fresher_is_hidden():
    assert hidden_s({"seg:A:0": 10, "seg:B:0": 9}, truth()) == {"seg:A:0": 0, "seg:B:0": 0}
    assert hidden_s({"seg:A:0": 1, "seg:B:0": 4}, truth()) == {"seg:A:0": 9, "seg:B:0": 0}


def test_segment_missing_from_shore_is_hidden_entirely():
    assert hidden_s({"seg:B:0": 4}, truth())["seg:A:0"] == 10


def test_audit_keeps_worst_and_flags_only_beyond_slack():
    audit = GapAudit(slack_s=5)
    audit.add({"seg:A:0": 7, "seg:B:0": 4}, truth())  # hidden 3: within slack
    assert audit.row()["ok"] and audit.max_hidden_s == 3
    audit.add({"seg:A:0": 2, "seg:B:0": 14}, truth(20_000))  # true 20 s, shown 2 s
    assert audit.violations == {"seg:A:0": (18, 20)}
    assert not audit.row()["ok"]


@pytest.mark.xfail(strict=True, reason=(
    "agent/shore.py (owner A) credits a whole segment when a heartbeat is within r_verify_m "
    "of any point on it, so the console shows partly swept segments as fresh. Remove this "
    "marker once the shore ages match the worst sample."))
def test_console_never_shows_a_segment_fresher_than_truth():
    from eval.run_batch import run_case
    result = run_case((".", 1, "elysa", 1_200))
    assert result["gap"]["max_hidden_s"] <= SLACK_S, result["gap"]
