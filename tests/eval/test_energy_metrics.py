"""#109: reserve violations, unserved work and recovery outcome, on the real scene. Owner: D."""
from pathlib import Path

from eval.metrics import HOME_M, Metrics
from eval.report import OUTCOMES, outcome_text, summary, table
from eval.warm import build_world, warm_up

ROOT = Path(__file__).resolve().parents[2]


def started():
    world = build_world(ROOT, "elysa", 1, warm_s=60)
    warm_up(world)
    metrics = Metrics(world, 12_000, t0_ms=world.warm_ms)
    world.step()
    metrics.on_tick()
    return world, metrics


def test_reserve_violation_counts_only_an_enabled_boat_at_sea_under_reserve():
    world, m = started()
    boat = world.boats[1]
    assert m.reserve_viol_ms == {}  # a fresh fleet is full
    boat.charge_ms = m.reserve_ms - 1
    m._reserve()
    assert m.reserve_viol_ms == {1: world.tick_ms}
    assert m.stranded == set()
    boat.enabled = False  # switched off by the tape: a failure, not an energy decision
    m._reserve()
    assert m.reserve_viol_ms == {1: world.tick_ms}
    boat.enabled = True
    sx, sy = world.mission.shore
    boat.x_mm, boat.y_mm = (sx + HOME_M // 2) * 1000, sy * 1000  # at the station
    m._reserve()
    assert m.reserve_viol_ms == {1: world.tick_ms}
    boat.x_mm += 10 * HOME_M * 1000
    boat.charge_ms = 0
    m._reserve()
    assert m.reserve_viol_ms == {1: 2 * world.tick_ms}
    assert m.stranded == {1}


def test_unserved_work_and_recovery_follow_live_owners():
    world, m = started()
    live = m.live()
    assert m.recovery(live) == ("all tasks", [])  # warm fleet: every fixed task is owned
    m._unserved(live)
    assert m.unserved_ms == {}
    picket = next(t for t in m.tasks if t.startswith("pick"))
    seg = next(t for t in m.tasks if t.startswith("seg"))
    owner = next(b for b in live if world.nodes[b].table.recs[picket].owner == b)
    without = [b for b in live if b != owner]
    outcome, unowned = m.recovery(without)
    assert picket in unowned
    assert outcome == ("not recovered" if any(u.startswith("seg") for u in unowned)
                       else "cables only")
    m._unserved(without)
    assert m.unserved_ms["pick"] >= world.tick_ms
    assert m.recovery([]) == ("not recovered", m.tasks)
    assert seg in m.recovery([])[1]


def test_scorecard_and_summary_carry_the_three_metrics_with_seeds():
    _, m = started()
    card = m.scorecard()
    for key in ("reserve_violation_s", "reserve_violation_boats", "stranded_boats",
                "unserved_task_s_post_T", "unserved_s_by_kind", "recovery_outcome",
                "unowned_at_end"):
        assert key in card
    assert card["recovery_outcome"] in OUTCOMES
    cards = [{**card, "seed": s, "mode": mode, "contacts": [], "warm_hash": "w",
              "params": {"policy": mode}, "gap": {"ok": True, "max_hidden_s": 0}}
             for s in (1, 2) for mode in ("off", "elysa")]  # run_batch adds hash and params
    out = summary(cards, source="test")
    assert out["source"] == "test" and out["label"] == "truth" and out["seeds"] == [1, 2]
    elysa = out["modes"]["elysa"]
    assert elysa["seeds"] == [1, 2]
    assert sum(elysa["recovery_outcome"].values()) == 2
    assert elysa["metrics"]["reserve_violation_s"]["of"] == 2
    assert "Recovery outcome at end" in table(cards)
    assert outcome_text(cards[:1]) == f"{card['recovery_outcome']} 1"


def test_warm_up_tide_shift_survives_reset():
    """#113 made reset() restore the current from `_base_current`; the warm shift must hold."""
    cold = build_world(ROOT, "elysa", 1, warm_s=0)
    warm = build_world(ROOT, "elysa", 1, warm_s=60)
    assert warm.current.flip_ms == cold.current.flip_ms + 60_000
    warm.reset()
    assert warm.current.flip_ms == cold.current.flip_ms + 60_000
