"""Friday re-measure: python -m tools.scene_check

Prints segments, station distances, the radio graph at the stations, lane offsets,
pre-event worst age per boat at both speeds, and the return limit per boat.
"""
from __future__ import annotations

import math

from contract.config import MODES, load
from eval.metrics import Metrics
from world import geo
from world.routes import lane_offset_m, load_scene
from world.sim import Sim


def main():
    cfg = load()
    sc = load_scene(cfg)
    print("== Segments (clipped public approximate lines, <= %d m) ==" % cfg["scene"]["segment_max_m"])
    tot = 0
    for s in sc.segments:
        print(f"  {s.task:9s} {s.cable:22s} {s.length_m/1000:5.2f} km  {len(s.samples):3d} samples")
        tot += s.length_m
    print(f"  total {tot/1000:.1f} km, {len(sc.samples)} samples at {cfg['scene']['sample_step_m']} m")
    print("== Stations ==")
    st = {"shore (Korsor)": sc.shore_xy, "relay station": sc.relay_xy, "picket N": sc.picket_n, "picket S": sc.picket_s}
    for a, pa in st.items():
        row = []
        for b, pb in st.items():
            if a != b:
                row.append(f"{b} {geo.dist(pa, pb)/1000:5.1f} km")
        inb = geo.in_box(*pa)
        off = lane_offset_m(sc, pa)
        print(f"  {a:14s} in box={inb!s:5s} lane offset {off/1000:4.2f} km | " + ", ".join(row))
    print("== Radio graph at the stations (boat %d m, shore %d m) ==" % (cfg["radio"]["boat_m"], cfg["radio"]["shore_m"]))
    sim = Sim(load(overrides=MODES["elysa"]), "elysa", 1, use_ais=False)
    hops = sim.radio.shore_reach()
    print("  hops from shore:", hops, "| links:", sim.radio.graph())
    print("== Return limit per boat (endurance - reserve - trip home at the farthest point of its tour) ==")
    V = cfg["boat"]["speed_mps"]
    for b, a in sim.agents.items():
        pts = [p for e in a.tour for p in a.mission.tasks[e[0]].points] or [sim.radio.positions[b]]
        far = max(geo.dist(p, sc.shore_xy) for p in pts)
        lim = cfg["boat"]["endurance_s"] - cfg["boat"]["reserve_s"] - far / V
        print(f"  boat {b}: farthest point {far/1000:5.1f} km from Korsor -> return rule fires by t = {lim:6.0f} s at {V} m/s")
    for speed in (cfg["boat"]["speed_mps"], 3.0):
        ov = dict(MODES["off"])
        ov["boat.speed_mps"] = speed
        c = load(overrides=ov)
        s = Sim(c, "off", 1, use_ais=False)
        m = Metrics(s)
        s.observers.append(m)
        s.run_warm()
        s.run_until(7199)
        ages = m.seg_age(s.t)
        print(f"== Pre-event worst age at {speed} m/s (seed 1, t = 7199 s): {max(ages.values())} s; per segment {ages}")
        print(f"   km overdue against {c['run']['revisit_target_s']} s target: {m.km_overdue(s.t):.1f}")
    print("== Chart check (by eye): stations and C-07 in WGS84 ==")
    for name, p in {**st, "C-07": geo.ll_to_xy(55.4505, 10.8706)}.items():
        lat, lon = geo.xy_to_ll(*p)
        print(f"  {name:14s} {lat:.5f} N {lon:.5f} E")
    print("No water mask is loaded: confirm every station is water on a chart before the demo.")


if __name__ == "__main__":
    main()
