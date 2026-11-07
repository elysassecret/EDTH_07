"""#72: real-scene operator answers traverse radio, not a direct boat mutation.

The checkpoint is the merged #70 demo's 8060 s approval beat. Deep copies are
isolated test fixtures, not a new World checkpoint/restart API or warm-start mode.
"""

from copy import deepcopy
from pathlib import Path

import pytest

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import VETOED
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]
TASK = "contact:C-07"


@pytest.fixture(scope="module")
def contact_checkpoint():
    world = World(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    while world.next_tick_ms <= 8_060_000:
        world.step()
    picture = world.shore.picture(world.t_ms)
    assert any(c.track == "C-07" and not c.ais for c in picture.contacts)
    cards = {d.id: d for d in picture.decisions}
    assert cards[TASK].state == "pending"
    assert cards[f"close:{TASK}"].state == "pending"
    assert cards[f"close:{TASK}"].tier == "held"
    return world


@pytest.mark.parametrize(
    "action,decision_id,accepted_state",
    [
        ("approve", f"close:{TASK}", "approved"),
        ("decline", f"close:{TASK}", "declined"),
        ("stop", TASK, "stopped"),
    ],
)
def test_real_scene_answers_require_delivery_and_preserve_physics(
    contact_checkpoint, action, decision_id, accepted_state
):
    world = deepcopy(contact_checkpoint)
    decision = next(d for d in world.shore.picture(world.t_ms).decisions if d.id == decision_id)
    owner = decision.boat
    assert owner in world.nodes
    node = world.nodes[owner]
    assert node.contacts.watching() == TASK
    assert node.contacts.close.get(TASK) is None
    charge = {boat: state.charge_ms for boat, state in world.boats.items()}

    assert world.shore.command(world.t_ms, {"cmd": action, "id": decision_id})
    assert world.shore.decisions[decision_id]["state"] == accepted_state
    # Acceptance at shore cannot bypass bytes/delay and mutate the watcher in this tick.
    assert node.contacts.watching() == TASK
    assert node.contacts.close.get(TASK) is None

    # A bounded regression budget, not a claimed deployment latency guarantee.
    deadline = world.t_ms + 180_000
    while world.t_ms < deadline and world.shore.decisions[decision_id]["state"] != "delivered":
        world.step()
    assert world.shore.decisions[decision_id]["state"] == "delivered"
    assert world.t_ms > contact_checkpoint.t_ms
    assert all(world.boats[boat].charge_ms <= value for boat, value in charge.items())
    if action == "approve":
        assert node.contacts.close[TASK] in ("approved", "done")
        assert node.contacts.watching() == TASK
    elif action == "decline":
        assert node.contacts.close.get(TASK) is None
        assert node.contacts.watching() == TASK  # decline a closer look, not the standing watch
    else:
        assert node.table.recs[TASK].state == VETOED
        assert node.contacts.watching() is None
        assert world.shore.decisions[f"close:{TASK}"]["state"] == "expired"
