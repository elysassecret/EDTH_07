"""Narrator: plain lines from consecutive /shore frames only. Owner: C."""

import json
import tomllib

from server.bridge import SimSource
from server.feed import ROOT, Feed
from server.narrator import Narrator


def frame(t, tasks=None, boats=()):
    return {"t": t, "tasks": {k: {"owner": o, "state": s} for k, (o, s) in (tasks or {}).items()},
            "boats": list(boats)}


def boat(i, last_heard, mode="PATROL", link="direct", via=0, roles=()):
    return {"id": i, "last_heard": last_heard, "mode": mode, "link": link, "via": via,
            "roles": list(roles)}


def texts(lines):
    return [ln["text"] for ln in lines]


def test_reassignment_reads_as_one_line():
    n = Narrator()
    n.update(frame(0, {"seg:G:0": (1, 1), "seg:G:1": (1, 1), "pick:S": (4, 1)}))
    out = n.update(frame(10, {"seg:G:0": (4, 1), "seg:G:1": (4, 1), "pick:S": (4, 0)}))
    assert texts(out) == ["USV 04 took cable seg:G:0, seg:G:1; lane picket S now uncovered"]


def test_link_and_staleness_lines():
    n = Narrator(stale_after_s=60)
    n.update(frame(0, boats=[boat(4, 0), boat(2, 0)]))
    out = n.update(frame(30, boats=[boat(4, 29, link="peer", via=5), boat(2, 0, link="none")]))
    assert texts(out) == ["USV 02 has no path to shore", "USV 04 reaches shore through USV 05"]
    out = n.update(frame(70, boats=[boat(4, 69, link="peer", via=5), boat(2, 0, link="none")]))
    assert texts(out) == ["Shore has not heard USV 02 for over 60 s"]
    out = n.update(frame(80, boats=[boat(4, 79, link="peer", via=5), boat(2, 79)]))
    assert texts(out) == ["Shore hears USV 02 again", "USV 02 direct to shore"]


def test_first_frame_is_silent_and_lines_are_capped():
    n = Narrator()
    assert n.update(frame(0, {"relay": (5, 1)}, [boat(5, 0)])) == []
    for t in range(1, 100):
        n.update(frame(t, {"relay": (5 if t % 2 else 3, 1)}, [boat(5, t)]))
    assert len(n.lines) == 40


def test_demo_story_on_the_real_sim():
    demo = tomllib.loads((ROOT / "server" / "demo.toml").read_text(encoding="utf-8"))
    f = Feed(lambda s: SimSource(s, demo=demo), seed=1, hz=10)
    f.paused = False
    every: list[dict] = []
    while f.world.t < 14_000:
        f.tick()
        every += [ln for ln in f.narrator.lines[-12:] if ln not in every]
    story = " | ".join(texts(every))
    for want in ("USV 01 returning to Korsør", "lane picket S now uncovered",
                 "USV 04 reaches shore through USV", "USV 03 keeping C-07 in view",
                 "USV 03 back on lane picket N", "Shore has not heard USV 03",
                 "USV 03 took the relay role"):
        assert want in story, want
    shore = json.loads(f.tick()["shore"])
    assert shore["narration"] and "narration" not in json.loads(f.tick()["truth"])
    for bad in ("suspicious", "hostile", "won", "cheapest"):
        assert bad not in story.lower()
