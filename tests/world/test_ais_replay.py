"""Tests for AIS replay and class-dependent reception range filtering (#52)."""

from pathlib import Path

from ais.replay import AisReplay, ais_in_range
from contract.constants import PATROL
from contract.geo import dist, to_lonlat
from contract.mission import Action, Detection, Mission, Own, Params
from world.sim import World

ROOT = Path(__file__).resolve().parents[2]


class RecordingAgent:
    def __init__(self, boat: int, mission: Mission, params: Params):
        self.boat = boat
        self.seen_by_tick: dict[int, tuple[Detection, ...]] = {}

    def step(
        self, t: int, own: Own, seen: tuple[Detection, ...], inbox: list[bytes]
    ) -> tuple[Action, list[bytes]]:
        self.seen_by_tick[t] = seen
        return Action(PATROL, None, 0), []


def _write_clip(path: Path, rows: list[dict]) -> Path:
    fieldnames = [
        "ts_file",
        "vessel_hash",
        "lat",
        "lon",
        "sog_kn",
        "cog_deg",
        "heading_deg",
        "nav_status",
        "ship_type",
        "ais_class",
        "length_band_m",
    ]
    lines = [",".join(fieldnames)]
    for row in rows:
        lines.append(",".join(str(row.get(col, "")) for col in fieldnames))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_ais_replay_filters_by_class_range_and_time_window(tmp_path: Path):
    lon_0, lat_0 = to_lonlat(0, 0)
    lon_6k, lat_6k = to_lonlat(6_000, 0)
    lon_15k, lat_15k = to_lonlat(15_000, 0)
    lon_25k, lat_25k = to_lonlat(25_000, 0)

    clip = _write_clip(
        tmp_path / "ais.csv",
        [
            {
                "ts_file": "2026-11-03T10:15:01",
                "vessel_hash": "V-B-IN",
                "lat": f"{lat_6k:.6f}",
                "lon": f"{lon_6k:.6f}",
                "sog_kn": "8.0",
                "cog_deg": "90",
                "ship_type": "Fishing",
                "ais_class": "Class B",
                "length_band_m": "20",
            },
            {
                "ts_file": "2026-11-03T10:15:01",
                "vessel_hash": "V-B-OUT",
                "lat": f"{lat_15k:.6f}",
                "lon": f"{lon_15k:.6f}",
                "sog_kn": "8.0",
                "cog_deg": "180",
                "ship_type": "Pleasure",
                "ais_class": "Class B",
                "length_band_m": "15",
            },
            {
                "ts_file": "2026-11-03T10:15:01",
                "vessel_hash": "V-A-IN",
                "lat": f"{lat_15k:.6f}",
                "lon": f"{lon_15k:.6f}",
                "sog_kn": "12.5",
                "cog_deg": "270",
                "ship_type": "Cargo",
                "ais_class": "Class A",
                "length_band_m": "180",
            },
            {
                "ts_file": "2026-11-03T10:15:01",
                "vessel_hash": "V-A-OUT",
                "lat": f"{lat_25k:.6f}",
                "lon": f"{lon_25k:.6f}",
                "sog_kn": "14.0",
                "cog_deg": "45",
                "ship_type": "Tanker",
                "ais_class": "Class A",
                "length_band_m": "220",
            },
        ],
    )
    replay = AisReplay(clip, "2026-11-03T10:15:00")
    assert replay.available
    assert replay.count_in_window(0, 1_000) == 4
    assert replay.between(1_000, 2_000) == ()

    in_range = replay.for_boat((0, 0), 0, 1_000, class_a_m=20_000, class_b_m=8_000)
    assert [ping.track for ping in in_range] == ["V-A-IN", "V-B-IN"]
    dets = replay.detections_for_boat((0, 0), 0, 1_000, class_a_m=20_000, class_b_m=8_000)
    assert [det.track for det in dets] == ["V-A-IN", "V-B-IN"]
    assert all(det.ais for det in dets)
    assert ais_in_range((0, 0), replay.between(0, 1_000), 20_000, 8_000) == in_range
    assert (lon_0, lat_0) is not None


