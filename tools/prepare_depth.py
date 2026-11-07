"""Build web/public/geo/depth.geojson, depth contours of the scene box, from EMODnet (issue #9).
Owner: D.

    uv run --with rasterio python -m tools.prepare_depth --cache <folder outside the repo>

Source: EMODnet Bathymetry DTM (2024 release, 1/16 arc minute, about 115 m here), fetched once
through its WCS for the scene box plus margin into the cache; later runs work offline. The
EMODnet contour layer itself only carries 50 m and deeper levels, and the Great Belt is shallower
than that, so the contours are drawn here with matplotlib at the levels below. Output: GeoJSON
FeatureCollection, EPSG:4326, `[lon, lat]`, one LineString per contour piece with
`{"depth_m": n, "source": ..., "licence": ...}`, simplified in local metres to about 20 m and
rounded to 1e-5 degrees, under 1 MB. Credit: "EMODnet Bathymetry Consortium (2024): EMODnet
Digital Bathymetry (DTM)", CC BY 4.0.
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


def contours(dtm: Path):
    """Yield (depth_m, LineString in degrees) from the DTM. Depth is minus elevation."""
    import matplotlib
    import numpy as np
    import rasterio
    from shapely.geometry import LineString

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    with rasterio.open(dtm) as src:
        z = src.read(1).astype(float)
        t = src.transform
        rows, cols = z.shape
        lon = t.c + t.a * (np.arange(cols) + 0.5)
        lat = t.f + t.e * (np.arange(rows) + 0.5)
    depth = -z
    fig, ax = plt.subplots()
    cs = ax.contour(lon, lat, depth, levels=list(LEVELS_M))
    for level, path_list in zip(cs.levels, cs.allsegs, strict=True):
        for seg in path_list:
            if len(seg) >= 2:
                yield round(level), LineString(seg)
    plt.close(fig)


def main() -> None:
    from shapely import set_precision
    from shapely.geometry import LineString, mapping

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, required=True, help="folder outside the repo")
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
    OUT.write_text(text, encoding="utf-8")
    by = {}
    for f in feats:
        by[f["properties"]["depth_m"]] = by.get(f["properties"]["depth_m"], 0) + 1
    print(f"{len(feats)} contour lines, {len(text.encode()) / 1e3:.0f} kB -> {OUT.name}; "
          f"lines per level {by}")
    print(LICENCE)


if __name__ == "__main__":
    main()
