"""Tests for the real-sim bridge (server/bridge.py). Owner: C."""

import asyncio
import json

import pytest

from contract.views import Snapshot
from server.bridge import SimSource
from server.feed import Feed


def run_to(s: SimSource, t_s: float, dt_ms: int = 24_000) -> None:
    while s.t < t_s:
        s.step(dt_ms)


def test_slow_warp_still_advances():
    s = SimSource(1)
    for _ in range(10):
        s.step(500)  # 5x warp at 10 Hz asks for half a tick per frame
    assert s.t == 5.0


def test_same_seed_same_frames():
    a, b = SimSource(2), SimSource(2)
    for _ in range(40):
        a.step(24_000)
        b.step(24_000)
        assert json.dumps(a.snapshot("shore")) == json.dumps(b.snapshot("shore"))
        assert json.dumps(a.snapshot("truth")) == json.dumps(b.snapshot("truth"))


def test_frames_match_contract_through_the_tape():
    s = SimSource(1)
    while s.t < 14_400:
        s.step(300_000)
        for ch in ("shore", "truth"):
            snap = Snapshot.model_validate(s.snapshot(ch))
            assert snap.view == ch


def test_shore_never_shows_truth_contacts():
    s = SimSource(1)
    run_to(s, 7_400)
    truth, shore = s.snapshot("truth"), s.snapshot("shore")
    assert any(c["track"] == "C-07" for c in truth["contacts"])
    assert "C-07" not in json.dumps(shore["events"])
    assert any(e["exercise"] and e["kind"] == "link_off" for e in shore["events"])


def test_switched_off_boat_stays_old_on_shore():
    s = SimSource(1)
    run_to(s, 120)
    assert s.command({"cmd": "inject", "kind": "boat_off", "a": 2})["ok"]
    run_to(s, 130)
    heard = next(b for b in s.snapshot("shore")["boats"] if b["id"] == 2)["last_heard"]
    run_to(s, 400)
    b2 = next(b for b in s.snapshot("shore")["boats"] if b["id"] == 2)
    assert b2["last_heard"] == heard and b2["link"] == "none"
    assert s.snapshot("shore")["events"][-1]["exercise"] is True


@pytest.mark.parametrize("msg", [
    {"cmd": "inject", "kind": "boom", "a": 1},
    {"cmd": "inject", "kind": "link_off", "a": 9, "b": "shore"},
    {"cmd": "inject", "kind": "link_off", "a": 1, "b": 9},
    {"cmd": "approve", "id": "no-colon"},
    {"cmd": "stop"},
    {"cmd": "stop", "id": "contact:unknown"},
    {"cmd": "stop", "id": "seg:G:0"},
    {"cmd": "fly"},
])
def test_bad_commands_are_rejected(msg):
    assert SimSource(1).command(msg)["ok"] is False


def test_stop_reaches_shore_node():
    s = SimSource(1)
    run_to(s, 8060)
    assert any(d["id"] == "contact:C-07" and d["state"] == "pending"
               for d in s.snapshot("shore")["decisions"])
    assert s.command({"cmd": "stop", "id": "contact:C-07"})["ok"]
    assert any(d["id"] == "contact:C-07" for d in s.snapshot("shore")["decisions"])


def test_feed_tick_with_sim():
    f = Feed(SimSource, seed=1, hz=10)
    frames = f.tick()
    assert set(frames) == {"shore", "truth"}
    assert f.handle_command({"cmd": "reset", "seed": 3})["ok"] and f.world.seed == 3
    assert f.handle_command({"cmd": "speed", "value": "nope"})["ok"] is False


def test_websocket_serves_sim():
    async def go():
        from websockets.asyncio.client import connect

        from server.bridge import serve

        ready = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(serve("127.0.0.1", 0, 1, hz=20, ready=ready))
        _, port = await asyncio.wait_for(ready, 10)
        try:
            async with connect(f"ws://127.0.0.1:{port}/shore") as ws:
                scene = json.loads(await ws.recv())
                assert scene["type"] == "scene" and scene["source"] == "sim"
                assert any(k.startswith("seg:H:") for k in scene["segments"])
                snap = json.loads(await ws.recv())
                assert snap["view"] == "shore" and snap["source"] == "sim"
        finally:
            task.cancel()

    asyncio.run(go())


def _shore_links(s: SimSource) -> dict[tuple[int, int], str]:
    return {(lk["a"], lk["b"]): lk["state"] for lk in s.snapshot("shore")["links"]}


def test_shore_link_down_only_if_once_direct_and_exercise_cut_is_crossed():
    s = SimSource(1)
    run_to(s, 7_400)
    links = _shore_links(s)
    never_direct = [b for b in s.world.mission.boats if b not in s.world.shore.direct]
    assert never_direct, "seed 1 has boats that only ever talk through a peer"
    assert not any((0, b) in links for b in never_direct)
    assert links[(0, 4)] == "cut"  # scripted link_off 4 -> shore at 7320 s
    run_to(s, 11_000)  # scripted link_on at 10 800 s
    assert _shore_links(s).get((0, 4)) != "cut"


