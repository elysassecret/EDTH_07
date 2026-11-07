"""S1 to S6: the fixed tape told by the real world, boats and shore. Slow.

Seed 11 is a run where a sweeper finds the contact while it loiters, so the whole story plays.
Most seeds never find it (`eval/results.md`), which is why one seed is chosen here and why no
number from this file belongs on a slide. Shore-side contact checks wait for #17.
"""
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from contract.constants import CLAIMED, RELEASED, RETURNING, SLOT
from contract.tasks import kind
from eval.warm import build_world, warm_up

ROOT = Path(__file__).resolve().parents[2]
SEED = 11
TRACK = "C-07"
TASK = "contact:C-07"
FAIL_S, CUT_S, DEPART_S, LINK_BACK_S = 7200, 7320, 9200, 10800
pytestmark = pytest.mark.slow


@dataclass
class Story:
    world: object
    t0: int
    pictures: dict = field(default_factory=dict)
    fail_held: list = field(default_factory=list)
    first_claim_s: int | None = None
    all_owned_s: int | None = None
    detect_s: int | None = None
    held_by: int | None = None
    watcher: int | None = None
    claim_s: int | None = None
    in_view_s: int | None = None
    cannot_hold_s: int | None = None
    released_s: int | None = None
    pick_s_states: list = field(default_factory=list)
    boat1_mode: str | None = None


def seg_tasks(world):
    return [t.id for t in world.mission.tasks if kind(t.id) == "seg"]


def record(s: Story) -> None:
    w, mt = s.world, (s.world.t - s.t0) // 1000
    if mt == FAIL_S - 1:  # the boat reacts on the failure tick itself
        s.fail_held = list(w.nodes[1].table.held_by(1))
    if mt == FAIL_S + 60:
        s.boat1_mode = w.actions[1].mode
    if mt > FAIL_S:
        table = w.nodes[2].table
        lost = [k for k in s.fail_held if table.recs[k].state == CLAIMED and table.recs[k].owner != 1]
        if s.first_claim_s is None and lost:
            s.first_claim_s = mt
        if s.all_owned_s is None and len(lost) == len([k for k in s.fail_held if kind(k) == "seg"]):
            s.all_owned_s = mt
    for b, node in sorted(w.nodes.items()):
        if s.detect_s is None and TRACK in node.contacts.first:
            s.detect_s = mt
        if s.held_by is None and node.contacts.holding == TRACK:
            s.held_by = b
        rec = node.table.recs.get(TASK)
        if rec is None:
            continue
        if s.claim_s is None and rec.state == CLAIMED:
            s.claim_s, s.watcher = mt, rec.owner
        if s.watcher == b and s.in_view_s is None and rec.state == CLAIMED and rec.owner == b:
            obs = node.contacts.by.get(TRACK, {}).get(b)
            if obs is not None and obs["to"] == w.t and obs["dist"] <= w.params.keep_in_view_m:
                s.in_view_s = mt
        if s.cannot_hold_s is None and node.contacts.flags.get(TASK, {}).get("cannot_hold"):
            s.cannot_hold_s = mt
        if s.watcher == b and s.released_s is None and rec.state == RELEASED:
            s.released_s = mt
    if mt % 60 == 0:
        s.pictures[mt] = w.shore.picture(w.t)
        s.pick_s_states.append((mt, s.pictures[mt].tasks["pick:S"].state))


@pytest.fixture(scope="module")
def story():
    world = build_world(ROOT, "elysa", SEED, warm_s=600)
    warm_up(world)
    s = Story(world, world.warm_ms)
    while world.next_tick_ms <= world.warm_ms + 14_000_000:
        world.step()
        record(s)
    return s


def boat_card(picture, boat):
    return next(b for b in picture.boats if b.id == boat)


def test_s1_battery_return_releases_tasks_and_they_are_re_owned(story):
    assert story.fail_held, "boat 1 held nothing before the failure"
    assert story.boat1_mode == RETURNING
    assert story.world.nodes[2].table.held_by(1) == []
    assert story.first_claim_s - FAIL_S <= 2 * SLOT // 1000 + 1
    assert story.all_owned_s - FAIL_S <= 60  # one bid per slot, measured in eval/results.md


def test_s2_link_cut_marks_boat_4_and_it_still_reaches_shore_through_a_peer(story):
    during = boat_card(story.pictures[CUT_S + 60], 4)
    assert during.link == "peer"  # not "direct", not lost: heard through a peer
    assert (CUT_S + 60) - during.last_heard <= 20
    after = boat_card(story.pictures[LINK_BACK_S + 60], 4)
    assert after.link == "direct"


@pytest.mark.xfail(reason="#21: via() takes the shore edge from reported neighbours")
def test_s2_the_relay_path_shows_on_the_shore(story):
    assert boat_card(story.pictures[CUT_S + 60], 4).via != 0


def test_s3_contact_detected_held_then_watched_in_view(story):
    assert CUT_S <= story.detect_s < DEPART_S
    assert story.held_by == 2  # the sweeper that found it holds until relieved
    assert story.watcher == 3  # the north picket takes it
    assert story.detect_s < story.claim_s <= story.in_view_s < DEPART_S


@pytest.mark.xfail(reason="#17: shore contacts arrive with the delivered OBS/CONTACT picture")
def test_s3_shore_shows_the_contact(story):
    assert story.pictures[story.claim_s // 60 * 60 + 60].contacts


def test_s4_cannot_hold_on_departure(story):
    assert story.cannot_hold_s == DEPART_S  # it leaves at 6 kn, faster than a boat at 2.3 m/s
    assert DEPART_S <= story.released_s <= DEPART_S + 60


@pytest.mark.xfail(reason="#17: the cannot-hold report needs the shore contact picture")
def test_s4_shore_keeps_the_contact_after_it_leaves(story):
    assert story.pictures[DEPART_S + 60].contacts


def test_s5_uncovered_picket_stays_visible_to_the_end(story):
    opened = next(t for t, state in story.pick_s_states if state == RELEASED)
    assert FAIL_S <= opened
    assert all(state == RELEASED for t, state in story.pick_s_states if t >= opened)


def test_s6_rejoin_converges_every_table():
    world = build_world(ROOT, "elysa", 3, warm_s=60)
    warm_up(world)
    start = world.warm_ms + 120_000
    while world.next_tick_ms < start:
        world.step()
    others = (0, 1, 2, 4, 5)
    for peer in others:
        world.inject({"kind": "link_off", "a": 3, "b": peer or "shore"}, start)
        world.inject({"kind": "link_off", "a": peer, "b": 3}, start)
    world.inject({"kind": "battery_low", "boat": 1}, start + 1000)
    while world.next_tick_ms <= start + 120_000:
        world.step()
    assert world.nodes[3].table.recs != world.nodes[2].table.recs  # split: 3 missed the repair
    back = world.next_tick_ms
    for peer in others:
        world.inject({"kind": "link_on", "a": 3, "b": peer or "shore"}, back)
        world.inject({"kind": "link_on", "a": peer, "b": 3}, back)
    while world.next_tick_ms <= back + 90_000:
        world.step()
    live = [world.nodes[b].table.recs for b in (2, 3, 4, 5)]
    assert all(recs == live[0] for recs in live)
    assert world.shore.table.recs == live[0]
    for task in seg_tasks(world):
        assert live[0][task].state == CLAIMED and live[0][task].owner != 1
