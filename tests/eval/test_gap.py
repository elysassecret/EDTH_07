"""Feature 11: the remaining gap stays visible on the console and is never hidden."""
from pathlib import Path

from eval.gap import SLACK_S, GapAudit, hidden_s

ROOT = str(Path(__file__).resolve().parents[2])
TRUTH = {"seg:A:0": None, "seg:B:0": 4}  # A has an unvisited sample; the world is 10 s old


def test_older_on_shore_is_fine_fresher_is_hidden():
    assert hidden_s({"seg:A:0": 10, "seg:B:0": 9}, TRUTH, 10) == {"seg:A:0": 0, "seg:B:0": 0}
    assert hidden_s({"seg:A:0": 1, "seg:B:0": 4}, TRUTH, 10) == {"seg:A:0": 9, "seg:B:0": 0}


def test_segment_missing_from_shore_is_hidden_entirely():
    assert hidden_s({"seg:B:0": 4}, TRUTH, 10)["seg:A:0"] == 10


def test_audit_keeps_worst_and_flags_only_beyond_slack():
    audit = GapAudit(slack_s=5)
    audit.add({"seg:A:0": 7, "seg:B:0": 4}, TRUTH, 10)  # hidden 3: within slack
    assert audit.row()["ok"] and audit.max_hidden_s == 3
    audit.add({"seg:A:0": 2, "seg:B:0": 14}, {"seg:A:0": 20, "seg:B:0": 4}, 20)
    assert audit.violations == {"seg:A:0": (18, 20)}
    assert not audit.row()["ok"]


def test_console_never_shows_a_segment_fresher_than_truth():
    from eval.run_batch import run_case

    card = run_case((ROOT, 1, "elysa", 1_200, None, None, 60))
    assert card["gap"]["max_hidden_s"] <= SLACK_S, card["gap"]
