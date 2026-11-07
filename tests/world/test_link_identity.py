"""A docked boat is not the shore node: cuts apply to directed node IDs.

Regression for the screenshot showing USV 04 direct-to-shore with a cut line that
actually ends at docked USV 01. The display labels are C's responsibility.
"""

from dataclasses import replace

import pytest

from contract.constants import UNAVAILABLE
from server.bridge import SimSource
from world.radio import Radio, RadioConfig


def test_colocated_shore_and_boat_keep_separate_link_identity():
    radio = Radio(RadioConfig(loss_permille=0), seed=1)
    positions = {0: (0, 0), 1: (0, 0), 4: (1000, 0)}
    radio.link(4, 1, False)
    radio.link(1, 4, False)
    radio.broadcast(0, 4, b"heartbeat", positions)
    assert radio.deliver(1000, positions) == {0: [b"heartbeat"]}
    assert not radio.reachable(4, 1, positions)
    assert radio.reachable(4, 0, positions)


@pytest.mark.parametrize("src,dst", [(1, 4), (4, 1), (4, 0), (0, 4)])
def test_restoring_one_direction_does_not_clear_other_cuts(src, dst):
    radio = Radio(RadioConfig(loss_permille=0), seed=1)
    cuts = {(1, 4), (4, 1), (4, 0), (0, 4)}
    for a, b in sorted(cuts):
        radio.link(a, b, False)
    radio.link(src, dst, True)
    assert radio.blocked == cuts - {(src, dst)}


def test_real_shore_snapshot_distinguishes_restored_shore_from_cut_docked_peer():
    source = SimSource(seed=1)
    world = source.world
    world.radio_config = replace(world.radio_config, loss_permille=0)
    world.reset()
    # Fixture: boat 1 is already at the dock; a low-battery event makes it UNAVAILABLE.
    world.boats[1].x_mm = world.mission.shore[0] * 1000
    world.boats[1].y_mm = world.mission.shore[1] * 1000
    world.inject({"kind": "battery_low", "a": 1}, t_ms=0)
    world.inject({"kind": "link_off", "a": 1, "b": 4}, t_ms=0)
    world.inject({"kind": "link_off", "a": 4, "b": 1}, t_ms=0)
    world.inject({"kind": "link_off", "a": 4, "b": "shore"}, t_ms=0)
    world.inject({"kind": "link_on", "a": 4, "b": "shore"}, t_ms=10_000)
    source.step(30_000)
    picture = source.snapshot("shore")
    boat4 = next(boat for boat in picture["boats"] if boat["id"] == 4)
    boat1 = next(boat for boat in picture["boats"] if boat["id"] == 1)
    assert boat1["mode"] == UNAVAILABLE
    assert boat4["link"] == "direct"
    assert boat4["via"] == 0
    links = {
        (min(link["a"], link["b"]), max(link["a"], link["b"])): link["state"]
        for link in picture["links"]
    }
    assert links[0, 4] == "up"
    assert links[1, 4] == "cut"
    assert (4, 0) not in world.radio.blocked
    assert {(1, 4), (4, 1)} <= world.radio.blocked
