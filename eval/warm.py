"""Warm-up in the runner, until B ships `World(warm_ms, phase)`. Owner: D.

The world starts cold at a fixed phase, so km overdue would measure the start-up, not the
response to a failure. This module gives every mode the same warm state:

- The sweepers start somewhere round their tour loop, drawn per boat from the seed.
- For `warm_s` the boats patrol with bidding off and the battery held full.
- At the end the real policy goes in and mission time 0 begins.

The sim clock cannot go back to 0: boats hold leases, retries and next-slot times against it.
So the clock stays ahead by `warm_ms`, and the tape, the tide flip and `repair_off_after_ms`
are shifted by the same amount. Agents see one longer mission, not a rewound one. Writes go to
public World attributes, boat position and charge, `params` on the nodes, and once, at t = 0,
each Follower's place in its tour.
"""

import itertools
from dataclasses import replace
from math import hypot

import numpy as np

from agent.core import Agent
from agent.shore import ShoreNode
from world.current import Current
from world.sim import World

WARM_S = 10_800


def tour_point(pts: list[tuple[int, int]], frac: float) -> tuple[int, int]:
    """The point `frac` of the way along a metre polyline, in integer mm."""
    legs = [hypot(b[0] - a[0], b[1] - a[1]) for a, b in itertools.pairwise(pts)]
    left = frac * sum(legs)
    for (a, b), d in zip(itertools.pairwise(pts), legs, strict=True):
        if d > 0 and left <= d:
            f = left / d
            return round((a[0] + (b[0] - a[0]) * f) * 1000), round((a[1] + (b[1] - a[1]) * f) * 1000)
        left -= d
    return pts[-1][0] * 1000, pts[-1][1] * 1000


def seed_phases(seed: int, boats) -> dict[int, float]:
    children = np.random.default_rng(seed).spawn(len(boats))
    return {b: float(rng.random()) for b, rng in zip(boats, children, strict=True)}


def loop_edges(node) -> list[tuple[int, int, tuple, tuple]]:
    """The closed tour as edges (leg i, waypoint j, from, to), transit legs included."""
    legs = node.follow.legs
    ways = [node.tours.way(leg) for leg in legs]
    edges = []
    for i, way in enumerate(ways):
        edges.append((i, 0, ways[i - 1][-1], way[0]))
        edges.extend((i, j, way[j - 1], way[j]) for j in range(1, len(way)))
    return edges


def place_boats(world: World, phases: dict[int, float]) -> None:
    """Put each sweeper `phase` of the way round its tour, heading for the next waypoint.

    Moving the boat alone is not enough: `Follower.start_nearest` snaps to the nearest waypoint,
    and these cables have few, so phases collapse into a handful of clusters. Runs once, on the
    t = 0 tick and before any mode differs. Pickets and the relay hold a station: no phase.
    """
    world.step()  # at t = 0 nothing moves and the agents build their tours
    for boat, node in sorted(world.nodes.items()):
        if not node.follow.legs:
            continue
        edges = loop_edges(node)
        lengths = [hypot(e[3][0] - e[2][0], e[3][1] - e[2][1]) for e in edges]
        left = phases[boat] * sum(lengths)
        for edge, d in zip(edges, lengths, strict=True):
            if left <= d:
                break
            left -= d
        state = world.boats[boat]
        state.x_mm, state.y_mm = tour_point([edge[2], edge[3]], left / d if d else 0.0)
        node.follow.i, node.follow.j = edge[0], edge[1]
    world.sample_visit_ms = [None] * len(world.scene.samples)


def build_world(root, mode: str, seed: int, speed_mm_s=None, radio_m=None, warm_s=WARM_S) -> World:
    """A world ready for `warm_up`, with tape and tide shifted by the warm-up length."""
    world = World(root, seed=seed, agent_factory=Agent, shore_factory=ShoreNode)
    warm_ms = warm_s * 1000
    world.script = [
        dict(e) if e["kind"] == "reset" else {**e, "t": e["t"] + warm_s} for e in world.script
    ]
    world.current = Current(world.current.vector, world.current.flip_ms + warm_ms)
    if radio_m is not None:
        world.radio_config = replace(world.radio_config, boat_m=radio_m)
    world.final_params = replace(
        world.params,
        policy=mode,
        speed_mm_s=speed_mm_s or world.params.speed_mm_s,
        repair_off_after_ms=world.params.repair_off_after_ms + warm_ms,
    )
    world.warm_ms = warm_ms
    # With policy off and repair_off_after_ms 0, may_bid is False from t = 0: nobody bids.
    world.params = replace(world.final_params, policy="off", repair_off_after_ms=0)
    world.reset()
    if warm_ms:
        place_boats(world, seed_phases(seed, world.mission.boats))
    return world


def warm_up(world: World) -> str:
    """Run to the tick before mission time 0, install the real policy, return the warm hash."""
    end = world.warm_ms - world.tick_ms
    while world.warm_ms and world.next_tick_ms <= end:
        world.step()
        for state in world.boats.values():  # drain off
            state.charge_ms, state.drain_remainder = state.endurance_ms, 0
    warm_hash = world.state_hash()
    world.params = world.final_params
    for node in (*world.nodes.values(), world.shore):
        node.params = world.final_params
    return warm_hash
