"""F1 to F5: the three modes see identical inputs and differ by one config key per step."""
import hashlib

import pytest

from contract.config import MODES, load
from eval.report import table
from tests.helpers import make_sim, run_cached

T = 7200


@pytest.fixture(scope="module")
def runs():
    out = {}
    for mode in ("static", "off", "elysa"):
        sim, m = make_sim(mode, 1)
        sim.run_warm()
        sim.run_until(T + 400)
        out[mode] = (sim, m)
    return out


def test_f1_warm_state_tape_and_events_equal_across_modes(runs):
    warm = {m: s.warm_hash for m, (s, _) in runs.items()}
    tapes = {m: s.tape.hash() for m, (s, _) in runs.items()}
    assert len(set(tapes.values())) == 1, tapes
    # warm state is identical for the two sweeping modes; static boats hold position so their hash differs by design
    assert warm["off"] == warm["elysa"], warm


def test_f2_segment_ages_at_T_minus_1_identical(runs):
    h = {m: hashlib.sha256(mm.ages_at_T_minus_1).hexdigest() for m, (_, mm) in runs.items() if mm.ages_at_T_minus_1}
    assert h["off"] == h["elysa"], h


def test_f3_repair_off_makes_no_repair_claims_after_T(runs):
    sim, _ = runs["off"]
    claims = [(t, b, k, body) for b, a in sim.agents.items() for t, k, body in a.events
              if k == "claim" and t >= T * 1000 and body["task"].startswith(("seg:", "pick:"))]
    assert claims == []
    sim_e, _ = runs["elysa"]
    claims_e = [1 for a in sim_e.agents.values() for t, k, body in a.events
                if k == "claim" and t >= T * 1000 and body["task"].startswith("seg:")]
    assert len(claims_e) >= 3


def test_f4_config_diff_between_adjacent_modes_is_one_key():
    def flat(cfg):
        return {f"{s}.{k}": v for s, d in cfg.items() if isinstance(d, dict) for k, v in d.items()}
    s, o, e = (flat(load(overrides=MODES[m])) for m in ("static", "off", "elysa"))
    assert [k for k in s if s[k] != o[k]] == ["agent.sweep"]
    assert [k for k in o if o[k] != e[k]] == ["agent.repair"]


def test_f5_report_uses_median_and_range_over_at_least_five_seeds():
    cfg = load()
    assert len(cfg["run"]["seeds"]) >= 5
    fake = [{"mode": "elysa", "seed": s, "cable_km_overdue": v, "worst_age_s": 1, "lane_crossings_in_view": 1,
             "lane_crossings_post_event": 2, "operator_actions": 0, "claims": 1, "repair_claims_after_T": 0,
             "worst_age_post_event_s": 1, "time_to_all_segs_owned_s": 60} for s, v in enumerate([1.0, 5.0, 3.0, 9.0, 2.0])]
    txt = table(fake)
    assert "3.0 (1.0 to 9.0)" in txt
    assert "| Seeds | 5 |" in txt
