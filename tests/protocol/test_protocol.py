"""P1 to P8: auction, leases, quorum, rebalance, relay election, deputy.

Unit tests drive agents through a tiny in-memory radio; scenario tests use the sim.
"""
from contract.config import MODES, load
from contract.constants import CLAIMED, LEASE, RELEASED, SLOT, VETOED
from contract.messages import Envelope
from contract.tasks import Rec, merge
from contract.views import Sensors
from tests.helpers import events, make_sim
from world.routes import load_scene
from agent.core import Agent
from agent import auction as A
from agent import table as T


def _agents(n=5):
    cfg = load(overrides=MODES["elysa"])
    mission = load_scene(cfg).mission()
    ags = {b: Agent(b, mission, cfg) for b in range(1, n + 1)}
    for b, a in ags.items():
        xy = mission.tasks[a.tour[0][0]].points[0] if a.tour else (mission.tasks[a.pick].points[0] if a.pick else mission.relay_xy)
        a.place(xy, 0)
        a.batt_s = 25200
    return cfg, mission, ags


def _tick(ags, t, inbox, silent=()):
    """One tick for every agent with instant delivery of last tick's output. Returns next inbox."""
    nxt = {b: [] for b in ags}
    for b, a in sorted(ags.items()):
        if b in silent:
            continue
        s = Sensors(t, a.xy[0], a.xy[1], a.batt_s, 1000, 2.3, [], [], inbox.get(b, []))
        _, out = a.step(s)
        for m in out:
            for q in ags:
                if q != b and q not in silent:
                    nxt[q].append(m)
    return nxt


def test_p1_lost_bid_cheaper_boat_wins_on_merge():
    a = Rec("seg:G:0", 2, CLAIMED, 5000, 3, 0)
    b = Rec("seg:G:0", 2, CLAIMED, 900, 4, 0)
    assert merge(a, b) == b and merge(b, a) == b


def test_p6_claim_beats_release_at_equal_version_and_veto_beats_both():
    rel = Rec("seg:G:0", 2, RELEASED, 0, 1, 0)
    cl = Rec("seg:G:0", 2, CLAIMED, 100, 4, 0)
    assert merge(rel, cl) == cl
    assert merge(cl, Rec("seg:G:0", 2, VETOED, 0, 0, 0)).state == VETOED


