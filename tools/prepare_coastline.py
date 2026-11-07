"""Build web/public/geo/land.geojson and infra.geojson from OSM (issue #9). Owner: D.

    uv run python -m tools.prepare_coastline --cache <folder outside the repo>

The first run fetches OSM `natural=coastline` ways and the Great Belt Bridge from Overpass into
the cache; later runs work offline. The window is the scene box plus a margin, so Korsor and
Sprogo are on the map. Coastlines cut the window into faces, and OSM keeps land on the left of
every coastline way, so each segment votes on the faces beside it. Simplifying works in local
metres (longitude scaled by the cosine of the mid latitude), then rounds to 1e-5 degrees.
"""

import argparse
import itertools
import json
import urllib.parse
import urllib.request
from math import cos, hypot, radians
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box, mapping
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web/public/geo/land.geojson"
INFRA = ROOT / "web/public/geo/infra.geojson"
OVERPASS = "https://overpass-api.de/api/interpreter"
AGENT = "edth07-coastline/1.0"
LICENCE = "© OpenStreetMap contributors, ODbL"
SOURCE = "OpenStreetMap natural=coastline via Overpass"
METRES_PER_DEGREE = 111_320
FETCH_MARGIN_DEG = 0.1  # ways are fetched wider than the window, so no way ends inside it
MAX_BYTES = 1_000_000
OFFSET_DEG = 1e-6  # about 10 cm: well inside the face beside a coastline segment
MIN_BRIDGE_M = 1_000  # shorter motorway bridges are road overpasses on land


def window(margin_km: float) -> tuple[float, float, float, float]:
    """(lon_min, lat_min, lon_max, lat_max): the scene box corners plus a margin."""
    data = json.loads((ROOT / "data/scene-coordinates.json").read_text(encoding="utf-8"))
    corners = data["box"]["corners_wgs84"].values()
    lats, lons = [c["lat"] for c in corners], [c["lon"] for c in corners]
    d_lat = margin_km * 1000 / METRES_PER_DEGREE
    d_lon = d_lat / cos(radians((min(lats) + max(lats)) / 2))
    return min(lons) - d_lon, min(lats) - d_lat, max(lons) + d_lon, max(lats) + d_lat


def fetch(cache: Path, name: str, query: str) -> dict:
    path = cache / name
    if not path.exists():
        body = urllib.parse.urlencode({"data": query}).encode()
        request = urllib.request.Request(OVERPASS, body, {"User-Agent": AGENT})
        with urllib.request.urlopen(request, timeout=180) as response:
            path.write_bytes(response.read())
    return json.loads(path.read_text(encoding="utf-8"))


def ways(raw: dict) -> list[LineString]:
    lines = []
    for way in sorted(raw["elements"], key=lambda e: e["id"]):
        coords = [(p["lon"], p["lat"]) for p in way.get("geometry", [])]
        if len(coords) >= 2:
            lines.append(LineString(coords))
    return lines


def land_faces(lines: list[LineString], bounds) -> list[Polygon]:
    """Each coastline segment votes: the face on its left is land, on its right is water."""
    frame = box(*bounds)
    inside = [g for g in (line.intersection(frame) for line in lines) if not g.is_empty]
    faces = list(polygonize(unary_union([*inside, frame.boundary])))
    tree = STRtree(faces)
    votes = [0] * len(faces)
    for piece in inside:
        for line in getattr(piece, "geoms", [piece]):
            for a, b in itertools.pairwise(line.coords):
                dx, dy = b[0] - a[0], b[1] - a[1]
                size = hypot(dx, dy)
                if size == 0:
                    continue
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                nx, ny = -dy / size * OFFSET_DEG, dx / size * OFFSET_DEG
                for sign in (1, -1):
                    point = Point(mx + sign * nx, my + sign * ny)
                    for i in tree.query(point, predicate="within"):
                        votes[i] += sign
    return [face for face, vote in zip(faces, votes, strict=True) if vote > 0]


def simplified(faces: list[Polygon], metres: float, mid_lat: float) -> list[Polygon]:
    k = cos(radians(mid_lat))
    flat = shapely.transform(unary_union(faces), lambda c: c * [k, 1])
    small = shapely.transform(
        flat.simplify(metres / METRES_PER_DEGREE), lambda c: np.round(c / [k, 1], 5)
    )
    small = small if small.is_valid else make_valid(small)
    parts = [g for g in getattr(small, "geoms", [small]) if isinstance(g, Polygon)]
    return sorted((p for p in parts if not p.is_empty), key=lambda p: -p.area)


def land_collection(polygons: list[Polygon]) -> dict:
    properties = {"source": SOURCE, "licence": LICENCE}
    features = [
        {"type": "Feature", "properties": properties, "geometry": mapping(p)} for p in polygons
    ]
    return {"type": "FeatureCollection", "features": features}


def bridge_collection(raw: dict) -> dict:
    """The two long motorway spans over the belt; OSM names them after the road."""
    features = []
    for way in sorted(raw["elements"], key=lambda e: e["id"]):
        coords = [[round(p["lon"], 5), round(p["lat"], 5)] for p in way.get("geometry", [])]
        if len(coords) >= 2 and LineString(coords).length * METRES_PER_DEGREE >= MIN_BRIDGE_M:
            properties = {
                "kind": "bridge",
                "name": "Great Belt Bridge",
                "source": "OpenStreetMap",
                "licence": LICENCE,
            }
            geometry = {"type": "LineString", "coordinates": coords}
            features.append({"type": "Feature", "properties": properties, "geometry": geometry})
    return {"type": "FeatureCollection", "features": features}


def write_json(path: Path, data: dict) -> int:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return len(text.encode())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--cache", type=Path, required=True, help="folder outside the repo")
    parser.add_argument("--margin-km", type=float, default=10.0)
    parser.add_argument("--simplify-m", type=float, default=20.0)
    args = parser.parse_args(argv)
    args.cache.mkdir(parents=True, exist_ok=True)
    bounds = window(args.margin_km)
    west, south, east, north = bounds
    m = FETCH_MARGIN_DEG
    bbox = f"{south - m},{west - m},{north + m},{east + m}"
    coast = fetch(
        args.cache,
        "coastline.json",
        f'[out:json][timeout:120];way["natural"="coastline"]({bbox});out geom;',
    )
    faces = land_faces(ways(coast), bounds)
    polygons = simplified(faces, args.simplify_m, (south + north) / 2)
    size = write_json(OUT, land_collection(polygons))
    print(f"{OUT.name}: {len(polygons)} polygons, {size} bytes, window {bounds}")
    bridge = fetch(
        args.cache,
        "bridge.json",
        f'[out:json][timeout:60];way["bridge"]["highway"="motorway"]({bbox});out geom;',
    )
    print(f"{INFRA.name}: {write_json(INFRA, bridge_collection(bridge))} bytes")
    if size >= MAX_BYTES:
        print(f"too big: raise --simplify-m (limit {MAX_BYTES} bytes)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
