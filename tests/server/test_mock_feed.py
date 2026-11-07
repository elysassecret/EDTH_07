"""Tests for the console's mock feed. Owner: C."""

import asyncio
import json

import pytest

from contract.views import Snapshot
from server.mock_feed import MODES, MockWorld, load_scene, serve


@pytest.fixture(scope="module")
def scene():
    return load_scene()


def run_to(w: MockWorld, t_s: float) -> None:
    while w.t < t_s:
        w.step(w.speed() * 100)


def test_scene_has_six_segments(scene):
    assert sorted(scene.segments) == [
        "seg:G:0", "seg:G:1", "seg:G:2", "seg:H:0", "seg:H:1", "seg:M:0"]


def test_same_seed_same_snapshots(scene):
    a, b = MockWorld(3, scene), MockWorld(3, scene)
    for _ in range(300):
        a.step(24_000)
        b.step(24_000)
        assert json.dumps(a.snapshot("truth")) == json.dumps(b.snapshot("truth"))


def test_snapshot_shape(scene):
    w = MockWorld(1, scene)
    w.step(1000)
    s = w.snapshot("shore")
    for k in ("type", "t", "speed", "boats", "tasks", "seg_age", "links", "contacts",
              "decisions", "alerts", "events"):
        assert k in s
    assert s["type"] == "snapshot" and s["source"] == "mock" and s["view"] == "shore"
    assert [b["id"] for b in s["boats"]] == [1, 2, 3, 4, 5]
    for b in s["boats"]:
        assert b["mode"] in MODES
        for k in ("hdg", "sog_kn", "role_text"):  # console extras
            assert k in b
    json.dumps(s)  # serialisable


def test_snapshots_match_frozen_contract(scene):
    """Every snapshot along the whole tape validates against contract/views.py."""
    w = MockWorld(1, scene)
    while w.t < 14400:
        w.step(60_000)
        for ch in ("shore", "truth"):
            Snapshot.model_validate(w.snapshot(ch))


def test_story_runs_and_dark_contact_appears(scene):
    w = MockWorld(1, scene)
    run_to(w, 7000)
    assert not any(not c["ais"] for c in w.snapshot("shore")["contacts"])
    run_to(w, 7700)
    shore = w.snapshot("shore")
    dark = [c for c in shore["contacts"] if not c["ais"]]
    assert len(dark) == 1 and dark[0]["source"] == "camera" and dark[0]["id"] == "contact:C-07"
    b1 = next(b for b in shore["boats"] if b["id"] == 1)
    assert b1["mode"] == "RETURNING"
    assert shore["tasks"]["pick:S"]["state"] == 0  # picket S left uncovered
    assert any(d["dec"] == "keep" and d["state"] == "pending" for d in shore["decisions"])


def test_truth_sees_contact_before_shore(scene):
    w = MockWorld(1, scene)
    run_to(w, 7330)
    truth = w.snapshot("truth")
    c07 = [c for c in truth["contacts"] if c["track"] == "C-07"]
    assert c07 and c07[0]["last_seen"] == 0
    assert not any(c["track"] == "C-07" for c in w.snapshot("shore")["contacts"])


def test_commands(scene):
    w = MockWorld(1, scene)
    run_to(w, 7900)
    held = next(d for d in w.decisions.values() if d["kind"] == "close_look")
    assert held["status"] == "waiting"
    assert not w.command({"cmd": "confirm", "id": held["id"]})["ok"]  # wrong button
    assert w.command({"cmd": "approve", "id": held["id"]})["ok"]
    assert held["status"] == "approved"
    assert not w.command({"cmd": "approve", "id": held["id"]})["ok"]  # already answered
    assert not w.command({"cmd": "approve", "id": "D-999"})["ok"]
    assert not w.command({"cmd": "fly"})["ok"]


def test_inject_link_and_boat_off(scene):
    w = MockWorld(1, scene)
    w.step(1000)
    assert w.command({"cmd": "inject", "kind": "link_off", "a": 5, "b": "shore"})["ok"]
    w.step(1000)
    s = w.snapshot("shore")
    assert any(lk["a"] == 0 and lk["b"] == 5 and lk["state"] == "cut" for lk in s["links"])
    assert s["events"][-1]["exercise"] is True
    assert w.command({"cmd": "inject", "kind": "boat_off", "a": 2})["ok"]
    heard = w.snapshot("shore")["boats"][1]["last_heard"]
    run_to(w, 200)
    b2 = w.snapshot("shore")["boats"][1]
    assert b2["link"] == "none" and b2["last_heard"] == heard  # frozen, not shown as live
    assert not w.command({"cmd": "inject", "kind": "boat_off", "a": 9})["ok"]


def test_websocket_roundtrip():
    async def go():
        from websockets.asyncio.client import connect

        loop = asyncio.get_running_loop()
        ready = loop.create_future()
        task = asyncio.create_task(serve("127.0.0.1", 0, 1, hz=20, ready=ready))
        _, port = await asyncio.wait_for(ready, 10)
        try:
            async with connect(f"ws://127.0.0.1:{port}/shore") as ws:
                first = json.loads(await ws.recv())
                assert first["type"] == "scene"
                snap = json.loads(await ws.recv())
                assert snap["type"] == "snapshot" and snap["view"] == "shore"
                await ws.send(json.dumps({"cmd": "inject", "kind": "link_off", "a": 4,
                                          "b": "shore"}))
                await ws.send("not json")
                acks = []
                while len(acks) < 2:
                    m = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    if m["type"] == "ack":
                        acks.append(m)
                assert acks[0]["ok"] is True and acks[1]["ok"] is False
            async with connect(f"ws://127.0.0.1:{port}/truth") as ws:
                await ws.recv()
                assert json.loads(await ws.recv())["view"] == "truth"
        finally:
            task.cancel()

    asyncio.run(go())


def test_load_test_tracks_are_extra_and_leave_the_story_alone():
    """G4: --tracks 240 adds synthetic AIS-like tracks; the default 6-track story is unchanged."""
    import json as _json

    from server.mock_feed import MockWorld

    a, b = MockWorld(1), MockWorld(1, tracks=240)
    for _ in range(20):
        a.step(24_000)
        b.step(24_000)
    ta, tb = a.snapshot("truth"), b.snapshot("truth")
    assert len([c for c in tb["contacts"] if c["ais"]]) == 240
    assert _json.dumps(ta["boats"]) == _json.dumps(tb["boats"])
    assert all(c["track"].startswith("AIS-") for c in tb["contacts"] if c["ais"])
