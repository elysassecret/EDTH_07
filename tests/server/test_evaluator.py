"""Evaluator comparison on /truth (shore belief next to truth). Owner: C."""

import json

import pytest

from server.bridge import SimSource
from server.evaluator import compare
from server.feed import Feed
from server.mock_feed import MockWorld


@pytest.mark.parametrize("source", [SimSource, MockWorld])
def test_only_truth_frames_carry_eval(source):
    f = Feed(source, seed=1, hz=10)
    for _ in range(3):
        frames = {ch: json.loads(fr) for ch, fr in f.tick().items()}
        assert "eval" not in frames["shore"]
        ev = frames["truth"]["eval"]
        assert ev["t"] == frames["truth"]["t"]
        assert {b["id"] for b in ev["boats"]} == {b["id"] for b in frames["truth"]["boats"]}


def test_real_sim_shows_what_the_shore_does_not_know():
    f = Feed(SimSource, seed=1, hz=10)
    f.world.step(7_400_000)  # C-07 placed at 7320 s (truth only)
    assert f.world.command({"cmd": "inject", "kind": "boat_off", "a": 2})["ok"]
    f.world.step(300_000)
    ev = json.loads(f.tick()["truth"])["eval"]
    c07 = next(c for c in ev["contacts"] if c["track"] == "C-07")
    assert c07["on_shore"] is False and c07["ais"] is False
    b2 = next(b for b in ev["boats"] if b["id"] == 2)
    assert b2["shore_age_s"] > 60  # switched off: the shore keeps its last report
    assert b2["shore"] is not None and b2["true"] is not None
    assert set(ev["seg_age"]) == {k for k in json.loads(f.tick()["shore"])["seg_age"]}


def test_compare_flags_link_and_position_differences():
    boat = {"id": 4, "x": 0, "y": 0, "lon": 11.0, "lat": 55.4, "link": "none", "mode": "PATROL",
            "last_heard": 100}
    truth = {"t": 200, "boats": [{**boat, "x": 300, "y": 400, "link": "peer"}],
             "contacts": [{"id": "contact:C-07", "track": "C-07", "lon": 10.9, "lat": 55.45,
                           "ais": False}],
             "links": [{"a": 4, "b": 0, "state": "cut"}, {"a": 4, "b": 5, "state": "up"}],
             "seg_age": {"seg:G:0": 50}}
    shore = {"t": 200, "boats": [boat], "contacts": [],
             "links": [{"a": 0, "b": 4, "state": "up"}],
             "seg_age": {"seg:G:0": 10, "seg:M:0": 200}}
    ev = compare(shore, truth)
    assert ev["boats"][0]["offset_m"] == 500 and ev["boats"][0]["shore_age_s"] == 100
    assert ev["links"] == [{"a": 0, "b": 4, "true": "cut", "shore": "up"},
                           {"a": 4, "b": 5, "true": "up", "shore": "not reported"}]
    assert ev["seg_age"] == {"seg:G:0": {"shore": 10, "true": 50},
                             "seg:M:0": {"shore": 200, "true": None}}
    assert ev["contacts"][0]["on_shore"] is False


def test_agents_never_import_the_evaluator():
    """N10: agents see only their own sensors and inbox; nothing in agent/ imports server/."""

    from server.feed import ROOT

    for p in sorted((ROOT / "agent").rglob("*.py")):
        text = p.read_text(encoding="utf-8")
        assert "import server" not in text and "from server" not in text, p


def test_true_cable_km_overdue_uses_real_sample_lengths():
    s = SimSource(1)
    c0 = s.cable_overdue()
    # boats start on their cables, so a little is visited at t = 0; nothing is overdue yet
    assert 0 < c0["never_visited_km"] < c0["total_km"] and c0["overdue_km"] == 0
    assert abs(c0["total_km"] - sum(s._sample_m) / 1000) < 0.01
    while s.t < 14_000:
        s.step(120_000)
    c = s.cable_overdue()
    assert c["target_s"] == s.revisit_target_s
    assert 0 <= c["overdue_km"] + c["never_visited_km"] <= c["total_km"]
    f = Feed(SimSource, seed=1, hz=10)
    ev = json.loads(f.tick()["truth"])["eval"]
    assert ev["cable_overdue"]["total_km"] == c["total_km"]
    assert json.loads(Feed(MockWorld, 1).tick()["truth"])["eval"]["cable_overdue"] is None


def test_scorecard_hook_passes_through_on_truth_only():
    class WithCard(MockWorld):
        def scorecard(self):
            return {"source": "test", "seeds": [1], "rows": []}

    f = Feed(WithCard, seed=1, hz=10)
    frames = {k: json.loads(v) for k, v in f.tick().items()}
    assert frames["truth"]["scorecard"]["source"] == "test"
    assert "scorecard" not in frames["shore"]
