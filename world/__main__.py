"""Offline world runner; core networking or fixed-route exercise, not evaluation."""

import argparse
import json

from contract.constants import PATROL, RETURNING, SENTINEL, UNAVAILABLE
from contract.geo import dist
from contract.mission import Action
from world.sim import World


class ExerciseBoat:
    """Fixed initial routes and simple safety return, without any task repair."""

    def __init__(self, me, mission, params):
        self.params = params
        self.shore = mission.shore
        held = {task for task, owner in mission.initial if owner == me}
        self.tasks = [task for task in mission.tasks if task.id in held]
        self.waypoints = tuple(point for task in self.tasks for point in task.pts)
        self.index = 0
        self.stationary = not any(task.id.startswith("seg:") for task in self.tasks)
        self.returning = False
        self.driving = False

    def step(self, t, own, seen, inbox):
        point = (own.x, own.y)
        distance = dist(point, self.shore)
        along = (
            (own.cur_x * (self.shore[0] - point[0]) + own.cur_y * (self.shore[1] - point[1]))
            // distance
            if distance
            else 0
        )
        ground = max(self.params.speed_mm_s + along, self.params.speed_mm_s // 4)
        home_ms = distance * 1_000_000 // ground
        budget = own.batt * self.params.endurance_ms // 1000
        if (
            budget
            <= (home_ms + self.params.reserve_ms) * self.params.return_safety_permille // 1000
        ):
            self.returning = True
        if self.returning:
            if dist(point, self.shore) <= 2:
                return Action(UNAVAILABLE, None, 0), []
            return Action(RETURNING, self.shore, self.params.speed_mm_s), []
        if self.stationary:
            offset = dist(point, self.waypoints[0])
            if offset > self.params.sentinel_radius_m:
                self.driving = True
            elif offset <= 100:
                self.driving = False
            return Action(
                SENTINEL, self.waypoints[0] if self.driving else None, self.params.speed_mm_s
            ), []
        if dist(point, self.waypoints[self.index]) <= 2:
            self.index = (self.index + 1) % len(self.waypoints)
        return Action(PATROL, self.waypoints[self.index], self.params.speed_mm_s), []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=14400)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--controller", choices=("exercise", "core"), default="exercise")
    args = parser.parse_args()
    if args.seconds < 0:
        parser.error("seconds must be nonnegative")
    if args.controller == "core":
        from agent.core import Agent
        from agent.shore import ShoreNode

        sim = World(seed=args.seed, agent_factory=Agent, shore_factory=ShoreNode)
        label = (
            "real agent core and shore protocol; motion/allocation depend on agent implementation"
        )
    else:
        sim = World(seed=args.seed, agent_factory=ExerciseBoat)
        label = "physical-world exercise; fixed-route stand-ins, no swarm allocation"
    sim.step()
    while sim.t + sim.tick_ms <= args.seconds * 1000:
        sim.step()
    print(
        json.dumps(
            {
                "label": label,
                "controller": args.controller,
                "agent_views": {
                    str(boat): node.view()
                    for boat, node in sorted(sim.nodes.items())
                    if hasattr(node, "view")
                },
                "shore_received": {
                    str(boat): {"created_ms": tc, "hops": hops, "heartbeat": payload}
                    for boat, (tc, hops, payload) in sorted(sim.shore.boats.items())
                }
                if sim.shore is not None
                else {},
                "truth": sim.snapshot(),
                "physical_hash": sim.state_hash(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
