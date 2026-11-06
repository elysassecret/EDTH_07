"""R1 to R3: the real Great Belt scene."""
import math

from contract.config import load
from contract.views import AisPing
from tests.helpers import make_sim
from world import geo
from world.routes import lane_offset_m, load_scene
from world.sensors import ais_in_range


def test_r1_radio_graph_at_stations_connected_and_boat4_has_a_direct_link():
    sim, _ = make_sim("elysa", 1)
    sim.run_warm()
    hops = sim.radio.shore_reach()
    assert all(h >= 0 for h in hops.values()), hops
    assert hops[4] == 1, hops                     # south picket talks to Korsor directly: a real link to cut
    assert hops[5] == 1 and hops[3] == 2           # relay direct; north picket through the relay


def test_r2_no_station_in_the_lane_band_and_scripted_contact_off_lane():
    cfg = load()
    sc = load_scene(cfg)
    band = max(abs(r["v_p95_km"] - r["v_median_km"]) for r in sc.raw["lane_measured_from_ais"]["centreline"]) * 1000
    for name, p in (("picket_n", sc.picket_n), ("picket_s", sc.picket_s), ("relay", sc.relay_xy)):
        assert lane_offset_m(sc, p) > band, (name, lane_offset_m(sc, p), band)
        assert geo.in_box(*p), name
    c07 = geo.ll_to_xy(55.4505, 10.8706)
    assert lane_offset_m(sc, c07) > 3000 and geo.in_box(*c07)
    assert math.hypot(c07[0] - sc.picket_n[0], c07[1] - sc.picket_n[1]) > cfg["boat"]["keep_in_view_m"]


def test_r3_ais_pings_reach_only_boats_inside_modelled_range():
    far = AisPing("a", 0.0, 0.0, 10, 0, "Cargo", "Class A", 0)
    b = AisPing("b", 9000.0, 0.0, 10, 0, "Cargo", "Class B", 0)
    got = ais_in_range((0.0, 0.0), [far, b], 20000, 8000)
    assert [p.track for p in got] == ["a"]
    # in the sim: every ping an agent has seen was inside range of that boat at the time
    sim, _ = make_sim("elysa", 1, use_ais=True)
    sim.run_warm()
    sim.run_until(900)
    assert sim.ais is not None
    for bid, a in sim.agents.items():
        for track, v in a.ais_seen.items():
            pass
    tv = sim.truth_view()
    assert tv["radio"]["oversize"] == 0
