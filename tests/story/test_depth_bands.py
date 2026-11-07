"""#89: the zoomed-out chart gets four quiet depth bands, not seven labelled line levels. Owner: D."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANDS = ROOT / "web/public/geo/depth_bands.geojson"
SAT = ROOT / "web/public/geo/s2_box.json"


def test_four_bands_with_edges_source_and_licence():
    fc = json.loads(BANDS.read_text(encoding="utf-8"))
    edges = [(f["properties"]["depth_min_m"], f["properties"]["depth_max_m"])
             for f in fc["features"]]
    assert edges == [(0, 10), (10, 20), (20, 30), (30, None)]
    for f in fc["features"]:
        assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")
        assert "EMODnet" in f["properties"]["source"]
        assert "CC BY 4.0" in f["properties"]["licence"]
        assert "label" not in f["properties"]  # nothing to print at box scale


def test_bands_are_small_and_inside_the_satellite_frame():
    assert BANDS.stat().st_size < 500_000
    frame = json.loads(SAT.read_text(encoding="utf-8"))["coordinates"]
    w, e = min(c[0] for c in frame), max(c[0] for c in frame)
    s, n = min(c[1] for c in frame), max(c[1] for c in frame)
    fc = json.loads(BANDS.read_text(encoding="utf-8"))
    for f in fc["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            for ring in poly:
                assert ring[0] == ring[-1]
                for lon, lat in ring:
                    assert w - 0.01 <= lon <= e + 0.01 and s - 0.01 <= lat <= n + 0.01
