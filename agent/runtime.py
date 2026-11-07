"""One boat as its own process (#105). Owner: A.

The agent already has an explicit boundary: Agent.step(t, own, seen, inbox bytes) returns an action
and the bytes to broadcast, with no clock, files or randomness. This wraps it in a process that
speaks JSON lines on stdin/stdout, so each boat can run alone, next to its peers, or under a
world/shore that restarts. The host (world or test) owns time, sensors and radio.

    uv run python -m agent.runtime <boat id>

First line in:  {"mission": {...}, "params": {...}}   (dataclasses.asdict of Mission, Params)
Then per tick:  {"t": ms, "own": [x, y, batt, cur_x, cur_y],
                 "seen": [[track, x, y, sog, cog, ais], ...], "inbox": ["<hex>", ...]}
Reply per tick: {"mode": str, "target": [x, y] | null, "speed": mm/s, "out": ["<hex>", ...]}

Reconnecting needs nothing special: records merge by version (contract/tasks.merge), leases are
renewed by heartbeats, and the network layer drops expired or already-seen messages, so an old
VETO or CMD is never executed twice or late.
"""
import json
import sys

from agent.core import Agent
from contract.mission import Detection, Mission, Own, Params, TaskSpec


def mission_from(d: dict) -> Mission:
    pt = tuple
    return Mission(boats=tuple(d["boats"]),
                   tasks=tuple(TaskSpec(s["id"], tuple(pt(p) for p in s["pts"])) for s in d["tasks"]),
                   initial=tuple((k, o) for k, o in d["initial"]), shore=pt(d["shore"]),
                   lane=tuple(pt(p) for p in d["lane"]), lane_half_m=d["lane_half_m"])


def serve(me: int, lines, write) -> None:
    hello = json.loads(next(lines))
    agent = Agent(me, mission_from(hello["mission"]), Params(**hello["params"]))
    for line in lines:
        m = json.loads(line)
        action, out = agent.step(m["t"], Own(*m["own"]), tuple(Detection(*d) for d in m["seen"]),
                                 [bytes.fromhex(h) for h in m["inbox"]])
        write(json.dumps({"mode": action.mode,
                          "target": list(action.target) if action.target else None,
                          "speed": action.speed_mm_s, "out": [b.hex() for b in out]}) + "\n")


if __name__ == "__main__":
    serve(int(sys.argv[1]), iter(sys.stdin.readline, ""),
          lambda s: (sys.stdout.write(s), sys.stdout.flush()))
