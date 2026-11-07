"""Proposals and approvals stay bound to a current, delivered contact claim."""

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import CLAIMED, RELEASED
from contract.messages import new
from contract.mission import load_params
from contract.tasks import Rec
from tests.agent.scene import line_mission
from world.routes import load_scene

PARAMS = load_params()
TASK, CLOSE = "contact:AUDIT", "close:contact:AUDIT"


def proposal():
    shore = ShoreNode(line_mission(), PARAMS)
    shore.contacts.on_obs({"track": "AUDIT", "x": 1000, "y": 0, "sog": 100,
                           "cog": 0, "ais": False, "to": 0, "by": 1, "dist": 1000})
    shore.table.apply(Rec(TASK, 1, CLAIMED, 1, 1))
    shore.offer(0)
    return shore


def test_automatic_proposals_are_not_operator_actions_and_bad_commands_do_not_mutate():
    shore = proposal()
    assert len(shore.decisions) == 2 and shore.operator_actions == 0
    before = dict(shore.table.recs)
    for command in ({"cmd": "stop", "id": "seg:A:0"},
                    {"cmd": "stop", "id": "contact:unknown"},
                    {"cmd": "approve", "id": TASK},
                    {"cmd": "approve", "id": CLOSE, "expected_v": 99}):
        assert not shore.command(0, command)
    assert shore.table.recs == before and shore.operator_actions == 0
    assert shore.command(0, {"cmd": "confirm", "id": TASK})
    assert shore.operator_actions == 1
    assert not shore.command(0, {"cmd": "confirm", "id": TASK})
    assert shore.operator_actions == 1
    assert shore.command(0, {"cmd": "stop", "id": TASK})  # confirmed watching can still be stopped
    assert shore.operator_actions == 2


def test_release_withdraws_a_proposal_and_new_claim_gets_a_new_review():
    shore = proposal()
    shore.table.apply(Rec(TASK, 2, RELEASED, 0, 1))
    shore.offer(1000)
    assert shore.decisions[CLOSE]["state"] == "expired"
    assert not shore.command(1000, {"cmd": "approve", "id": CLOSE})
    shore.table.apply(Rec(TASK, 3, CLAIMED, 1, 2))
    shore.offer(2000)
    assert shore.decisions[CLOSE]["state"] == "pending"
    assert shore.decisions[CLOSE]["boat"] == 2
    assert "USV 02" in shore.decisions[CLOSE]["text"]
    assert not shore.command(2000, {"cmd": "approve", "id": CLOSE, "expected_v": 1})
    assert shore.command(2000, {"cmd": "approve", "id": CLOSE, "expected_v": 3})


def test_an_old_inflight_approval_does_not_authorize_another_claim_or_boat():
    agent = Agent(1, line_mission(), PARAMS)
    agent.table.apply(Rec(TASK, 1, CLAIMED, 1, 1))
    cmd = {"task": TASK, "dec": "close", "ans": "approve", "boat": 1, "v": 1}
    agent.contacts.on_cmd(cmd)
    assert agent.contacts.close_allowed(TASK)
    agent.table.apply(Rec(TASK, 2, RELEASED, 0, 1))
    agent.table.apply(Rec(TASK, 3, CLAIMED, 1, 1))
    assert not agent.contacts.close_allowed(TASK)
    agent.contacts.on_cmd(cmd)
    assert not agent.contacts.close_allowed(TASK)
    agent.contacts.on_cmd({**cmd, "v": 3, "boat": 2})
    assert not agent.contacts.close_allowed(TASK)
    agent.contacts.on_cmd({**cmd, "v": 3})
    assert agent.contacts.close_allowed(TASK)


def test_cancelled_approval_does_not_become_delivered_on_a_late_ack():
    shore = proposal()
    assert shore.command(0, {"cmd": "approve", "id": CLOSE})
    msg = shore.decisions[CLOSE]["msg"]
    shore.table.apply(Rec(TASK, 2, RELEASED, 0, 1))
    shore.offer(1000)
    shore.on_ack(1, msg, 1000)
    assert shore.decisions[CLOSE]["state"] == "expired"
    assert msg not in shore.net.pending


def test_return_by_is_the_boats_own_water_current_estimate_not_a_shore_shortcut():
    mission = load_scene().mission
    agent = Agent(3, mission, PARAMS)
    agent.pos, agent.t, agent.cur = (797, 8644), 100_000, (0, 0)
    heartbeat = agent.heartbeat()
    shore = ShoreNode(mission, PARAMS)
    shore.on_msg(new(3, 1, agent.t, "HB", heartbeat))
    (boat,) = shore.picture(agent.t).boats
    assert boat.must_return_by == heartbeat["return_by_s"]
    assert boat.must_return_by == (
        agent.t + max(agent.remaining_ms() - agent.return_need_ms(), 0)) // 1000
    old = dict(heartbeat)
    old.pop("return_by_s")
    shore.on_msg(new(3, 2, agent.t + 1, "HB", old))
    assert shore.picture(agent.t + 1).boats[0].must_return_by is None
