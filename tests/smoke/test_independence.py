"""#105 acceptance run as a smoke test (#109 item 2). Owner: D.

Separate boat and shore runtimes over B's wire boundary (`world/runtime_bus.py`), seed 1:

1. Supervised patrol: every fixed task (7 segments, 2 pickets, relay) has exactly one holder.
2. Stop the shore service, isolate boat 2 from peers and shore, stop boat 1's runtime.
3. Within the segment lease, the isolated boat keeps sweeping exactly its own segments and takes
   nothing new; the peers keep theirs.
4. After the lease, the connected peers hold everything boat 1 held.
5. Restore everything without restarting a runtime: same agent objects, every fixed task held by
   exactly one boat again, and the shore shows every segment, never fresher than truth.

Isolation is cut both ways here. `DetachedWorldHarness.isolate_boat` blocks only the boat's own
transmissions, because `Radio.link(src, dst)` is directed, so the "isolated" boat still hears its
peers (reported on #105). Not covered yet: stale or duplicate shore commands after reconnect (A's
runtime and C's shore service, #105).
"""
from pathlib import Path

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import SHORE, UNAVAILABLE
from eval.metrics import seg_ages_s
from world.runtime_bus import DetachedWorldHarness

ROOT = Path(__file__).resolve().parents[2]
SLACK_S = 60  # heartbeat timing, as in eval/gap.py


def holders(h) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for boat, ep in sorted(h.boat_endpoints.items()):
        for task in ep.node.table.held_by(boat):
            out.setdefault(task, []).append(boat)
    return out


def held(h, boat: int) -> set[str]:
    return set(h.boat_endpoints[boat].node.table.held_by(boat))


def cut_both_ways(h, boat: int, on: bool) -> None:
    for other in [SHORE, *h.world.mission.boats]:
        if other != boat:
            h.world.radio.link(boat, other, on)
            h.world.radio.link(other, boat, on)


def run(h, seconds: int) -> None:
    for _ in range(seconds * 1000 // h.world.tick_ms):
        h.step()


def test_each_boat_keeps_working_without_shore_or_peers_and_rejoins():
    h = DetachedWorldHarness(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    w = h.world
    fixed = [t.id for t in w.mission.tasks]
    run(h, 60)
    before = holders(h)
    assert sorted(before) == sorted(fixed) and all(len(b) == 1 for b in before.values())
    nodes = {b: id(ep.node) for b, ep in h.boat_endpoints.items()}
    own2, own1 = held(h, 2), held(h, 1)
    peers = {b: held(h, b) for b in (3, 4, 5)}

    h.stop_shore()
    h.isolate_boat(2)
    cut_both_ways(h, 2, False)
    h.stop_boat_runtime(1)
    lease_s = w.params.seg_lease_ms // 1000
    run(h, lease_s - 60)
    assert held(h, 2) == own2  # solo: its own authorised work, nothing new
    assert w.actions[2].mode != UNAVAILABLE
    assert w.actions[1].mode == UNAVAILABLE
    assert {b: held(h, b) for b in peers} == peers

    run(h, 180)
    connected = set().union(*(held(h, b) for b in (3, 4, 5)))
    assert own1 <= connected  # the peers shared out what boat 1 left
    assert held(h, 2) == own2  # still sweeping: it cannot hear that the peers took its work too

    h.restore_all()
    cut_both_ways(h, 2, True)
    run(h, 180)
    assert {b: id(ep.node) for b, ep in h.boat_endpoints.items()} == nodes  # nobody restarted
    after = holders(h)
    assert sorted(after) == sorted(fixed)
    assert all(len(b) == 1 for b in after.values()), after  # merge left no double owner

    shore = h.shore_endpoint.node.picture(w.t).seg_age
    truth = seg_ages_s(w.scene.samples, w.sample_visit_ms, w.t)
    assert sorted(shore) == sorted(truth)  # every segment on the shore picture
    for seg, age in truth.items():
        if age is not None and shore[seg] is not None:
            assert shore[seg] >= age - SLACK_S, seg  # older than truth is allowed, fresher never
