"""Audit output is repeatable and clearly distinguished from eval results."""

from pathlib import Path

import pytest

from world.check import comparisons, run_case

ROOT = str(Path(__file__).resolve().parents[2])


def test_short_real_audit_is_deterministic_and_pre_event_modes_match():
    a = run_case((ROOT, 1, "elysa", 2300, 10))
    b = run_case((ROOT, 1, "off", 2300, 10))
    assert a == run_case((ROOT, 1, "elysa", 2300, 10))
    assert a["initial_phase"]["strategy"] == "cold-seeded-cable-offsets-v1"
    assert a["initial_phase"]["enabled"] is True
    assert a["comparison_ms"] == 10000
    assert a["contact"]["first_local_detection_ms"] is None
    assert comparisons([a, b])[0]["elysa_off_pre_event_physical_equal"] is True
    assert comparisons([a])[0]["elysa_off_pre_event_physical_equal"] is None
    changed = {**b, "pre_event_physical_hash": "different"}
    assert comparisons([a, changed])[0]["elysa_off_pre_event_physical_equal"] is False


@pytest.mark.parametrize(
    "policy,speed,horizon", [("bad", 2300, 1), ("off", 0, 1), ("off", 2300, -1)]
)
def test_invalid_audit_inputs(policy, speed, horizon):
    with pytest.raises(ValueError):
        run_case((ROOT, 1, policy, speed, horizon))
