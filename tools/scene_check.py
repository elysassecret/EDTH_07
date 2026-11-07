"""Re-measure the scene against the plan. Owner: D.

    uv run python -m tools.scene_check
    uv run python -m tools.scene_check --land <path to land.geojson>

Prints segments, stations (water, lane band), the radio graph at both ranges, when the return
rule fires, and the pre-event worst age at both speeds after warm-up. All values are truth from
config and the scene; nothing here is hull or radio test data.
"""

import argparse
import json
from pathlib import Path

from shapely.geometry import LineString, Point, shape

from contract.geo import dist, to_xy
from eval.metrics import (
    interval_lengths_m,
    km_overdue,
    seg_ages_s,
    task_lengths_m,
    worst_age_ms,
)
from eval.run_batch import run_config
from eval.warm import build_world, warm_up
from world.routes import load_scene

ROOT = Path(__file__).resolve().parent.parent
LAND = ROOT / "web/public/geo/land.geojson"
STATIONS = {"pick:N": 3, "pick:S": 4, "relay": 5}
C07 = (55.4505, 10.8706)
SPEEDS = (2300, 3000)


def hops_from_shore(points: dict, shore, boat_m: int, shore_m: int) -> dict[int, int | None]:
    """Radio hops from shore per node; None if unreachable. Breadth first over range only."""
    hops: dict[int, int | None] = dict.fromkeys(points)
    frontier = [n for n, p in sorted(points.items()) if dist(p, shore) <= shore_m]
    for n in frontier:
        hops[n] = 1
    while frontier:
        n = frontier.pop(0)
        for m, p in sorted(points.items()):
            if hops[m] is None and dist(p, points[n]) <= boat_m:
                hops[m] = hops[n] + 1
                frontier.append(m)
    return hops


def land_polygons(path: Path) -> list:
    if not path.exists():
        return []
    return [shape(f["geometry"]) for f in json.loads(path.read_text(encoding="utf-8"))["features"]]


def pre_event_ages(speed: int) -> dict:
    """Seed 1 after warm-up, at the tick before the first failure."""
    world = build_world(ROOT, "off", 1, speed_mm_s=speed)
    warm_up(world)
    end = world.params.repair_off_after_ms - world.tick_ms
    while world.next_tick_ms <= end:
        world.step()
    km = [m / 1000 for m in interval_lengths_m(world.scene.samples, task_lengths_m(world.mission.tasks))]
    visits = world.sample_visit_ms
    target = run_config(ROOT)["revisit_target_s"] * 1000
    return {
        "worst_s": worst_age_ms(visits, world.t) // 1000,
        "km_overdue": round(km_overdue(visits, km, world.t, target), 1),
        "segments": seg_ages_s(world.scene.samples, visits, world.t),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--land", type=Path, default=LAND)
    args = parser.parse_args(argv)
    scene = load_scene(ROOT)
    world = build_world(ROOT, "off", 1, warm_s=0)
    mission, params = scene.mission, world.params

    print("== Segments ==")
    total = 0.0
    tasks = {t.id: t for t in mission.tasks}
    for tid, task in sorted(tasks.items()):
        if tid.startswith("seg:"):
            metres = LineString(task.pts).length
            total += metres
            count = sum(1 for s in scene.samples if s.task == tid)
            print(f"  {tid}  {metres / 1000:5.2f} km  {count:3d} samples")
    print(f"  total {total / 1000:.2f} km, {len(scene.samples)} samples")

    print("== Stations ==")
    land = land_polygons(args.land)
    lane = LineString(mission.lane)
    named = {t: tasks[t].pts[0] for t in STATIONS} | {"C-07": to_xy(*C07)}
    for name, point in named.items():
        lane_m = round(lane.distance(Point(point)))
        print(f"  {name:7s} lane offset {lane_m:6d} m (band {mission.lane_half_m} m), "
              f"Korsor {dist(point, mission.shore) / 1000:5.1f} km")
    if land:
        wet = {"pick:N": (55.4578, 10.9081), "pick:S": (55.3543, 11.0135),
               "relay": (55.405, 10.975), "C-07": C07}
        for name, (lat, lon) in wet.items():
            state = "LAND" if any(p.contains(Point(lon, lat)) for p in land) else "water"
            print(f"  {name:7s} {state}")
    else:
        print("  water check skipped: no coastline in this checkout (#49)")

    print("== Radio graph at the stations, hops from shore ==")
    points = {boat: tasks[t].pts[0] for t, boat in STATIONS.items()}
    shore_m = world.radio_config.shore_m
    for boat_m in (8000, 4000):
        hops = hops_from_shore(points, mission.shore, boat_m, shore_m)
        print(f"  boat radio {boat_m} m, shore {shore_m} m: {hops}")

    print("== Return rule, farthest point of each boat's initial work ==")
    for boat in mission.boats:
        mine = [tasks[k] for k, owner in mission.initial if owner == boat]
        far = max(dist(p, mission.shore) for t in mine for p in t.pts)
        home_s = far * 1000 / params.speed_mm_s
        fires = (params.endurance_ms / 1000
                 - params.return_safety_permille / 1000 * (home_s + params.reserve_ms / 1000))
        print(f"  boat {boat}: {far / 1000:5.1f} km from Korsor, {home_s:6.0f} s home in still "
              f"water, rule fires by {fires:6.0f} s of cruise")

    print("== Pre-event ages, seed 1, after warm-up, at T-1 ==")
    for speed in SPEEDS:
        row = pre_event_ages(speed)
        print(f"  {speed} mm/s: worst {row['worst_s']} s, km overdue {row['km_overdue']}")
        print(f"    {row['segments']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
