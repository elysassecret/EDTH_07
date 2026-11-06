"""Projection, parameter loading and the exported schema."""
from contract.export import PATH, schema_text
from contract.geo import dist, to_lonlat, to_xy
from contract.mission import load_params
from contract.views import Contract, Snapshot


def test_projection_matches_scene():
    korsor = to_xy(55.3316, 11.1303)
    relay = to_xy(55.405, 10.975)
    assert korsor == (8237, -7605)
    assert 12_700 < dist(korsor, relay) < 12_850  # docs: relay 12.8 km from the mast
    lon, lat = to_lonlat(*korsor)
    assert abs(lon - 11.1303) < 1e-4 and abs(lat - 55.3316) < 1e-4


def test_params_from_repo_config():
    p = load_params()
    assert p.speed_mm_s == 2300 and p.endurance_ms == 25_200_000
    assert p.policy == "elysa"
    assert p.repair_off_after_ms == 7_200_000  # first failure event in scenarios/fixed.toml
    assert p.return_safety_permille == 1200 and p.rebalance_ratio_permille == 1250


def test_schema_json_is_up_to_date():
    assert PATH.read_text() == schema_text(), "run: uv run python -m contract.export"


def test_docstring_example_and_commands_validate():
    s = Snapshot.model_validate({
        "view": "shore", "t": 0, "speed": 240,
        "boats": [{"id": 1, "x": 0, "y": 0, "lon": 11.0, "lat": 55.4, "mode": "PATROL",
                   "batt": 1000, "endurance_s": 25200, "must_return_by": 14140,
                   "link": "direct", "tour": ["seg:G:0"], "roles": ["seg:G:0"],
                   "last_heard": 0}],
        "tasks": {"seg:G:0": {"v": 1, "owner": 1, "deputy": 0, "state": 1}},
        "seg_age": {}, "links": [], "contacts": [], "decisions": [], "alerts": [],
        "events": []})
    assert s.schema_version == 1
    stop = Contract.model_validate({"snapshot": s.model_dump(), "command": {"cmd": "stop",
                                                                         "id": "contact:C-07"}})
    assert stop.command.cmd == "stop"
    inject = Contract.model_validate({"snapshot": s.model_dump(), "command": {
        "cmd": "inject", "kind": "link_off", "a": 4, "b": "shore"}})
    assert inject.command.b == "shore"


def test_console_fields_from_issue_7():
    s = Snapshot.model_validate({
        "view": "truth", "t": 7500, "speed": 5, "seg_age": {}, "tasks": {}, "links": [],
        "alerts": [], "events": [{"t": 7200, "kind": "battery_low", "text": "USV 01 low",
                                  "exercise": True}],
        "boats": [{"id": 3, "x": 1, "y": 2, "lon": 10.9, "lat": 55.45, "mode": "SHADOWING",
                   "batt": 800, "endurance_s": 20000, "link": "peer", "tour": [], "roles": [],
                   "last_heard": 7490, "hdg": 270, "sog": 2300, "via": 5}],
        "contacts": [{"id": "contact:C-07", "track": "C-07", "x": 0, "y": 0, "lon": 10.87,
                      "lat": 55.45, "sog": 200, "cog": 0, "ais": False, "first_seen": 7400,
                      "last_seen": 7499, "seen_by": [2, 3], "watcher": 3, "state": 1,
                      "flags": {"dwell": True}, "source": "camera",
                      "trail": [[10.87, 55.45], [10.871, 55.45]]}],
        "decisions": [{"id": "close:contact:C-07", "task": "contact:C-07", "dec": "close",
                       "text": "Close to 500 m, photograph both bows", "state": "pending",
                       "t": 7500, "tier": "held", "actions": ["approve", "decline"], "boat": 3,
                       "route": [[10.88, 55.45], [10.871, 55.45]]}]})
    assert s.t0_utc.endswith("Z") and s.boats[0].via == 5 and s.contacts[0].source == "camera"
    old = Snapshot.model_validate({"view": "shore", "t": 0, "speed": 1, "boats": [], "tasks": {},
                                   "seg_age": {}, "links": [], "contacts": [], "decisions": [],
                                   "alerts": [], "events": []})
    assert old.t0_utc == "2026-11-03T10:15:00Z"  # optional fields keep old producers valid
    ack = Contract.model_validate({"snapshot": old.model_dump(),
                                   "command": {"cmd": "ack", "id": "A-1"}})
    assert ack.command.cmd == "ack"
