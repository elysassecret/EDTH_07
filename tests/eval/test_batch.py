"""Features 4 and 12 on a short horizon: the full batch is `python -m eval.run_batch`."""
from pathlib import Path

from eval.repeat import check_processes, check_reset
from eval.report import fairness, headline_ok
from eval.run_batch import main, run_all, run_case

ROOT = str(Path(__file__).resolve().parents[2])
SHORT_S = 120
WARM = 60


def case(policy, seed=1):
    return (ROOT, seed, policy, SHORT_S, None, None, WARM)


def test_seeded_case_repeats_across_processes_and_hash_seeds():
    result = check_processes(case("elysa", 2))
    assert result["ok"], result["digests"]


def test_reset_mid_run_equals_fresh_run():
    result = check_reset(ROOT, 3, "off", SHORT_S)
    assert result["ok"], result["digests"]


def test_modes_differ_in_policy_only_and_one_seed_is_never_a_headline():
    cards = run_all([case(m) for m in ("static", "off", "elysa")])
    by_name = {}
    for c in fairness(cards):
        by_name.setdefault(c["check"], []).append(c["ok"])
    assert all(by_name["F1"]) and all(by_name["F4"])
    assert not all(by_name["F5"])
    assert not headline_ok(cards)
    assert {c["mode"] for c in cards} == {"static", "off", "elysa"}


def test_a_run_shorter_than_the_tape_still_reports_and_says_never_visited():
    card = run_case(case("elysa"))
    assert card["t_s"] == SHORT_S
    assert card["never_visited_km"] > 0
    assert card["ages_hash_T1"] is None


def test_cli_exit_code_is_nonzero_without_a_headline(tmp_path, capsys):
    argv = ["--modes", "elysa", "--seeds", "1", "--horizon-s", "60", "--warm-s", "60",
            "--no-ais", "--jobs", "1", "--out", str(tmp_path)]
    assert main(argv) == 1
    assert "PRELIMINARY" in capsys.readouterr().out
    assert (tmp_path / "elysa_s1.jsonl").exists()
    assert (tmp_path / "scorecard.md").exists()
