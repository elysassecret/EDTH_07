"""Exercise conditions in effect, and undoing them with ordinary inject commands (owner C)."""

from server.bridge import SimSource


def run_to(s: SimSource, t_s: float, dt_ms: int = 24_000) -> None:
    while s.t < t_s:
        s.step(dt_ms)


def kinds(s: SimSource) -> list[tuple[str, str]]:
    return [(i["kind"], i["origin"]) for i in s.snapshot("shore")["exercises"]]


def test_injections_are_listed_until_undone_by_their_own_commands():
    s = SimSource(1)
    run_to(s, 120)
    assert s.snapshot("shore")["exercises"] == []
    assert s.command({"cmd": "inject", "kind": "boat_off", "a": 2})["ok"]
    assert s.command({"cmd": "inject", "kind": "link_off", "a": 3, "b": "shore"})["ok"]
    assert s.command({"cmd": "inject", "kind": "battery_low", "a": 4})["ok"]
    run_to(s, 150)
    items = s.snapshot("shore")["exercises"]
    assert sorted(i["kind"] for i in items) == ["battery_low", "boat_off", "link_off"]
    assert all(i["origin"] == "operator injection" for i in items)
    batt = next(i for i in items if i["kind"] == "battery_low")
    assert batt["undo"] is None  # no recharge in the world (#116)
    for item in items:
        for cmd in item["undo"] or []:
            assert s.command(cmd)["ok"]
    run_to(s, 180)
    assert kinds(s) == [("battery_low", "operator injection")]
    # the undo is an ordinary, logged exercise injection: the timeline says so
    texts = [e["text"] for e in s.snapshot("shore")["events"] if e["exercise"]]
    assert any("switched back on" in t for t in texts)
    assert any("Link USV 03 → shore restored" in t for t in texts)


def test_a_one_way_restore_leaves_the_other_direction_listed():
    s = SimSource(1)
    run_to(s, 120)
    for a, b in ((1, 2), (2, 1)):
        assert s.command({"cmd": "inject", "kind": "link_off", "a": a, "b": b})["ok"]
    run_to(s, 150)
    assert s.command({"cmd": "inject", "kind": "link_on", "a": 1, "b": 2})["ok"]
    run_to(s, 180)
    (left,) = s.snapshot("shore")["exercises"]
    assert left["undo"] == [{"cmd": "inject", "kind": "link_on", "a": 2, "b": 1}]
    assert "exercises" in s.snapshot("truth")