def test_world_feeds_only_in_range_ais_pings_to_boat_sensors(tmp_path: Path):
    base = World(ROOT, seed=1)
    b1_x, b1_y = base.boats[1].point
    lon_near, lat_near = to_lonlat(b1_x + 5_000, b1_y)
    lon_mid, lat_mid = to_lonlat(b1_x + 15_000, b1_y)
    lon_far, lat_far = to_lonlat(b1_x + 25_000, b1_y)

    clip = _write_clip(
        tmp_path / "ais.csv",
        [
            {
                "ts_file": "2026-11-03T10:15:01",
                "vessel_hash": "NEAR-B",
                "lat": f"{lat_near:.6f}",
                "lon": f"{lon_near:.6f}",
                "sog_kn": "6.0",
                "cog_deg": "90",
                "ship_type": "Fishing",
                "ais_class": "Class B",
            },
            {
                "ts_file": "2026-11-03T10:15:01",
                "vessel_hash": "MID-B",
                "lat": f"{lat_mid:.6f}",
                "lon": f"{lon_mid:.6f}",
                "sog_kn": "6.0",
                "cog_deg": "90",
                "ship_type": "Fishing",
                "ais_class": "Class B",
            },
            {
                "ts_file": "2026-11-03T10:15:01",
                "vessel_hash": "MID-A",
                "lat": f"{lat_mid:.6f}",
                "lon": f"{lon_mid:.6f}",
                "sog_kn": "11.0",
                "cog_deg": "180",
                "ship_type": "Cargo",
                "ais_class": "Class A",
            },
            {
                "ts_file": "2026-11-03T10:15:01",
                "vessel_hash": "FAR-A",
                "lat": f"{lat_far:.6f}",
                "lon": f"{lon_far:.6f}",
                "sog_kn": "13.0",
                "cog_deg": "270",
                "ship_type": "Tanker",
                "ais_class": "Class A",
            },
        ],
    )

    world = World(ROOT, seed=1, agent_factory=RecordingAgent, ais_clip=clip)
    world.step()  # t = 0
    world.step()  # t = 1000 ms
    seen_b1 = world.nodes[1].seen_by_tick[1_000]
    assert {det.track for det in seen_b1} == {"MID-A", "NEAR-B"}
    assert {ping.track for ping in world.ais_pings_for_boat(1)} == {"MID-A", "NEAR-B"}


def test_missing_ais_clip_matches_today_hashes_and_behaviour(tmp_path: Path):
    missing = tmp_path / "does-not-exist.csv"
    replay = AisReplay(missing)
    assert not replay.available
    assert replay.between(0, 60_000) == ()

    world_default = World(ROOT, seed=1, agent_factory=RecordingAgent)
    world_missing = World(ROOT, seed=1, agent_factory=RecordingAgent, ais_clip=missing)
    for _ in range(10):
        world_default.step()
        world_missing.step()
    assert world_missing.state_hash() == world_default.state_hash()


def test_real_clip_if_present_respects_boat_ranges():
    clip = ROOT / "data/ais-clip-box.csv"
    if not clip.is_file():
        return
    world = World(ROOT, seed=1, agent_factory=RecordingAgent, ais_enabled=True)
    class_a_m = world.boat_config["ais_class_a_m"]
    class_b_m = world.boat_config["ais_class_b_m"]
    for _ in range(30):
        world.step()
        for boat, state in world.boats.items():
            for ping in world.ais_pings_for_boat(boat):
                limit = class_a_m if ping.ais_class == "Class A" else class_b_m
                assert dist(state.point, ping.point) <= limit
    contacts = world.ais_contacts_view()
    assert len(contacts) > 0
    assert all(c["ais"] is True and isinstance(c["cog"], int) for c in contacts)


def test_water_routing_keeps_transits_off_sprogo_and_halsskov():
    import json

    from shapely.geometry import LineString, MultiPolygon, Polygon, shape
    from shapely.ops import unary_union

    from agent.tour import route_water_path
    from contract.geo import to_xy

    land_fc = json.loads((ROOT / "web/public/geo/land.geojson").read_text(encoding="utf-8"))

    def geom_to_xy(geom):
        g = shape(geom)
        if g.geom_type == "Polygon":
            return Polygon([to_xy(lat, lon) for lon, lat in g.exterior.coords])
        return MultiPolygon(
            [Polygon([to_xy(lat, lon) for lon, lat in p.exterior.coords]) for p in g.geoms]
        )

    land_xy = unary_union([geom_to_xy(feat["geometry"]) for feat in land_fc["features"]])
    for start, goal in (
        ((853, -5081), (-2278, -7893)),
        ((4446, -4976), (-2278, -7893)),
        ((-2278, -7893), (4446, -4976)),
        ((797, 8644), (8237, -7605)),
        ((-5528, 6491), (-2278, -7893)),
    ):
        pts = [(-2293, -7950) if p == (-2278, -7893) else p for p in route_water_path(start, goal)]
        assert LineString(pts).intersection(land_xy).length == 0.0
