"""Build web/public/geo/depth.geojson and depth_bands.geojson from EMODnet (issues #9, #89).
Owner: D.

    uv run --with rasterio python -m tools.prepare_depth --cache <folder outside the repo>
    uv run --with rasterio python -m tools.prepare_depth --cache <...> --check <png outside web/>

Source: EMODnet Bathymetry DTM (2024 release, 1/16 arc minute, about 115 m here), fetched once
through its WCS for the scene box plus margin into the cache; later runs work offline. The
EMODnet contour layer itself only carries 50 m and deeper levels, and the Great Belt is shallower
than that, so the contours are drawn here with matplotlib at the levels below.

`depth.geojson`: FeatureCollection, EPSG:4326, `[lon, lat]`, one LineString per contour piece
with `{"depth_m": n, "source": ..., "licence": ...}`, simplified in local metres to about 20 m and
rounded to 1e-5 degrees, under 1 MB. For the zoomed-in chart.

`depth_bands.geojson` (#89): filled bands for the box-scale chart, where seven labelled line
levels are too loud. Four bands, 0 to 10, 10 to 20, 20 to 30 and deeper than 30 m, one
(Multi)Polygon per band with `{"depth_min_m", "depth_max_m" (null for the open deepest band),
"source", "licence"}`, simplified to about 50 m, under 500 kB. Land (elevation above 0) is in no
band. `--check <png>` draws the bands over the satellite image `s2_box.png` so the shore can be
checked by eye.

Credit: "EMODnet Bathymetry Consortium (2024): EMODnet Digital Bathymetry (DTM)", CC BY 4.0.
"""

import argparse
import gzip
import json
import urllib.parse
import urllib.request
from math import cos, radians
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web/public/geo/depth.geojson"
BANDS_OUT = ROOT / "web/public/geo/depth_bands.geojson"
SATELLITE = ROOT / "web/public/geo/s2_box.png"
SATELLITE_CORNERS = ROOT / "web/public/geo/s2_box.json"
WCS = "https://ows.emodnet-bathymetry.eu/wcs"
COVERAGE = "emodnet__mean"
MARGIN_DEG = (0.16, 0.09)  # same window as the satellite image
LEVELS_M = (5, 10, 15, 20, 30, 40, 50)
SOURCE = "EMODnet Bathymetry DTM 2024, 1/16 arc minute, via WCS"
LICENCE = "EMODnet Bathymetry Consortium (2024): EMODnet Digital Bathymetry (DTM), CC BY 4.0"
METRES_PER_DEGREE = 111_320
SIMPLIFY_M = 20
MIN_LENGTH_M = 300  # drop contour crumbs the console cannot read
MAX_BYTES = 1_000_000
BAND_EDGES_M = (0, 10, 20, 30)  # the last band is open: deeper than 30 m
BANDS_SIMPLIFY_M = 50
BANDS_MIN_AREA_M2 = 50_000  # drop specks smaller than about four grid cells
BANDS_MAX_BYTES = 500_000
DEEPEST_M = 10_000  # upper edge for contourf only; written as null


def window() -> tuple[float, float, float, float]:
    scene = json.loads((ROOT / "data/scene-coordinates.json").read_text(encoding="utf-8"))
    corners = scene["box"]["corners_wgs84"].values()
    lons = [c["lon"] for c in corners]
    lats = [c["lat"] for c in corners]
    dx, dy = MARGIN_DEG
    return min(lons) - dx, min(lats) - dy, max(lons) + dx, max(lats) + dy