def test_injected_boat_link_cut_is_crossed():
    s = SimSource(1)
    run_to(s, 60)
    assert s.command({"cmd": "inject", "kind": "link_off", "a": 3, "b": 2})["ok"]
    s.step(2_000)
    assert _shore_links(s)[(2, 3)] == "cut"
    assert s.command({"cmd": "inject", "kind": "link_on", "a": 3, "b": 2})["ok"]
    s.step(2_000)
    assert _shore_links(s).get((2, 3)) != "cut"


def test_scene_carries_revisit_target_from_run_config():
    import tomllib

    from server.feed import ROOT
    from server.mock_feed import MockWorld

    want = tomllib.loads((ROOT / "config" / "run.toml").read_text())["revisit_target_s"]
    assert SimSource(1).scene_msg()["revisit_target_s"] == want
    assert MockWorld(1).scene_msg()["revisit_target_s"] == want


def test_scene_carries_ring_ranges_from_boat_config():
    import tomllib

    from server.feed import ROOT
    from server.mock_feed import MockWorld

    boat = tomllib.loads((ROOT / "config" / "boat.toml").read_text())
    want = {"detect_ship_day_m": boat["r_detect_m"]["ship_day"], "keep_in_view_m": boat["keep_in_view_m"],
            "standoff_m": boat["standoff_m"]}
    assert SimSource(1).scene_msg()["ranges"] == want
    assert MockWorld(1).scene_msg()["ranges"] == want


def test_scene_carries_boat_model_from_boat_config():
    import tomllib

    from server.feed import ROOT
    from server.mock_feed import MockWorld

    boat = tomllib.loads((ROOT / "config" / "boat.toml").read_text())
    want = {"speed_mps": boat["speed_mps"], "endurance_s": boat["endurance_s"],
            "reserve_s": boat["reserve_s"]}
    assert SimSource(1).scene_msg()["boat_model"] == want
    assert MockWorld(1).scene_msg()["boat_model"] == want


@pytest.mark.parametrize("make", ["sim", "mock"])
def test_injection_works_for_any_boat_and_link(make):
    """BUILD_PLAN step 14: not only the scripted boats 01, 04 and 05."""
    from server.mock_feed import MockWorld

    s = SimSource(1) if make == "sim" else MockWorld(1)
    s.step(60_000)
    for msg in ({"cmd": "inject", "kind": "battery_low", "a": 3},
                {"cmd": "inject", "kind": "boat_off", "a": 2},
                {"cmd": "inject", "kind": "link_off", "a": 3, "b": 2},
                {"cmd": "inject", "kind": "link_off", "a": 2, "b": "shore"},
                {"cmd": "inject", "kind": "link_on", "a": 2, "b": "shore"}):
        assert s.command(msg)["ok"], msg
    assert s.command({"cmd": "inject", "kind": "link_off", "a": 3, "b": 3})["ok"] is False
    s.step(2_000)
    texts = [e["text"] for e in s.snapshot("shore")["events"] if e["exercise"]]
    assert any("03" in t for t in texts) and any("02" in t for t in texts)


def test_frames_say_who_sets_the_warp():
    f = Feed(SimSource, seed=1, hz=10)
    assert json.loads(f.tick()["shore"])["warp_mode"] == "auto"
    f.handle_command({"cmd": "speed", "value": 60})
    snap = json.loads(f.tick()["shore"])
    assert snap["warp_mode"] == "manual" and snap["near_event"] is False and snap["speed"] == 60
    f.handle_command({"cmd": "pause", "on": True})
    assert json.loads(f.tick()["truth"])["warp_mode"] == "paused"
    f.handle_command({"cmd": "speed", "value": "auto"})
    f.handle_command({"cmd": "pause", "on": False})
    f.world.step(7_190_000)  # just before the scripted battery_low at 7200 s
    snap = json.loads(f.tick()["shore"])
    assert snap["near_event"] is True and snap["speed"] == f.world.ui["warp_near_events"]


def test_issue_25_peer_cut_survives_shore_link_restore():
    """#25: cuts 1->4 and 4->1 at ~7081 s stay crossed after the script restores 4->shore."""
    s = SimSource(1)
    run_to(s, 7_081)
    for a, b in ((1, 4), (4, 1)):
        assert s.command({"cmd": "inject", "kind": "link_off", "a": a, "b": b})["ok"]
    run_to(s, 11_000)  # script: 4 -> shore cut at 7320 s, restored at 10 800 s
    links = _shore_links(s)
    assert links[(1, 4)] == "cut"
    assert links.get((0, 4)) != "cut"
    assert s.scene_msg()["home_m"] > 0


