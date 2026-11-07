"""Stepless warp 0.25x-999x and the batch frames API for replay playback (owner C)."""

import json
from itertools import pairwise

from server.bridge import SimSource
from server.feed import Feed


def feed():
    return Feed(lambda s: SimSource(s, launch=True, endless=True, scenario="scenarios/quiet.toml"), 1)


def test_any_speed_from_a_quarter_to_999_is_taken_and_steps_the_sim_by_it():
    f = feed()
    for v in (0.25, 1.5, 999):
        assert f.handle_command({"cmd": "speed", "value": v})["ok"]
        snap = json.loads(f.tick()["shore"])
        assert snap["warp"] == v and snap["warp_set"] == v
        assert snap["speed"] == max(1, round(v))  # contract: a whole number, 0 only when paused
    for bad in (0.1, 1000, "x", float("nan")):
        assert not f.handle_command({"cmd": "speed", "value": bad})["ok"]
    f.handle_command({"cmd": "speed", "value": 0.25})
    t = f.world.t
    for _ in range(40):  # 4 s of real time at 10 Hz
        f.tick()
    assert abs(f.world.t - t - 1.0) <= 1.0  # a quarter speed: about one sim second


def test_frames_between_two_times_for_playback_and_event_marks():
    f = feed()
    f.handle_command({"cmd": "speed", "value": 240})
    for _ in range(30):
        f.tick()
    frames = json.loads(f.history.between(0, 300))
    assert frames[0]["t"] == 0 and all(a["t"] < b["t"] for a, b in pairwise(frames))
    assert frames[-1]["t"] <= 300
    marks = f.history.span()["marks"]
    assert any("switched on at Korsør" in m["text"] for m in marks)
