"""#105, A's part: each boat in its own process behaves exactly like the in-process agent."""
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from contract.mission import Action, load_params
from tests.agent.harness import Sim
from tests.agent.scene import START, scene_mission

ROOT = Path(__file__).resolve().parents[2]
PARAMS = load_params()


class ProcAgent:
    """Stands in for Agent in the harness; the real agent runs in a child process."""

    def __init__(self, me: int, mission, params):
        self.p = subprocess.Popen([sys.executable, "-m", "agent.runtime", str(me)], cwd=ROOT,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.send({"mission": asdict(mission), "params": asdict(params)})

    def send(self, obj: dict) -> None:
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def step(self, t, own, seen, inbox):
        self.send({"t": t, "own": [own.x, own.y, own.batt, own.cur_x, own.cur_y],
                   "seen": [[d.track, d.x, d.y, d.sog, d.cog, d.ais] for d in seen],
                   "inbox": [b.hex() for b in inbox]})
        r = json.loads(self.p.stdout.readline())
        target = tuple(r["target"]) if r["target"] else None
        return Action(r["mode"], target, r["speed"]), [bytes.fromhex(h) for h in r["out"]]

    def close(self) -> None:
        self.p.stdin.close()
        self.p.wait(timeout=10)


def story(procs: bool) -> list:
    s = Sim(scene_mission(), PARAMS, START)
    if procs:
        s.agents = {b: ProcAgent(b, s.mission, PARAMS) for b in s.mission.boats}
    trace = []
    try:
        while s.t <= 900_000:
            if s.t == 600_000:
                s.set_batt(1, 200)  # 01 goes home, 04 takes its cables
            s.tick()
            trace.append(sorted(s.actions.items()))
        pic = s.shore.picture(s.t)
        return [trace, pic.model_dump(exclude={"events"}), [e for e in s.shore.events]]
    finally:
        if procs:
            for a in s.agents.values():
                a.close()


def test_five_boat_processes_match_the_in_process_fleet():
    """Same actions every tick, same shore picture and events: the message boundary is the only
    thing between a boat and the rest, so it can run as its own process."""
    assert story(procs=True) == story(procs=False)