def test_place_contact_snaps_to_a_cable_sample_and_stays_truth_only(tmp_path):
    from server.replay import replay

    s = SimSource(1, runs_dir=tmp_path)
    run_to(s, 60)
    res = s.command({"cmd": "inject", "kind": "contact_start", "lat": 55.42, "lon": 10.95})
    assert res["ok"] and res["placed"] == "X-01" and res["on"].startswith("seg:")
    assert s.command({"cmd": "inject", "kind": "contact_start", "lat": 55.3,
                      "lon": 11.0, "ais": True})["placed"] == "X-02"
    s.step(2_000)  # applied at the next tick
    truth = {c["track"]: c for c in s.snapshot("truth")["contacts"]}
    assert {"X-01", "X-02"} <= set(truth) and truth["X-02"]["ais"] is True
    x, y = truth["X-01"]["x"], truth["X-01"]["y"]
    gap = min(((p.point[0] - x) ** 2 + (p.point[1] - y) ** 2) ** 0.5 for p in s.world.scene.samples)
    assert gap <= 5  # on a cable sample (lon/lat round trip and the first second of drift)
    # truth only: the shore may show it only once a boat has reported seeing it
    assert not any(c["track"] == "X-01" for c in s.snapshot("shore")["contacts"])
    run_to(s, 180)
    for c in s.snapshot("shore")["contacts"]:
        if c["track"] in ("X-01", "X-02"):
            assert c["seen_by"] or c["last_seen"] > 0
    s.close()
    assert replay(s.log.path).ok


def test_boat_restore_brings_the_same_boat_back_and_replays(tmp_path):
    """#63: off then restore; same boat, battery as it was; the alert clears; replay matches."""
    from server.replay import replay

    s = SimSource(1, runs_dir=tmp_path)
    run_to(s, 120)
    assert s.command({"cmd": "inject", "kind": "boat_off", "a": 2})["ok"]
    run_to(s, 400)
    off = next(b for b in s.snapshot("shore")["boats"] if b["id"] == 2)
    batt = next(b for b in s.world.truth_view()["boats"] if b["id"] == 2)["batt"]
    assert off["link"] == "none"
    assert any(a["text"].startswith("EXERCISE: USV 02 switched off")
               for a in s.snapshot("shore")["alerts"])
    assert s.command({"cmd": "inject", "kind": "boat_restore", "a": 2})["ok"]
    s.step(1_000)
    t2 = next(b for b in s.world.truth_view()["boats"] if b["id"] == 2)
    assert t2["enabled"] and t2["batt"] <= batt  # no recharge
    run_to(s, 520)
    shore = s.snapshot("shore")
    back = next(b for b in shore["boats"] if b["id"] == 2)
    assert back["last_heard"] > off["last_heard"]
    assert not any("USV 02 switched off" in a["text"] for a in shore["alerts"])
    assert any("USV 02 switched back on" in e["text"] for e in shore["events"])
    s.close()
    assert replay(s.log.path).ok


def test_scorecard_is_read_from_eval_output_on_truth_only(tmp_path):
    card = {"source": "eval/run_batch.py", "seeds": [1, 2], "preliminary": True,
            "rows": [{"mode": "elysa", "metric": "cable km overdue", "unit": "km",
                      "median": 1.0, "min": 0.5, "max": 2.0}]}
    path = tmp_path / "scorecard_console.json"
    f = Feed(lambda seed: SimSource(seed, scorecard_path=path), seed=1, hz=10)
    assert "scorecard" not in json.loads(f.tick()["truth"])  # no file yet: panel waits
    path.write_text(json.dumps(card))
    frames = {k: json.loads(v) for k, v in f.tick().items()}
    assert frames["truth"]["scorecard"] == card and "scorecard" not in frames["shore"]
    path.write_text("{broken")
    import os
    os.utime(path, (1, 1))  # force a new mtime
    assert "scorecard" not in json.loads(f.tick()["truth"])


def test_escalate_records_the_officers_report_only_for_a_shore_contact():
    src = SimSource(1)
    src.step(8100 * 1000)  # C-07 is in the shore picture by about 7865 s on seed 1
    shore = src.snapshot("shore")
    cid = next(c["id"] for c in shore["contacts"] if not c["ais"])
    text = "USV contact C-07 ... reported by the watch officer"
    assert src.command({"cmd": "escalate", "id": cid, "text": text, "note": "for a look"})["ok"]
    after = src.snapshot("shore")
    assert after["escalations"][0]["id"] == cid and after["escalations"][0]["note"] == "for a look"
    assert any(e["kind"] == "operator_command" and "escalated" in e["text"] for e in after["events"])
    assert not src.command({"cmd": "escalate", "id": "contact:NOPE", "text": text})["ok"]
    assert not src.command({"cmd": "escalate", "id": cid, "text": "  "})["ok"]
    assert not src.command({"cmd": "escalate", "id": cid, "text": "x" * 5000})["ok"]


def test_report_names_an_escalation_and_the_text_sent():
    from evidence.report import _line

    rec = {"kind": "command", "data": {"ok": True, "msg": {
        "cmd": "escalate", "id": "contact:C-07", "note": "", "text": "line one\nline two"}}}
    assert _line(rec) == ("Watch officer escalated contact:C-07 (recorded). "
                          "Report sent: line one / line two")