def fetch_dtm(bbox, cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    local = cache / "emodnet_dtm_box.tif"
    if local.exists():
        return local
    w, s, e, n = bbox
    q = {"service": "WCS", "version": "2.0.1", "request": "GetCoverage",
         "coverageId": COVERAGE, "format": "image/tiff"}
    url = f"{WCS}?{urllib.parse.urlencode(q)}&subset=Long({w},{e})&subset=Lat({s},{n})"
    print(f"fetching {url}")
    with urllib.request.urlopen(url, timeout=300) as r:
        data = r.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    if data[:2] not in (b"II", b"MM"):
        raise SystemExit("WCS did not return a TIFF: " + data[:200].decode(errors="replace"))
    local.write_bytes(data)
    return local


def read_depth(dtm: Path):
    """(lon, lat, depth) cell centres; depth is minus elevation, so land is negative."""
    import numpy as np
    import rasterio

    with rasterio.open(dtm) as src:
        z = src.read(1).astype(float)
        t = src.transform
        rows, cols = z.shape
        lon = t.c + t.a * (np.arange(cols) + 0.5)
        lat = t.f + t.e * (np.arange(rows) + 0.5)
    return lon, lat, -z


def contours(dtm: Path):
    """Yield (depth_m, LineString in degrees) from the DTM."""
    import matplotlib
    from shapely.geometry import LineString

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    lon, lat, depth = read_depth(dtm)
    fig, ax = plt.subplots()
    cs = ax.contour(lon, lat, depth, levels=list(LEVELS_M))
    for level, path_list in zip(cs.levels, cs.allsegs, strict=True):
        for seg in path_list:
            if len(seg) >= 2:
                yield round(level), LineString(seg)
    plt.close(fig)


def bands(dtm: Path):
    """Yield (min_m, max_m or None, geometry in degrees), one filled area per depth band.

    Each contourf path holds every ring of its band; nested rings (water, island, pond) are
    resolved even-odd, which is what the fill looks like on the matplotlib plot.
    """
    import matplotlib
    from shapely.geometry import Polygon

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    lon, lat, depth = read_depth(dtm)
    edges = [*BAND_EDGES_M, DEEPEST_M]
    fig, ax = plt.subplots()
    cs = ax.contourf(lon, lat, depth, levels=edges)
    paths = cs.get_paths()
    if len(paths) != len(edges) - 1:
        raise SystemExit(f"contourf gave {len(paths)} paths for {len(edges) - 1} bands")
    for lo, hi, path in zip(edges[:-1], edges[1:], paths, strict=True):
        area = Polygon()
        for ring in path.to_polygons(closed_only=True):
            if len(ring) >= 4:
                area = area.symmetric_difference(Polygon(ring).buffer(0))
        yield lo, (None if hi == DEEPEST_M else hi), area
    plt.close(fig)


def to_local(geom, kx: float, ky: float):
    from shapely import affinity
    return affinity.scale(geom, kx, ky, origin=(0, 0))


def to_degrees(geom, kx: float, ky: float):
    from shapely import affinity
    return affinity.scale(geom, 1 / kx, 1 / ky, origin=(0, 0))


def band_features(dtm: Path, kx: float, ky: float) -> list[dict]:
    from shapely import make_valid, set_precision
    from shapely.geometry import MultiPolygon, mapping

    feats = []
    for lo, hi, area in bands(dtm):
        local = to_local(area, kx, ky)
        parts = getattr(local, "geoms", [local])
        keep = [p for p in parts if p.geom_type == "Polygon" and p.area >= BANDS_MIN_AREA_M2]
        local = MultiPolygon(keep).simplify(BANDS_SIMPLIFY_M)
        back = make_valid(set_precision(to_degrees(local, kx, ky), 1e-5))
        polys = [g for g in getattr(back, "geoms", [back]) if g.geom_type == "Polygon"]
        polys += [p for g in getattr(back, "geoms", []) if g.geom_type == "MultiPolygon"
                  for p in g.geoms]
        if not polys:
            continue
        geom = polys[0] if len(polys) == 1 else MultiPolygon(polys)
        feats.append({"type": "Feature",
                      "properties": {"depth_min_m": lo, "depth_max_m": hi,
                                     "source": SOURCE, "licence": LICENCE},
                      "geometry": mapping(geom)})
    return feats


def draw_check(feats: list[dict], out: Path) -> None:
    """Bands over the satellite image, for a by-eye check of the shore line."""
    import matplotlib
    import numpy as np

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.patches import Patch
    from shapely.geometry import shape

    corners = json.loads(SATELLITE_CORNERS.read_text(encoding="utf-8"))["coordinates"]
    lons = [c[0] for c in corners]
    lats = [c[1] for c in corners]
    img = plt.imread(SATELLITE)
    colours = ["#9ecae1", "#6baed6", "#3182bd", "#08519c"]
    fig, ax = plt.subplots(figsize=(12, 12 * img.shape[0] / img.shape[1]), dpi=110)
    ax.imshow(img, extent=(min(lons), max(lons), min(lats), max(lats)), aspect="auto")
    handles = []
    for f, col in zip(feats, colours, strict=False):
        g = shape(f["geometry"])
        for p in getattr(g, "geoms", [g]):
            x, y = p.exterior.xy
            ax.fill(np.asarray(x), np.asarray(y), color=col, alpha=0.35, lw=0)
            ax.plot(np.asarray(x), np.asarray(y), color=col, lw=0.6)
            for hole in p.interiors:
                hx, hy = hole.xy
                ax.plot(np.asarray(hx), np.asarray(hy), color=col, lw=0.6)
        p = f["properties"]
        label = (f"{p['depth_min_m']} to {p['depth_max_m']} m" if p["depth_max_m"] is not None
                 else f"deeper than {p['depth_min_m']} m")
        handles.append(Patch(color=col, alpha=0.6, label=label))
    ax.set_xlim(min(lons), max(lons))
    ax.set_ylim(min(lats), max(lats))
    ax.legend(handles=handles, loc="lower left")
    ax.set_title("depth_bands.geojson over s2_box.png (EMODnet DTM 2024, Sentinel-2 2026-05-25)")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    print(f"check image -> {out}")


def main() -> None:
    from shapely import set_precision
    from shapely.geometry import LineString, mapping

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, required=True, help="folder outside the repo")
    ap.add_argument("--check", type=Path, help="write the band overlay check image here")
    a = ap.parse_args()
    bbox = window()
    dtm = fetch_dtm(bbox, a.cache)
    mid_lat = (bbox[1] + bbox[3]) / 2
    kx = METRES_PER_DEGREE * cos(radians(mid_lat))
    ky = METRES_PER_DEGREE
    feats = []
    for depth_m, line in contours(dtm):
        local = LineString([(x * kx, y * ky) for x, y in line.coords])
        if local.length < MIN_LENGTH_M:
            continue
        simple = local.simplify(SIMPLIFY_M)
        back = LineString([(x / kx, y / ky) for x, y in simple.coords])
        back = set_precision(back, 1e-5)
        if back.is_empty or len(back.coords) < 2:
            continue
        feats.append({"type": "Feature",
                      "properties": {"depth_m": depth_m, "source": SOURCE, "licence": LICENCE},
                      "geometry": mapping(back)})
    feats.sort(key=lambda f: (f["properties"]["depth_m"], f["geometry"]["coordinates"][0]))
    fc = {"type": "FeatureCollection", "features": feats}
    text = json.dumps(fc, separators=(",", ":")) + "\n"
    if len(text.encode()) > MAX_BYTES:
        raise SystemExit(f"depth.geojson is {len(text.encode())} bytes, over {MAX_BYTES}")
    OUT.write_bytes(text.encode())  # LF on Windows too
    by = {}
    for f in feats:
        by[f["properties"]["depth_m"]] = by.get(f["properties"]["depth_m"], 0) + 1
    print(f"{len(feats)} contour lines, {len(text.encode()) / 1e3:.0f} kB -> {OUT.name}; "
          f"lines per level {by}")

    band_feats = band_features(dtm, kx, ky)
    text = json.dumps({"type": "FeatureCollection", "features": band_feats},
                      separators=(",", ":")) + "\n"
    if len(text.encode()) > BANDS_MAX_BYTES:
        raise SystemExit(f"depth_bands.geojson is {len(text.encode())} bytes, "
                         f"over {BANDS_MAX_BYTES}")
    BANDS_OUT.write_bytes(text.encode())  # LF on Windows too
    print(f"{len(band_feats)} depth bands, {len(text.encode()) / 1e3:.0f} kB -> {BANDS_OUT.name}")
    if a.check:
        draw_check(band_feats, a.check)
    print(LICENCE)


if __name__ == "__main__":
    main()
