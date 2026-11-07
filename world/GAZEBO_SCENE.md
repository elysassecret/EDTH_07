# Whole-environment native Gazebo view

`world/gazebo_scene.py` replaces the **single-boat view** with a native Gazebo scene
of the complete local Great Belt mission. This is a **read-only evaluator truth
visualization of Python World**, not a Gazebo-authoritative six-degree-of-freedom
physics backend. The existing simulation, sensors, agents, radio, energy model,
failures, reset, replay and console remain unchanged.

## Start

Gazebo must already be installed locally. No model/Fuel downloads are used.
Verified locally with Gazebo Sim **8.15.0** on macOS.

1. Keep the existing real simulator/console running (do not start a second copy on
   the same port). If it is not running, from the repo root:

   ```bash
   uv run python -m server --serve-web
   ```

2. Start the full scene and mirror, also from the repo root:

   ```bash
   uv run python -m world.gazebo_scene --launch-server --gui
   ```

   On macOS this launches **two separate processes**, `gz sim -s -r …` and
   `gz sim -g`, rather than the unsupported combined server/GUI invocation.
   The Python process owns only the Gazebo children it starts. Ctrl+C stops those
   display processes, not the existing Python simulation server. Closing a GUI launched
   this way also ends its owned display server/mirror; it does not stop the source.

3. Use the existing console at http://127.0.0.1:8765/ for mission Run/Pause/reset
   and injections. A source already at its horizon will display its final state;
   reset/resume from the console if a new moving run is desired. The mirror never
   resets or unpauses the source automatically.

To attach the GUI in a separate terminal instead:

```bash
# Terminal 2: display server + mirror
uv run python -m world.gazebo_scene --launch-server --overlays
# Terminal 3: GUI, matching the display partition and loopback interface
GZ_IP=127.0.0.1 GZ_PARTITION=edth07_fleet gz sim -g
```

For another simulator port, pass `--feed ws://127.0.0.1:PORT/truth`. `/shore` is
rejected: this is an explicitly truth-only view, not the operator's delivered picture.
Use the same checkout/config/assets as the simulator. Never feed this display state
back into an agent or `/shore`.

## What is present

- All five configured USVs, following actual snapshot positions and headings.
- All current contacts from the actual `/truth` feed, including AIS when that
  simulator supplies it; no extra ships are invented or loaded from a private CSV.
- Seven configured cable segments, chosen lane boundary and mission box.
- Korsør shore node, picket and relay station markers.
- Local coastline geometry, extruded as schematic land volumes with holes retained.
- Local infrastructure/bridge geometry, with schematic elevations.
- Existing depth-band polygons as stepped midpoint surfaces where a closed depth
  range is available; open-ended ranges have no invented midpoint surface.
- Physical radio links from truth: blue up, red cut, grey down where supplied. These
  are evaluator links, not what the shore has heard. `--gui` enables these overlays;
  use `--overlays` when attaching the GUI manually.
- A cyan sphere above shore denotes received truth frames; a red cube denotes a
  lost/stalled feed (also logged as FEED LOST). Mission clock/modes/battery remain
  in the console; Ogre2 does not support the native TEXT marker type in this build.
- Native orbit/select/follow controls. Select `usv_01` … `usv_05` through Gazebo's
  entity tree/context menu to follow a particular boat.

The local `web/public/geo/` assets are read, not modified. Generated SDF, COLLADA meshes,
manifest and process logs go to `/tmp/edth07-gazebo-fleet/` by default. They reference
only local files, not online tiles, fonts or Fuel assets. OSM/EMODnet attribution is
retained in `manifest.json`. Missing optional assets are explicitly listed there.

## Important visual/model boundaries

- Positions use `contract.geo.to_xy`, the **same local origin as World**. This is not
  the old canvas viewer's separate approximate projection.
- Heading is converted from navigation bearing to Gazebo ENU yaw. No roll, pitch,
  heave, waves, sensor noise, new bathymetry or calibrated hull physics are fabricated.
- Hulls, cables, station glyphs and bridge heights are **schematic**. Hull display
  scale defaults to 20 for overview visibility; use `--vessel-scale 1` for unexaggerated
  proxy dimensions. These are not claims about actual vessel dimensions or clearance.
- Gazebo physics only carries kinematic display proxies. Its clock/play controls do
  not advance the mission. Mission time and physical decisions come from Python World.
- Delivered radio status, assignments, batteries and decisions remain in the existing console;
  this is not a second command/approval implementation.
- New contacts are created once; departed contacts and contacts removed by reset are
  hidden. Their model names are hashed identifiers, not interpreted commands.
- The mirror coalesces updates and reconnects to the feed. Feed closure or a three-second
  receipt timeout freezes the last poses and logs **FEED LOST**; it never extrapolates motion. Service failures are
  logged as **not live**, not silently treated as successful rendering.
- Restart the mirror if the Gazebo server itself is restarted. Optional assets or the
  native Gazebo executable are not required by normal Python tests.

## Export / regression checks

```bash
uv run python -m world.gazebo_scene --export-only
# If Gazebo is installed:
gz sdf -k /tmp/edth07-gazebo-fleet/fleet.sdf
uv run pytest -q tests/world/test_gazebo_scene.py
```

The older `world/gazebo.py` two-waypoint harness and `world/gazebo_stage1.sdf` are
separate work; this whole-scene module does not overwrite them.
