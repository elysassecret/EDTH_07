"""Server robustness (release-gate P0): any command, however malformed, gets an answer, never
crashes the feed, and a refused command changes nothing. Every frame matches the contract.
Owner: C."""

import json
import math

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from contract.views import Snapshot
from server.bridge import SimSource
from server.feed import Feed

CMDS = ["approve", "decline", "confirm", "stop", "ack", "escalate", "inject", "speed", "pause",
        "reset", "nonsense", None, 7]
KINDS = ["battery_low", "boat_off", "boat_restore", "link_off", "link_on", "contact_start",
         "warp_drive", None, 3]
values = st.one_of(st.none(), st.booleans(), st.integers(-10**12, 10**12),
                   st.floats(allow_nan=True, allow_infinity=True), st.text(max_size=20),
                   st.lists(st.integers(), max_size=3), st.dictionaries(st.text(max_size=5),
                                                                        st.integers(), max_size=2))
commands = st.fixed_dictionaries(
    {"cmd": st.sampled_from(CMDS)},
    optional={"id": values, "kind": st.sampled_from(KINDS), "a": values, "b": values,
              "value": values, "on": values, "seed": values, "text": values, "note": values,
              "lat": values, "lon": values, "ais": values, "t": values},
)
FEED = Feed(lambda s: SimSource(s, launch=True, endless=True, scenario="scenarios/quiet.toml"), 1)
for _ in range(30):
    FEED.tick()


def state(f: Feed) -> str:
    shore = json.loads(f.tick()["shore"])
    for k in ("t", "speed", "warp", "t_exact", "narration", "boats", "links", "seg_age",
              "contacts", "alerts", "events"):
        shore.pop(k, None)  # these move with time; the rest is what a command could change
    return json.dumps(shore, sort_keys=True)


@settings(max_examples=300, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(commands)
def test_any_command_gets_an_answer_and_the_feed_keeps_running(msg):
    if msg["cmd"] == "reset" and not isinstance(msg.get("seed"), int):
        msg.pop("seed", None)  # a reset may change the run on purpose; tested below
    try:
        res = FEED.handle_command(msg)
    except Exception as e:
        raise AssertionError(f"{msg} raised {e!r}") from e
    assert isinstance(res, dict) and isinstance(res.get("ok"), bool)
    if not res["ok"]:
        assert isinstance(res.get("error"), str) and res["error"]
    frames = FEED.tick()  # and the next frame still renders on both channels
    for ch in ("shore", "truth"):
        json.loads(frames[ch])


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(commands)
def test_a_refused_command_changes_nothing(msg):
    if msg["cmd"] in ("reset", "pause", "speed"):
        return  # feed controls change the run by design
    f = Feed(lambda s: SimSource(s, launch=True, endless=True, scenario="scenarios/quiet.toml"), 1)
    f.handle_command({"cmd": "pause", "on": True})
    before = state(f)
    if not f.handle_command(msg)["ok"]:
        assert state(f) == before, msg


def test_speed_refuses_nonsense_values():
    f = FEED
    for bad in (0, -1, 0.2, 1000, math.nan, math.inf, "fast", [1]):
        assert not f.handle_command({"cmd": "speed", "value": bad})["ok"], bad


def test_every_frame_matches_the_contract_through_a_run_with_failures():
    f = Feed(lambda s: SimSource(s, launch=True, endless=True, scenario="scenarios/quiet.toml"), 1)
    f.handle_command({"cmd": "speed", "value": 240})
    script = {20: {"cmd": "inject", "kind": "battery_low", "a": 1},
              40: {"cmd": "inject", "kind": "link_off", "a": 2, "b": "shore"},
              60: {"cmd": "inject", "kind": "boat_off", "a": 3},
              80: {"cmd": "inject", "kind": "boat_restore", "a": 3}}
    for i in range(120):
        if i in script:
            f.handle_command(script[i])
        frames = f.tick()
        for ch in ("shore", "truth"):
            snap = json.loads(frames[ch])
            core = {k: snap[k] for k in Snapshot.model_fields if k in snap}
            Snapshot.model_validate(core)  # raises on any contract break


def test_restart_keeps_frames_flowing_while_the_new_run_is_built():
    """The demo preset's restart replays its first 6900 sim-seconds; frames must keep going out
    meanwhile, or every console shows FEED LOST."""
    import asyncio
    import time

    def slow_factory(seed):
        time.sleep(1.0)  # stands in for the demo fast-forward
        return SimSource(seed, launch=True, endless=True, scenario="scenarios/quiet.toml")

    f = Feed(lambda s: SimSource(s, launch=True, endless=True, scenario="scenarios/quiet.toml"), 1)
    f.factory = slow_factory

    async def go():
        frames = 0

        async def ticker():
            nonlocal frames
            while True:
                f.tick()
                frames += 1
                await asyncio.sleep(0.05)

        t = asyncio.create_task(ticker())
        res = await f.reset_async({"cmd": "reset", "seed": 2})
        again = await f.reset_async({"cmd": "reset", "seed": 2})
        t.cancel()
        return res, frames, again

    res, frames, _ = asyncio.run(go())
    assert res["ok"] and f.seed == 2
    assert frames >= 10  # about 20 frames went out during the 1 s build


def test_a_second_restart_while_one_is_building_is_refused():
    import asyncio
    import time

    f = Feed(lambda s: SimSource(s, launch=True, endless=True, scenario="scenarios/quiet.toml"), 1)
    f.factory = lambda s: (time.sleep(0.5), SimSource(s, launch=True, endless=True,
                                                       scenario="scenarios/quiet.toml"))[1]

    async def go():
        first = asyncio.create_task(f.reset_async({"cmd": "reset", "seed": 1}))
        await asyncio.sleep(0.1)
        second = await f.reset_async({"cmd": "reset", "seed": 1})
        return await first, second

    first, second = asyncio.run(go())
    assert first["ok"] and not second["ok"] and "already" in second["error"]
