"""Coast and contact constraints must hold on the same final navigation leg."""

from itertools import pairwise

import pytest

from agent import water


def test_real_scene_route_obeys_coast_and_contact_at_once():
    start, goal = (-1971, -8069), (-5715, -5690)
    circles = (((-4578, -8501), 1852),)
    route = water.path_around(start, goal, circles)
    assert route and route[0] == start and route[-1] == goal
    for a, b in pairwise(route):
        assert not water.blocked(a, b)
        assert water.clear_of_circles(a, b, circles)
    assert route == water.path_around(start, goal, circles)


def test_synthetic_scene_routes_around_contacts_without_the_great_belt_coast():
    circles = (((0, 0), 1852), ((2000, 0), 1000))
    route = water.path_around((-5000, 0), (5000, 0), circles, coast=False)
    assert len(route) > 2
    assert all(water.clear_of_circles(a, b, circles) for a, b in pairwise(route))


@pytest.mark.parametrize("end,allowed", [((3000, 0), True), ((-3000, 0), False),
                                        ((500, 0), False), ((1000, 0), False)])
def test_a_boat_first_observed_inside_a_ring_can_only_escape_outward(end, allowed):
    assert water.clear_of_circles((1000, 0), end, (((0, 0), 1852),)) is allowed


def test_no_safe_route_is_explicit_not_a_segment_through_the_contact():
    assert water.path_around((-5000, 0), (0, 0), (((0, 0), 1852),), coast=False) == []


def test_disconnected_coast_graph_never_falls_back_to_driving_through_land():
    saved = water.OBSTACLES, water.NODES, water.EDGES
    try:
        water.load((((0, 0), (1000, 0), (1000, 1000), (0, 1000), (0, 0)),), (), ())
        start, end = (-200, 500), (1200, 500)
        assert water.blocked(start, end)
        assert water.path(start, end) == []
        assert water.home_path(start, end) == []
    finally:
        water.load(*saved)
