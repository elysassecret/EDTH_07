"""Demo preset for the video (server/demo.toml, server/DEMO.md). Owner: C.

test_demo_beats_still_happen checks the sim times written in DEMO.md. If agent/ or world/
change and it fails, re-measure and update demo.toml and the shot list before recording.
"""

import json
import tomllib

from server.bridge import SimSource
from server.feed import ROOT, Feed
from server.replay import replay

DEMO = tomllib.loads((ROOT / "server" / "demo.toml").read_text(encoding="utf-8"))


def test_demo_starts_paused_at_start_s_with_the_relay_loss_scheduled():
    f = Feed(lambda s: SimSource(s, demo=DEMO), seed=DEMO["seed"], hz=10,
             start_paused=DEMO["start_paused"])
    assert f.world.t == DEMO["start_s"]
    assert DEMO["inject"][0]["t"] * 1000 in f.world.world.upcoming_event_times()
    snap = json.loads(f.tick()["shore"])
    assert snap["speed"] == 0 and snap["warp_mode"] == "paused"
    f.handle_command({"cmd": "pause", "on": False})
    f.handle_command({"cmd": "reset"})
    assert f.paused and f.world.t == DEMO["start_s"]  # every retake starts the same way


def test_demo_warp_uses_preset_and_slow_windows():
    s = SimSource(DEMO["seed"], demo=DEMO)
    assert s.speed() == DEMO["warp_between"]
    a, _ = DEMO["slow"][0]
    s.step((a - DEMO["start_s"]) * 1000)
    assert s.near_event() and s.speed() == DEMO["warp_near"]


def test_demo_run_log_replays(tmp_path):
    s = SimSource(DEMO["seed"], runs_dir=tmp_path, demo=DEMO)
    while s.t < 11_400:
        s.step(60_000)
    s.close()
    r = replay(s.log.path)
    assert r.ok, r.message


def _shore(s: SimSource):
    return s.world.shore.picture(s.world.t_ms, 1)


def test_demo_beats_still_happen():
    s = SimSource(DEMO["seed"], demo=DEMO)

    def at(t_s: int):
        s.step(t_s * 1000 - s.world.t_ms)
        p = _shore(s)
        return p, {b.id: b for b in p.boats}

    p, b = at(7240)
    assert "seg:G:0" in b[4].roles and p.tasks["pick:S"].state != 1, "battery beat moved"
    p, b = at(7345)
    assert b[4].link == "peer", "link-loss beat moved"
    p, b = at(7870)
    assert b[2].mode == "SHADOWING", "keep-in-view beat (USV 02) moved"
    p, b = at(7870)
    assert any(c.track == "C-07" and not c.ais for c in p.contacts), "contact-on-shore beat moved"
    p, b = at(8060)
    assert "contact:C-07" in b[3].roles, "keep-in-view beat (USV 03) moved"
    held = [d for d in p.decisions if d.tier == "held" and d.state == "pending"]
    assert held and "500 m" in held[0].text, "approval-card beat moved"
    p, b = at(8280)
    assert b[2].mode == "PATROL", "USV 02 relieved beat moved"
    p, b = at(9270)
    assert "pick:N" in b[3].roles, "USV 03 back on picket beat moved"
    p, b = at(10810)
    assert b[4].link == "direct", "link-back beat moved"
    p, b = at(11165)
    assert p.t - b[2].last_heard > 60 and p.t - b[3].last_heard > 60, "relay-loss beat moved"
    p, b = at(13315)
    assert "relay" in b[3].roles and p.t - b[3].last_heard <= 10, "relay-takeover beat moved"
