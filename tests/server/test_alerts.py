"""Tests for console alerts (server/alerts.py, feature 23). Owner: C."""

from contract.views import Boat, Decision, Snapshot, TaskView
from server.alerts import ALARM_AFTER_S, AlertBook
from server.bridge import SimSource


def run_to(s: SimSource, t_s: float, dt_ms: int = 24_000) -> None:
    while s.t < t_s:
        s.step(dt_ms)


def pic(t: int, boats=(), tasks=None, decisions=()) -> Snapshot:
    return Snapshot(view="shore", t=t, speed=1, boats=list(boats), tasks=tasks or {},
                    seg_age={}, links=[], contacts=[], decisions=list(decisions), alerts=[],
                    events=[])


def boat(i: int, last_heard: int, link="direct", mode="PATROL") -> Boat:
    return Boat(id=i, x=0, y=0, lon=11.0, lat=55.4, mode=mode, batt=900, endurance_s=1,
                link=link, tour=[], roles=[], last_heard=last_heard)


def ids(book: AlertBook) -> dict[str, str]:
    return {a.id: a.level for a in book.alerts()}


def test_stale_boat_is_a_warning_and_clears_when_heard_again():
    book = AlertBook(stale_after_s=60, t0_utc="2026-11-03T10:15:00Z")
    book.update(pic(100, [boat(2, 50)]), [], set())
    assert "stale:2" not in ids(book)
    book.update(pic(200, [boat(2, 50, link="none")]), [], set())
    assert ids(book) == {"stale:2": "warning", "nolink:2": "caution"}
    assert "10:15Z" in next(a.text for a in book.alerts() if a.id == "stale:2")
    book.update(pic(210, [boat(2, 209)]), [], set())
    assert ids(book) == {}


def test_dedup_keeps_first_time_and_ack():
    book = AlertBook(60)
    book.update(pic(10, [boat(1, 10, mode="RETURNING")]), [], set())
    assert book.ack("rtb:1")
    book.update(pic(20, [boat(1, 20, mode="RETURNING")]), [], set())
    [a] = book.alerts()
    assert (a.id, a.t, a.ack, a.level) == ("rtb:1", 10, True, "caution")
    assert book.ack("nope") is False


def test_picket_uncovered_only_after_it_was_held():
    book = AlertBook(60)
    book.update(pic(0, tasks={"pick:S": TaskView(v=0, owner=0, deputy=0, state=0)}), [], set())
    assert ids(book) == {}
    book.update(pic(5, tasks={"pick:S": TaskView(v=1, owner=4, deputy=0, state=1)}), [], set())
    book.update(pic(9, tasks={"pick:S": TaskView(v=2, owner=4, deputy=0, state=0)}), [], set())
    assert ids(book) == {"picket:pick:S": "caution"}


def test_held_decision_escalates_to_alarm_and_needs_new_ack():
    book = AlertBook(60)
    d = Decision(id="close:contact:C-07", task="contact:C-07", dec="close", text="Close to 500 m",
                 state="pending", t=100, tier="held")
    book.update(pic(150, decisions=[d]), [], set())
    assert ids(book) == {"decision:close:contact:C-07": "warning"}
    book.ack("decision:close:contact:C-07")
    book.update(pic(100 + ALARM_AFTER_S, decisions=[d]), [], set())
    [a] = book.alerts()
    assert a.level == "alarm" and a.ack is False and a.text.startswith("Unanswered 05:00")
    delegated = d.model_copy(update={"tier": "delegated"})
    book.update(pic(500, decisions=[delegated]), [], set())
    assert ids(book) == {}


def test_exercise_alert_goes_on_ack_or_restore():
    book = AlertBook(60)
    ex = [{"kind": "link_off", "text": "EXERCISE: cut", "pair": (0, 4)},
          {"kind": "boat_off", "text": "EXERCISE: off", "pair": None}]
    book.update(pic(10), ex, {(0, 4)})
    assert ids(book) == {"exercise:0": "caution", "exercise:1": "caution"}
    assert book.ack("exercise:1")
    book.update(pic(11), ex, {(0, 4)})
    assert ids(book) == {"exercise:0": "caution"}
    book.update(pic(12), ex, set())  # link restored
    assert ids(book) == {}


def test_sim_alerts_through_the_tape():
    s = SimSource(1)
    run_to(s, 7_400)
    alerts = {a["id"]: a for a in s.snapshot("shore")["alerts"]}
    assert alerts["rtb:1"]["level"] == "caution"  # scripted battery_low at 7200 s
    assert alerts["picket:pick:S"]["level"] == "caution"  # 04 took the cable tasks
    assert any(a["text"].startswith("EXERCISE") for a in alerts.values())
    assert s.command({"cmd": "ack", "id": "rtb:1"})["ok"]
    assert next(a for a in s.snapshot("shore")["alerts"] if a["id"] == "rtb:1")["ack"] is True
    assert s.command({"cmd": "ack", "id": "nope"})["ok"] is False
    assert s.snapshot("truth")["alerts"] == s.snapshot("shore")["alerts"]


def test_picket_says_since_when_and_keeps_that_time():
    book = AlertBook(60, t0_utc="2026-11-03T10:15:00Z")
    open_s = {"pick:S": TaskView(v=2, owner=4, deputy=0, state=0)}
    book.update(pic(3600, tasks=open_s), [], set())
    book.update(pic(4000, tasks=open_s), [], set())
    [a] = book.alerts()
    assert a.text == "Lane picket S uncovered since 11:15Z" and a.t == 3600


def test_overdue_cable_segments_use_the_shore_age():
    book = AlertBook(60, t0_utc="2026-11-03T10:15:00Z", revisit_target_s=1000)
    snap = pic(5000).model_copy(update={"seg_age": {"seg:G:0": 999, "seg:G:1": 1800,
                                                    "seg:M:0": 5000}})
    book.update(snap, [], set())
    texts = {a.id: a.text for a in book.alerts()}
    assert "overdue:seg:G:0" not in texts
    assert texts["overdue:seg:G:1"] == "Cable seg:G:1 overdue: no visit since 11:08Z (shore-reported)"
    assert texts["overdue:seg:M:0"] == "Cable seg:M:0: no visit reported since start (shore-reported)"
    assert AlertBook(60).revisit_target_s is None  # no target: no overdue alerts
