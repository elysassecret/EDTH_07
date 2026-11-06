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