def test_p2_winner_dies_mid_round_task_reauctioned_next_slot():
    cfg, mission, ags = _agents()
    inbox = {b: [] for b in ags}
    # boat 1 releases seg:G:0 at t = 1 s
    t = 0
    for t in range(1000, 1000 + SLOT * 2 + 2000, 1000):
        if t == 1000:
            ags[1]._release("seg:G:0", t)
        inbox = _tick(ags, t, inbox)
    # by now a bid round has happened and someone (should be 1 or another) claimed, or bids are pending
    # Now simulate: at the next slot boat 4 is cheapest and dies right after bidding.
    task = "seg:G:0"
    for a in ags.values():
        a.publish(Rec(task, T.max_ver(a, task) + 1, RELEASED, 0, a.me, 0), t) if a.me == ags[1].me else None
    inbox = _tick(ags, t + 1000, inbox)
    t_slot = ((t // SLOT) + 1) * SLOT
    while t < t_slot:
        t += 1000
        inbox = _tick(ags, t, inbox)
    # boat 4 just bid at t_slot (if it was eligible); kill it before the round closes
    silent = {4}
    for _ in range(SLOT // 1000 + 1):
        t += 1000
        inbox = _tick(ags, t, inbox, silent=silent)
    # the round closed without 4 claiming; the task must not be stranded: within a few more slots someone claims
    for _ in range(3 * SLOT // 1000):
        t += 1000
        inbox = _tick(ags, t, inbox, silent=silent)
    owners = {a.table[task].owner for b, a in ags.items() if b != 4}
    states = {a.table[task].state for b, a in ags.items() if b != 4}
    assert states == {CLAIMED} and 4 not in owners, (owners, states)


def test_p3_claim_arriving_before_close_cancels_round():
    cfg, mission, ags = _agents()
    a = ags[3]
    t = SLOT * 10
    task = "seg:G:0"
    a.table[task] = Rec(task, 2, RELEASED, 0, 1, 0)
    a.bids = {t // SLOT - 1: {task: [(100, 3), (200, 4)]}}
    a.last_hb[2] = t                      # boat 2 is alive
    # a live claim from boat 2 arrives before the round closes
    T.on_record(a, Rec(task, 3, CLAIMED, 50, 2, 0), t)
    A.close_round(a, t // SLOT - 1, t)
    assert a.table[task].owner == 2 and a.stats["claims"] == 0


def test_p4_isolated_boat_claims_nothing_on_expiry():
    cfg, mission, ags = _agents()
    a = ags[3]
    t = LEASE * 3
    for b in mission.boats:
        a.last_hb[b] = 0           # everyone silent for a long time: all leases expired
    a.last_hb[3] = t
    a.t = t
    a.open_since = {}
    for task in sorted(a.table):
        if task.startswith("seg:"):
            assert T.is_open(a, task, t)
            assert not A.can_bid(a, task, t), task   # no live majority: expiry takeover refused
    # with a live majority (2 peers of 4 active -> 1 + 2 >= 3) it may bid
    a.last_hb[4] = t
    a.last_hb[5] = t
    a.peers[4] = {"mode": "PATROL", "t": t, "x": 0, "y": 0, "batt": 1000, "cycle": 0, "tour": [], "pick": "", "relay": False, "shore_age": 0}
    a.peers[5] = dict(a.peers[4])
    assert any(A.can_bid(a, task, t) for task in a.table if task.startswith("seg:"))


def test_p5_rejoin_no_idle_boat_after_two_rebalance_periods():
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    # isolate boat 2 (the HVDC scout) from everyone for long enough that its lease expires and its tasks move
    sim.run_until(600)
    for q in [0, 1, 3, 4, 5]:
        sim.inject({"kind": "link_off", "a": 2, "b": q})
    sim.run_until(600 + 900)
    for q in [0, 1, 3, 4, 5]:
        sim.inject({"kind": "link_on", "a": 2, "b": q})
    sim.run_until(600 + 900 + 700)
    # after rejoin and two rebalance periods (600 s), nobody patrolling is idle
    idle = [b for b, a in sim.agents.items() if a.mode == "PATROL" and not a.tour and not a.pick and not A.i_am_relay(a)]
    assert idle == [], (idle, {b: (a.mode, a.tour, a.pick) for b, a in sim.agents.items()})
    # and every segment has exactly one owner in the converged tables
    owners = {}
    for b, a in sim.agents.items():
        for task, r in a.table.items():
            if task.startswith("seg:"):
                owners.setdefault(task, set()).add((r.ver, r.owner, r.state))
    assert all(len(v) == 1 for v in owners.values()), owners


def test_p7_group_with_shore_path_elects_no_relay_and_relay_loss_is_repaired():
    sim, m = make_sim("elysa", 1)
    sim.run_warm()
    sim.run_until(300)
    sim.inject({"kind": "boat_fail", "boat": 5})
    sim.run_until(300 + 400)
    # the side that lost its shore path (north: 2 and 3) elects a relay within a few slots
    north = {b: sim.agents[b].table["relay"] for b in (2, 3)}
    owners = {r.owner for r in north.values()}
    assert len(owners) == 1 and 5 not in owners, north
    new = owners.pop()
    assert sim.agents[new].mode == "RELAY"
    # P7 proper: boat 4 (direct shore link at the south picket) never bid on relay
    bids = events(sim, kinds={"bid"}, after_s=300)
    assert not any(b == 4 and body["task"] == "relay" for _, b, _, body in bids), bids
    # the south side cannot know yet: no path exists until the new relay reaches the station (that is the point)
    assert sim.radio.shore_reach()[new] == -1
    sim.run_until(300 + 3600)
    assert sim.radio.shore_reach()[new] >= 0
    assert {sim.agents[b].table["relay"].owner for b in (1, 2, 3, 4)} == {new}


def test_p8_deputy_takes_relay_with_owner_silent_or_declines():
    cfg, mission, ags = _agents()
    a = ags[3]
    t = SLOT * 100
    a.t = t
    for b in mission.boats:
        a.last_hb[b] = t
    a.last_hb[0] = 0                            # shore silent: no path
    a.table["relay"] = Rec("relay", 3, CLAIMED, 100, 5, 3)   # 5 owns, 3 is deputy
    a.last_hb[5] = t - LEASE - 1000             # owner lease expired
    from agent import deputy as D
    D.on_tick(a, t)
    r = a.table["relay"]
    assert r.ver == 4 and r.owner == 3 and r.state == CLAIMED and a.mode == "RELAY"
    assert any(k == "deputy_takeover" for _, k, _ in a.events)
    # decline path: a deputy that is returning cannot take it and reopens the task
    b = ags[4]
    b.t = t
    for q in mission.boats:
        b.last_hb[q] = t
    b.last_hb[0] = 0
    b.table["relay"] = Rec("relay", 3, CLAIMED, 100, 5, 4)
    b.last_hb[5] = t - LEASE - 1000
    b.mode = "RETURNING"
    D.on_tick(b, t)
    assert b.table["relay"].state == RELEASED and b.table["relay"].ver == 4


def test_envelope_round_trip_and_forwarding_keeps_t_created():
    e = Envelope("1-7", 1, 5000, 17000, "REC", 0, {"rec": ["seg:G:0", 2, 1, 10, 1, 0]})
    f = Envelope.decode(e.encode()).forwarded()
    assert f.t_created == 5000 and f.hops == 1 and f.msg_id == "1-7"
