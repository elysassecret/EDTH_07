# Maritime browser 3D — port 8766

This is the upgraded browser viewer, not the optional native Gazebo window.
It uses the **same Python simulation as the main dashboard**: the browser connects
to its existing `/truth` WebSocket. Port 8766 serves HTML/assets only; it does not
create agents, run a second World, or run the former single-boat background loop.

## Run

Prepare the frontend while internet/package caches are available:

```bash
pnpm --dir web install --frozen-lockfile
pnpm --dir web build
```

Keep the real dashboard server running on port 8765. If absent, start it with:

```bash
uv run python -m server --serve-web
```

Start the upgraded browser viewer:

```bash
uv run python -m world.gazebo --serve --host 127.0.0.1 --port 8766
# Equivalent asset-only server:
uv run python -m world.viewer --port 8766
```

Open **http://127.0.0.1:8766/**. Restart an older `world.gazebo --serve` process after
updating its Python code; rebuilding/reloading the frontend alone cannot replace that
old server implementation. The dashboard process does not need to be reset for this.

For a different existing simulator:

```text
http://127.0.0.1:8766/?feed=ws://127.0.0.1:PORT/truth
```

The view explicitly uses evaluator truth, not delivered operator knowledge. Use the
main dashboard for the shore picture and approval workflow. Run/Pause and the reviewed
Reset in this viewer affect that **same shared simulation**, not a separate run. An
ended run is labelled END OF RUN; it is never reset or populated automatically.

## Scene and controls

- Actual WebGL2 / Three.js meshes, not projected hull drawings on a 2D canvas.
- Procedurally modelled twin-hull USV proxies: hulls, deck, cabin glazing, rails,
  solar panel, mast, radar/sensor enclosure, navigation lights and propulsion housings.
- 3D cargo-like AIS traffic proxies and smaller non-AIS workboat proxies. Appearance
  and hull dimensions are **illustrative, not inferred identities or surveyed assets**.
- Shader-based water with moving wave normals, Fresnel sky reflection, sun glint and
  distance filtering; a procedural sky and daylight/sunset lighting. No remote texture
  or model download. Wave motion is decorative and does not alter telemetry/physics.
- Local OSM coastline, optional cached Sentinel terrain imagery, schematic terrain
  heights and bridge geometry. No fabricated
  bathymetry or measured elevation claim. Water-side berths and schematic pontoons/gangway
  share `world/harbour.json` with the simulator. The initial harbour camera faces from the
  seaward side, and meshes remain life-sized near shore; offshore enlargement is capped by
  coast/vessel clearance. Overview markers are small, crisp symbols rather than glows.
  Attribution is shown on the minimap.
- Bottom-right live north-up minimap: local land, cables, own ships, contacts and camera
  direction. Click/keyboard-activate a vessel marker to follow it in the 3D view.
- Fleet panel: choose a USV; the anchor button switches to live traffic selection.
  Drag to orbit, wheel/pinch to approach. O gives mission overview; 1–9 follows an
  available USV. The launch header reflects the shared run's shore-launch mode;
  fleet rows and the selected-vessel card show reported return and battery-swap state.
  Swap estimates use received simulation time only, freeze when paused or disconnected,
  and never declare completion without a new frame. Pending individual launches are not
  exposed by the truth feed, so an unavailable boat is not guessed to be waiting to launch.
  Controls and overlays use the same shadcn components, Inter fonts
  and neutral theme tokens as the main dashboard.
- Scene settings: wave motion, visual lighting, physical up-link lines, markers,
  exaggerated overview glyphs and an optional cable overlay. Cable lines are hidden
  in the main 3D scene by default to avoid presenting an enlarged overlay as a physical
  pipe across the water; they remain on the minimap.

All positions/headings come from received truth frames. Display-only interpolation
blends received samples over 100 ms, never predicts beyond the newest sample, and
snaps on reset/reconnect or when a straight display chord would cross the coastline/hull
clearance envelope. Before coastline data loads, samples snap instead of interpolating.
No position is shifted to hide an invalid truth frame. There is no separate vessel-physics
loop. Feed closure/stall shows FEED LOST and freezes visual
wave progression and actor updates. Renderer initialization failure is explicit rather
than silently falling back to the old canvas model. Missing optional map assets are
reported in settings, never fetched from online tiles.

## Build structure / checks

`web/viewer.html` and `web/src/viewer/` form a separate Vite entry alongside the existing
dashboard. Shared UI/theme files are imported rather than copied. Renderer animation
updates WebGL objects/uniforms outside React; only feed/HUD and throttled camera-map
state update React. Geometry is batched by material, pixel ratio is capped, and decorative
waves default off for reduced-motion preferences. These are code-level safeguards,
not a cross-device frame-rate certification.

```bash
pnpm --dir web test
pnpm --dir web build
pnpm --dir web exec playwright test tests/viewer.spec.ts
uv run pytest -q tests/world/test_harbour.py tests/world/test_browser_viewer.py tests/smoke
```

The viewer browser suite also replays snapshots generated by real agents and World
through shore launch, an injected low battery, return, swap and rejoin. It checks paused
and stalled swap estimates and a backwards-time reset; this is controlled snapshot
replay, not a live accelerated-server timing test.

Mobile layout can be checked in browser emulation; real-phone gesture, thermal and GPU
performance still require hardware testing. WebGL2 must be available. The browser
implementation does not require Gazebo to be installed.
