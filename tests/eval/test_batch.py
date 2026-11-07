"""Features 4 and 12 on a short horizon: the full batch is `python -m eval.run_batch`."""
from pathlib import Path

from eval.repeat import check_processes, check_reset
from eval.run_batch import batch, fairness, main, run_case

ROOT = str(Path.cwd())
SHORT_S = 300


def test_seeded_case_repeats_across_processes_and_hash_seeds():
    result = check_processes((ROOT, 2, "elysa", SHORT_S))
    assert result["ok"], result["digests"]


def test_reset_mid_run_equals_fresh_run():
    result = check_reset(ROOT, 3, "off", SHORT_S)
    assert result["ok"], result["digests"]


def test_modes_differ_in_policy_only_and_report_every_mode():
    report = batch(Path("."), [1], ["static", "off", "elysa"], SHORT_S)
    assert set(report["summary"]) == {"static", "off", "elysa"}
    by_name = {c["check"]: c for c in report["checks"]}
    assert by_name["F1"]["ok"] and by_name["F4"]["ok"]
    assert not by_name["F5"]["ok"]  # one seed is never a headline
    assert not report["headline_ok"]
    for run in report["runs"]:
        assert run["coverage"]["km_never_visited"] > 0  # cold start: the gap shows


def test_fairness_flags_claims_and_extra_keys():
    base = run_case((ROOT, 1, "off", SHORT_S))
    off = {**base, "end_s": 10, "repair_off_after_s": 5, "claims_after_fail": [[6, 1, "seg:G:0"]]}
    other = {**base, "policy": "elysa", "params": {**base["params"], "speed_mm_s": 1}}
    checks = {c["check"]: c["ok"] for c in fairness([off, other])}
    assert checks["F3"] is False and checks["F4"] is False


def test_cli_exit_code_is_nonzero_without_a_headline(capsys):
    assert main(["--seeds", "1", "--modes", "elysa", "--horizon-s", "60"]) == 1
    assert "PRELIMINARY" in capsys.readouterr().out
