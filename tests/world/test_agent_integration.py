"""Real merged agent/shore over B's physical world, not the test harness radio.

These tests focus on heartbeat/table networking with the merged agent. Auction
and movement integration are covered in test_bridge_api.py; contact policy and
operator decisions await A's later phases.
"""

import json
from dataclasses import replace
from pathlib import Path

from agent.core import Agent
from agent.shore import ShoreNode
from contract.geo import dist
from contract.tasks import to_wire
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


def connected_world():
    world = World(ROOT, seed=42, agent_factory=Agent, shore_factory=ShoreNode)
    world.radio_config = replace(world.radio_config, loss_permille=0)
    world.reset()
    return world


def advance(world, seconds):
    for _ in range(seconds):
        world.step()


def diagnostic(world):
    """Compare public agent views and delivered shore state as well as physical hash."""
    return json.dumps(
        {
            "physical": world.state_hash(),
            "agents": {boat: node.view() for boat, node in sorted(world.nodes.items())},
            "shore": world.shore.boats,
            "shore_tasks": {
                task: to_wire(rec) for task, rec in sorted(world.shore.table.recs.items())
            },
        },
        sort_keys=True,
    )


def test_core_learns_real_scene_peers_and_shore_via_peer_hops():
    world = connected_world()
    advance(world, 31)
    assert set(world.shore.boats) == {1, 2, 3, 4, 5}
    for me, node in world.nodes.items():
        assert set(node.peers) == set(world.mission.boats) - {me}
        assert node.shore_t > 0
        assert node.table.recs == world.shore.table.recs
    # Northern picket cannot reach shore directly, yet its original HB is delivered.
    assert dist(world.boats[3].point, world.mission.shore) > world.radio_config.shore_m
    created, hops, payload = world.shore.boats[3]
    assert hops > 0
    assert 0 < created < world.t
    assert (payload["x"], payload["y"]) == world.boats[3].point


def test_direct_link_loss_stays_blocked_while_peer_route_delivers():
    world = connected_world()
    world.inject({"kind": "link_off", "a": 4, "b": "shore"})
    advance(world, 31)
    assert (4, 0) in world.radio.blocked
    created, hops, _ = world.shore.boats[4]
    assert created >= 20_000
    assert hops > 0
    world.inject({"kind": "link_on", "a": 4, "b": "shore"})
    advance(world, 10)
    assert (4, 0) not in world.radio.blocked
    assert world.shore.boats[4][0] > created
    assert world.shore.boats[4][1] == 0


def test_dead_boat_report_stays_stale_not_refreshed_by_forwarding():
    world = connected_world()
    advance(world, 31)
    world.inject({"kind": "boat_off", "boat": 3})
    # Allow already-in-flight messages to finish before checking a stable last report.
    advance(world, 15)
    report = world.shore.boats[3]
    peers = {boat: node.table.last_hb.get(3) for boat, node in world.nodes.items() if boat != 3}
    advance(world, 60)
    assert world.shore.boats[3] == report
    assert report[0] < world.t - 60_000
    assert peers == {
        boat: node.table.last_hb.get(3) for boat, node in world.nodes.items() if boat != 3
    }


def test_complete_shore_isolation_then_rejoin_uses_only_delivered_data():
    world = connected_world()
    advance(world, 31)
    for boat in world.mission.boats:
        world.inject({"kind": "link_off", "a": boat, "b": "shore"})
    advance(world, 15)
    reports = dict(world.shore.boats)
    advance(world, 30)
    assert world.shore.boats == reports
    for boat in world.mission.boats:
        world.inject({"kind": "link_on", "a": boat, "b": "shore"})
    advance(world, 20)
    assert all(world.shore.boats[boat][0] > report[0] for boat, report in reports.items())


def test_real_node_reset_reconstructs_protocol_state_deterministically():
    world = connected_world()
    advance(world, 61)
    expected = diagnostic(world)
    old_node = world.nodes[1]
    world.inject({"kind": "boat_off", "boat": 2})
    advance(world, 10)
    world.reset()
    assert world.nodes[1] is not old_node
    advance(world, 61)
    assert diagnostic(world) == expected
    fresh = connected_world()
    advance(fresh, 61)
    assert diagnostic(fresh) == expected
