"""Shore launch and battery swap at Korsør (#116, with #117 rejoin). Owner: C (with A and B)."""

from pathlib import Path

from agent.core import Agent
from agent.shore import ShoreNode
from contract.geo import dist
from world.sim import World, launch_order

ROOT = Path(__file__).resolve().parents[2]


def world(seed: int = 1, **kw) -> World:
    return World(ROOT, seed=seed, agent_factory=Agent, shore_factory=ShoreNode, launch=True, **kw)


def run_to(w: World, t_s: int) -> None:
    while w.t < t_s * 1000:
        w.step()


def test_boats_start_docked_without_owners_and_are_switched_on_one_by_one():
    w = world()
    assert w.mission.initial == ()
    assert all(dist(b.point, w.mission.shore) <= w.dock_m for b in w.boats.values())
    w.step()
    assert sum(b.enabled for b in w.boats.values()) == 1
    run_to(w, (len(w.boats) - 1) * w.launch_gap_ms // 1000)
    assert all(b.enabled for b in w.boats.values())
    launched = [e["boat"] for e in w.events if e["kind"] == "launch"]
    assert launched == launch_order(w.mission.boats, 1)[1:]


def test_the_switch_on_order_is_seeded_not_planned():
    orders = {tuple(launch_order((1, 2, 3, 4, 5), seed)) for seed in range(1, 9)}
    assert len(orders) > 1
    assert launch_order((1, 2, 3, 4, 5), 3) == launch_order((1, 2, 3, 4, 5), 3)


def test_the_swarm_decides_who_goes_where_and_leaves_the_dock():
    w = world()
    run_to(w, 1800)
    held = {b: n.table.held_by(b) for b, n in sorted(w.nodes.items())}
    assert all(held.values()), held  # every boat found work on its own
    owners = {task: b for b, tasks in held.items() for task in tasks}
    assert len(owners) == sum(len(t) for t in held.values())  # no task held twice
    assert sum(k.startswith("seg:") for k in owners) >= 5
    assert all(dist(b.point, w.mission.shore) > w.dock_m for b in w.boats.values())


def test_a_docked_boat_gets_a_fresh_battery_after_the_swap_and_goes_back_to_work():
    w = world()
    run_to(w, 600)
    boat = launch_order(w.mission.boats, 1)[0]
    w.inject({"kind": "battery_low", "boat": boat})
    run_to(w, 6000)
    kinds = [(e["kind"], e["t_ms"]) for e in w.events if e.get("boat") == boat
             and e["kind"] in ("swap_start", "battery_swap")]
    assert [k for k, _ in kinds] == ["swap_start", "battery_swap"]
    assert kinds[1][1] - kinds[0][1] == w.swap_ms  # 10 min (config/energy.toml swap_s)
    agent = w.nodes[boat]
    assert not agent.returning
    run_to(w, 7800)
    assert w.nodes[boat].table.held_by(boat), "back in the formation after the swap"
    assert dist(w.boats[boat].point, w.mission.shore) > w.dock_m


def test_placed_start_is_unchanged_by_default():
    w = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    assert not w.launch and w.mission.initial
    assert all(b.enabled for b in w.boats.values())
