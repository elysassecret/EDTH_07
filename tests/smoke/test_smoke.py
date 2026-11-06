"""Smoke: main must always pass this. Config, scene, a short run, snapshot shapes."""
from contract.config import load, load_scenario
from tests.helpers import make_sim
from world.routes import load_scene


def test_config_and_scene():
    cfg = load()
    assert cfg["_hash"]
    sc = load_scene(cfg)
    assert len(sc.segments) == 7, [s.task for s in sc.segments]
    total = sum(s.length_m for s in sc.segments)
    assert 23_000 < total < 24_500
    assert all(s.length_m <= cfg["scene"]["segment_max_m"] + 1 for s in sc.segments)
    assert 230 <= len(sc.samples) <= 250


def test_scenario_tape():
    ev = load_scenario()
    kinds = [e["kind"] for e in ev]
    for k in ("reset", "battery_low", "link_off", "contact_start", "contact_depart", "link_on", "evaluate"):
        assert k in kinds


def test_short_run_and_views():
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    assert sim.t == 0
    assert sim.warm_hash
    sim.run_until(120)
    tv = sim.truth_view()
    assert {b["id"] for b in tv["boats"]} == {1, 2, 3, 4, 5}
    assert set(tv["tasks"]) >= {"relay", "pick:N", "pick:S", "seg:H:0", "seg:G:0", "seg:M:0"}
    sv = sim.shore_view()
    assert "boats" in sv and "cards" in sv and "events" in sv
    assert m.km_overdue(sim.t) >= 0
    assert sim.radio.stats["oversize"] == 0


def test_initial_roles_two_two_one():
    sim, _ = make_sim("elysa", 1)
    roles = {b: (sorted(e[0] for e in a.tour), a.pick) for b, a in sim.agents.items()}
    assert roles[1][0] and all(t.startswith(("seg:G", "seg:M")) for t in roles[1][0])
    assert roles[2][0] and all(t.startswith("seg:H") for t in roles[2][0])
    assert roles[3] == ([], "pick:N") and roles[4] == ([], "pick:S")
    assert roles[5] == ([], None) and sim.agents[5].table["relay"].owner == 5
