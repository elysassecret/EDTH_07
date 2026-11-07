"""Build web/public/geo/s2_box.png and s2_box.json from Sentinel-2 L2A true colour (issue #9).
Owner: D.

    uv run --with rasterio python -m tools.prepare_satellite --cache <folder outside the repo>

Source: Copernicus Sentinel-2 L2A true-colour image (TCI), read as a cloud-optimised GeoTIFF from
the public AWS Open Data mirror (`sentinel-cogs`, found through the Element84 Earth Search STAC
API, no account needed). The scene is chosen by STAC query: lowest tile cloud cover, no missing
pixels, inside the search window, and it must cover the whole scene box plus margin in one tile.
Pass `--item` to pin a scene by id, which is what the committed file was made with.

The image is warped to EPSG:4326, north up, cropped to the scene box plus a margin, scaled to
`--max-px` on the long side and written as PNG. `s2_box.json` holds the four corners of the PNG
in `[lon, lat]`, in the order top-left, top-right, bottom-right, bottom-left, which is exactly
what the console's image layer expects. Credit: "Contains modified Copernicus Sentinel data 2026".
rasterio is a tool-only dependency and stays out of pyproject.
"""

import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "web/public/geo/s2_box.png"
META = ROOT / "web/public/geo/s2_box.json"
STAC = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = "sentinel-2-l2a"
MARGIN_DEG = (0.16, 0.09)  # about 10 km in lon and lat at 55.4 N
CREDIT = "Contains modified Copernicus Sentinel data 2026"


def window() -> tuple[float, float, float, float]:
    """Scene box corners plus margin: (min lon, min lat, max lon, max lat)."""
    scene = json.loads((ROOT / "data/scene-coordinates.json").read_text(encoding="utf-8"))
    corners = scene["box"]["corners_wgs84"].values()
    lons = [c["lon"] for c in corners]
    lats = [c["lat"] for c in corners]
    dx, dy = MARGIN_DEG
    return min(lons) - dx, min(lats) - dy, max(lons) + dx, max(lats) + dy


def covers(item: dict, bbox: tuple[float, float, float, float]) -> bool:
    w, s, e, n = item["bbox"][:4]
    return w <= bbox[0] and s <= bbox[1] and e >= bbox[2] and n >= bbox[3]


def search(bbox, start: str, end: str, item_id: str | None) -> dict:
    body = {
        "collections": [COLLECTION],
        "bbox": list(bbox),
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
        "query": {"eo:cloud_cover": {"lt": 5}},
        "limit": 200,
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
    }
    if item_id:
        body["ids"] = [item_id]
        body.pop("query")
    req = urllib.request.Request(
        STAC, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        items = json.load(r)["features"]
    good = [
        i for i in items
        if covers(i, bbox) and i["properties"].get("s2:nodata_pixel_percentage", 100) < 1
    ]
    if not good:
        raise SystemExit("no single-tile cloud-free scene covers the window; widen the dates")
    return good[0]


def build(item: dict, bbox, max_px: int, cache: Path | None) -> None:
    import numpy as np
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    from rasterio.windows import from_bounds

    href = item["assets"]["visual"]["href"]
    src_path = href
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        local = cache / f"{item['id']}_TCI.tif"
        if not local.exists():
            print(f"downloading {href} to {local}")
            urllib.request.urlretrieve(href, local)
        src_path = str(local)
    w, s, e, n = bbox
    with (
        rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"),
        rasterio.open(src_path) as src,
        WarpedVRT(src, crs="EPSG:4326", resampling=Resampling.bilinear) as vrt,
    ):
        win = from_bounds(w, s, e, n, vrt.transform)
        scale = max_px / max(win.width, win.height)
        shape = (3, round(win.height * scale), round(win.width * scale))
        data = vrt.read(window=win, out_shape=shape, resampling=Resampling.bilinear)
        bounds = vrt.window_bounds(win)
    img = np.moveaxis(data, 0, -1)
    Image.fromarray(img, "RGB").save(PNG, optimize=True)
    w, s, e, n = bounds
    corners = [[round(x, 5), round(y, 5)] for x, y in ((w, n), (e, n), (e, s), (w, s))]
    META.write_text(json.dumps({"coordinates": corners}) + "\n", encoding="utf-8")
    p = item["properties"]
    print(f"{item['id']} {p['datetime'][:10]} cloud {p['eo:cloud_cover']:.3f}% "
          f"{shape[2]}x{shape[1]} px, {PNG.stat().st_size / 1e6:.1f} MB -> {PNG.name}, {META.name}")
    print(f"corners TL TR BR BL: {json.loads(META.read_text())['coordinates']}")
    print(CREDIT)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, default=None, help="folder outside the repo for the TCI")
    ap.add_argument("--item", default=None, help="STAC item id to pin, e.g. S2A_32UPG_20260525_1_L2A")
    ap.add_argument("--start", default="2025-04-01")
    ap.add_argument("--end", default="2026-10-31")
    ap.add_argument("--max-px", type=int, default=2400)
    a = ap.parse_args()
    bbox = window()
    item = search(bbox, a.start, a.end, a.item)
    build(item, bbox, a.max_px, a.cache)


if __name__ == "__main__":
    main()
