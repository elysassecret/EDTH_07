"""Replay timeline: the feed records the shore picture as the run goes (owner C)."""

import json
from itertools import pairwise

from server.bridge import SimSource
from server.feed import RECORD_EVERY_S, Feed


def test_the_feed_records_the_shore_picture_and_serves_the_frame_at_a_time():
    feed = Feed(lambda s: SimSource(s, launch=True, endless=True, scenario="scenarios/quiet.toml"), 1)
    feed.handle_command({"cmd": "speed", "value": 240})
    for _ in range(40):
        feed.tick()  # 40 frames at 240x, 10 Hz: 16 sim minutes
    span = feed.history.span()
    assert span["from"] == 0 and span["to"] >= RECORD_EVERY_S and span["every_s"] == RECORD_EVERY_S
    frames = feed.history.times
    assert all(b - a >= RECORD_EVERY_S for a, b in pairwise(frames))
    mid = frames[len(frames) // 2]
    snap = json.loads(feed.history.at(mid + RECORD_EVERY_S / 2))
    assert snap["t"] == mid and snap["view"] == "shore"
    assert json.loads(feed.history.at(-5))["t"] == frames[0]  # before the start: the first frame


def test_a_reset_starts_a_new_recording():
    feed = Feed(lambda s: SimSource(s, launch=True, endless=True, scenario="scenarios/quiet.toml"), 1)
    feed.handle_command({"cmd": "speed", "value": 240})
    for _ in range(20):
        feed.tick()
    assert feed.history.span()["frames"] > 1
    feed.handle_command({"cmd": "reset", "seed": 1})
    assert feed.history.span()["frames"] == 1  # just the new run's first state
