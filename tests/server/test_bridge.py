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
    {"cmd": "fly"},
])
def test_bad_commands_are_rejected(msg):
    assert SimSource(1).command(msg)["ok"] is False


def test_stop_reaches_shore_node():
    s = SimSource(1)
    run_to(s, 60)
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
