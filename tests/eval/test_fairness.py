"""F1 to F4 on real worlds: the three modes share inputs and differ by one key. Slow."""
from dataclasses import asdict
from pathlib import Path

import pytest

from eval.metrics import Metrics
from eval.report import fairness
from eval.run_batch import POLICIES as MODES
from eval.run_batch import run_config
from eval.warm import build_world, warm_up

ROOT = Path(__file__).resolve().parents[2]
AFTER_T_MS = 400_000
pytestmark = pytest.mark.slow


def run(mode: str, seed: int = 2) -> dict:
    world = build_world(ROOT, mode, seed)
    warm_hash = warm_up(world)
    metrics = Metrics(world, run_config(ROOT)["revisit_target_s"], t0_ms=world.warm_ms)
    while world.next_tick_ms <= metrics.T + AFTER_T_MS:
        world.step()
        metrics.on_tick()
    return {
        **metrics.scorecard(),
        "warm_hash": warm_hash,
        "params": asdict(world.final_params),
    }


@pytest.fixture(scope="module")
def cards():
    return {m: run(m) for m in MODES}


def failed(cards, name):
    return [c for c in fairness(list(cards.values())) if c["check"] == name and not c["ok"]]


def test_f1_warm_hash_equal_in_every_mode(cards):
    assert not failed(cards, "F1")


def test_f2_ages_and_physics_at_t_minus_1_equal_off_vs_elysa(cards):
    assert cards["off"]["ages_hash_T1"] is not None
    assert not failed(cards, "F2")


def test_f3_off_claims_nothing_after_t_and_elysa_does(cards):
    assert cards["off"]["repair_claims_after_T"] == 0
    assert cards["elysa"]["claims_after_T"].get("seg", 0) >= 1
    assert not failed(cards, "F3")


def test_f4_modes_differ_by_policy_only(cards):
    assert not failed(cards, "F4")
    assert {c["params"]["policy"] for c in cards.values()} == set(MODES)


def test_warm_up_varies_with_the_seed():
    a, b = (warm_up(build_world(ROOT, "off", s, warm_s=60)) for s in (1, 2))
    assert a != b
