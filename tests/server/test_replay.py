"""Run log and replay (BUILD_PLAN step 13, acceptance test D3). Owner: C."""

import json

from server.bridge import SimSource
from server.replay import replay
from server.runlog import HASH_MS, SNAPSHOT_MS, config_hash, read


def run_with_commands(tmp_path, until_s: int = 600) -> SimSource:
    s = SimSource(1, runs_dir=tmp_path)
    plan = {
        30: {"cmd": "inject", "kind": "link_off", "a": 3, "b": 2},
        95: {"cmd": "inject", "kind": "battery_low", "a": 2},
        130: {"cmd": "stop", "id": "contact:C-07"},
        200: {"cmd": "inject", "kind": "link_on", "a": 3, "b": 2},
        260: {"cmd": "inject", "kind": "boat_off", "a": 9},  # rejected, still logged
    }
    while s.t < until_s:
        s.step(7_000)  # uneven frames on purpose: replay must not depend on the frame rate
        for t in [t for t in plan if t <= s.t]:
            s.command(plan.pop(t))
    s.close()
    return s


def test_log_has_header_events_commands_snapshots_hashes(tmp_path):
    s = run_with_commands(tmp_path)
    lines = read(s.log.path)
    head = lines[0]
    assert head["type"] == "header" and head["seed"] == 1
    assert head["config_hash"] == config_hash()
    kinds = {r["type"] for r in lines}
    assert kinds == {"header", "event", "cmd", "snapshot", "hash"}
    cmds = [r for r in lines if r["type"] == "cmd"]
    assert len(cmds) == 5 and cmds[-1]["ok"] is False
    snaps = [r["t_ms"] for r in lines if r["type"] == "snapshot"]
    assert snaps[:3] == [0, SNAPSHOT_MS, 2 * SNAPSHOT_MS]
    assert all(t % HASH_MS == 0 for t in (r["t_ms"] for r in lines if r["type"] == "hash"))
    first_snap = next(r for r in lines if r["type"] == "snapshot")
    assert first_snap["shore"]["view"] == "shore" and first_snap["truth"]["view"] == "truth"


def test_replay_matches_hashes(tmp_path):
    s = run_with_commands(tmp_path)
    r = replay(s.log.path)
    assert r.ok, r.message
    assert r.checked == 11  # t = 0, 60, ..., 600 s


def test_replay_finds_a_changed_command(tmp_path):
    s = run_with_commands(tmp_path)
    lines = s.log.path.read_text().splitlines()
    i = next(i for i, ln in enumerate(lines) if '"battery_low"' in ln and '"cmd"' in ln)
    lines[i] = lines[i].replace('"a":2', '"a":4')
    s.log.path.write_text("\n".join(lines) + "\n")
    r = replay(s.log.path)
    assert not r.ok and "hash differs at t = 120 s" in r.message


def test_no_log_unless_asked(tmp_path):
    s = SimSource(1)
    s.step(20_000)
    assert s.log is None
    assert list(tmp_path.iterdir()) == []


def test_log_lines_are_json(tmp_path):
    s = run_with_commands(tmp_path, until_s=60)
    for line in s.log.path.read_text().splitlines():
        json.loads(line)


def test_replay_in_another_process_with_another_hash_seed(tmp_path):
    """D1 + D3: a fresh process with a different PYTHONHASHSEED gets the same hashes."""
    import os
    import subprocess
    import sys

    from server.feed import ROOT

    s = run_with_commands(tmp_path, until_s=300)
    env = {**os.environ, "PYTHONHASHSEED": "12345"}
    out = subprocess.run([sys.executable, "-m", "server.replay", str(s.log.path)], cwd=ROOT,
                         env=env, capture_output=True, text=True, timeout=120, check=False)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "replay OK: 6 hashes match" in out.stdout
