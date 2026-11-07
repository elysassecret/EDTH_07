# tools/ — owner: D

Scene checks and helper scripts.

Rule: only D edits files here. Others open an issue or ask in chat.

| Script | What |
|---|---|
| `scene_check.py` | Friday re-measure: lengths, stations, radio graph, return limits |
| `prepare_coastline.py` | `web/public/geo/land.geojson`, `infra.geojson` from OSM (#9). Credit "© OpenStreetMap contributors" (ODbL) |
| `prepare_satellite.py` | `web/public/geo/s2_box.png`, `s2_box.json` from Sentinel-2 L2A true colour (#9). Run with `uv run --with rasterio python -m tools.prepare_satellite --cache <outside repo>`; rasterio is tool-only. Committed file: scene `S2A_32UPG_20260525_1_L2A`, 2026-05-25, tile cloud cover 0.006 %, 20 m per pixel, 2400 x 1754 px, 4.2 MB. Credit "Contains modified Copernicus Sentinel data 2026" |
| `prepare_depth.py` | `web/public/geo/depth.geojson` from the EMODnet Bathymetry DTM via WCS (#9). Run with `uv run --with rasterio python -m tools.prepare_depth --cache <outside repo>`. Levels 5, 10, 15, 20, 30, 40, 50 m, 247 lines, 211 kB. Credit "EMODnet Bathymetry Consortium (2024): EMODnet Digital Bathymetry (DTM)", CC BY 4.0 |
