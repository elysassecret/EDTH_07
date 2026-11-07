"""Native Gazebo view of the complete local scene and the existing /truth feed.

This is an evaluator visualization, NOT a second physics backend. Python World
remains authoritative. No agent input, command, radio or shore snapshot is changed.
All geometry/resources are local; no Fuel models, online tiles or private CSV needed.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import shutil
import signal
import subprocess
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path

import numpy as np
from shapely import transform
from shapely.geometry import Polygon, shape
from shapely.ops import triangulate

from contract.geo import to_xy
from world.routes import load_scene

WORLD_NAME = "edth07_fleet"
ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger(__name__)
HIDDEN_Z = -1_000_000


def tag(parent, element, text=None, **attrs):
    node = ET.SubElement(parent, element, attrs)
    if text is not None:
        node.text = str(text)
    return node


def xml_write(node, path):
    ET.indent(node)
    ET.ElementTree(node).write(path, encoding="utf-8", xml_declaration=True)


def material(visual, colour):
    mat = tag(visual, "material")
    tag(mat, "ambient", colour)
    tag(mat, "diffuse", colour)


def model(parent, name, pose="0 0 0 0 0 0", moving=False):
    node = tag(parent, "model", name=name)
    tag(node, "pose", pose)
    tag(node, "static", "false" if moving else "true")
    link = tag(node, "link", name="body")
    if moving:
        # Kinematic display proxy, no calibrated mass or Gazebo propulsion claim.
        tag(link, "kinematic", "true")
        tag(link, "gravity", "false")
    return node, link


def visual(link, name, kind, dimensions, colour, pose="0 0 0 0 0 0"):
    node = tag(link, "visual", name=name)
    tag(node, "pose", pose)
    geom = tag(node, "geometry")
    item = tag(geom, kind)
    for key, value in dimensions.items():
        tag(item, key, value)
    material(node, colour)
    alpha = float(colour.split()[-1])
    if alpha < 1:
        tag(node, "transparency", 1 - alpha)
    return node


def line(link, name, a, b, z, width, colour):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 0.01:
        return
    visual(
        link,
        name,
        "box",
        {"size": f"{length} {width} {width}"},
        colour,
        f"{(a[0] + b[0]) / 2} {(a[1] + b[1]) / 2} {z} 0 0 {math.atan2(dy, dx)}",
    )


def vessel(parent, name, scale, ais=False, contact=False):
    node, link = model(parent, name, f"0 0 {HIDDEN_Z} 0 0 0", moving=True)
    colour = "0.15 0.8 0.45 1" if ais else "1 0.55 0.12 1" if contact else "0.15 0.55 0.95 1"
    for side in (-1, 1):
        visual(
            link,
            f"hull_{side}",
            "box",
            {"size": f"{4.8 * scale} {0.5 * scale} {0.5 * scale}"},
            colour,
            f"0 {side * scale} {0.1 * scale} 0 0 0",
        )
    visual(
        link,
        "deck",
        "box",
        {"size": f"{2.6 * scale} {2.2 * scale} {0.3 * scale}"},
        "0.85 0.9 0.95 1",
        f"0 0 {0.5 * scale} 0 0 0",
    )
    visual(
        link,
        "mast",
        "cylinder",
        {"radius": 0.08 * scale, "length": 1.6 * scale},
        "1 0.8 0.1 1",
        f"{0.5 * scale} 0 {1.3 * scale} 0 0 0",
    )
    # The orange bow makes the model's +X / forward direction visible.
    visual(
        link,
        "bow",
        "box",
        {"size": f"{0.6 * scale} {1.8 * scale} {0.2 * scale}"},
        "1 0.55 0.1 1",
        f"{1.5 * scale} 0 {0.8 * scale} 0 0 0",
    )
    return node


def polygons(geometry):
    if geometry.geom_type == "Polygon":
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from polygons(part)


def projected(geometry):
    # Same rounded local-metre projection as World, never a second map origin.
    return transform(
        shape(geometry),
        lambda coords: np.array(
            [to_xy(lat, lon) for lon, lat in coords],
            dtype=float,
        ).reshape((-1, 2)),
    )


def mesh_file(polys, path, height):
    """Local COLLADA triangles, with holes retained. Height is schematic or band midpoint."""
    points = []
    for poly in polys:
        for tri in triangulate(poly):
            if poly.covers(tri):
                points.extend((x, y, height) for x, y in list(tri.exterior.coords)[:3])
        # Vertical coastline walls make land read as a volume instead of a map decal.
        if height > 0:
            for ring in (poly.exterior, *poly.interiors):
                for a, b in pairwise(ring.coords):
                    points.extend(
                        [
                            (a[0], a[1], -2),
                            (b[0], b[1], -2),
                            (b[0], b[1], height),
                            (a[0], a[1], -2),
                            (b[0], b[1], height),
                            (a[0], a[1], height),
                        ]
                    )
    if not points:
        return False
    dae = ET.Element(
        "COLLADA", xmlns="http://www.collada.org/2005/11/COLLADASchema", version="1.4.1"
    )
    asset = tag(dae, "asset")
    tag(asset, "unit", name="meter", meter="1")
    tag(asset, "up_axis", "Z_UP")
    geometry = tag(tag(dae, "library_geometries"), "geometry", id="geometry")
    mesh = tag(geometry, "mesh")
    source = tag(mesh, "source", id="positions")
    tag(
        source,
        "float_array",
        " ".join(str(v) for p in points for v in p),
        id="positions-array",
        count=str(len(points) * 3),
    )
    accessor = tag(
        tag(source, "technique_common"),
        "accessor",
        source="#positions-array",
        count=str(len(points)),
        stride="3",
    )
    for axis in "XYZ":
        tag(accessor, "param", name=axis, type="float")
    vertices = tag(mesh, "vertices", id="vertices")
    tag(vertices, "input", semantic="POSITION", source="#positions")
    triangles = tag(mesh, "triangles", count=str(len(points) // 3))
    tag(triangles, "input", semantic="VERTEX", source="#vertices", offset="0")
    tag(triangles, "p", " ".join(str(i) for i in range(len(points))))
    scene = tag(tag(dae, "library_visual_scenes"), "visual_scene", id="scene")
    tag(tag(scene, "node", id="land"), "instance_geometry", url="#geometry")
    tag(tag(dae, "scene"), "instance_visual_scene", url="#scene")
    xml_write(dae, path)
    return True


def export_scene(root: Path, out: Path, vessel_scale=20.0):
    """Generate the whole offline scene, without changing any existing user SDF."""
    if not math.isfinite(vessel_scale) or vessel_scale <= 0:
        raise ValueError("vessel scale must be positive and finite")
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    scene = load_scene(root)
    sdf = ET.Element("sdf", version="1.9")
    world = tag(sdf, "world", name=WORLD_NAME)
    physics = tag(world, "physics", name="display", type="ignored")
    tag(physics, "max_step_size", "0.01")
    tag(physics, "real_time_factor", "1")
    for library, system in [
        ("physics", "Physics"),
        ("user-commands", "UserCommands"),
        ("scene-broadcaster", "SceneBroadcaster"),
    ]:
        tag(
            world, "plugin", filename=f"gz-sim-{library}-system", name=f"gz::sim::systems::{system}"
        )
    tag(world, "scene")
    light = tag(world, "light", name="sun", type="directional")
    tag(light, "pose", "0 0 20000 0 0 0")
    tag(light, "diffuse", "0.9 0.9 0.9 1")
    tag(light, "direction", "-0.3 0.2 -0.9")
    xs, ys = zip(*scene.boundary, strict=True)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    gui = tag(world, "gui", fullscreen="false")
    plugin = tag(gui, "plugin", filename="MinimalScene", name="3D View")
    settings = tag(plugin, "gz-gui")
    tag(settings, "title", "Great Belt | EVALUATOR TRUTH | Python World physics")
    tag(settings, "property", "true", type="bool", key="showTitleBar")
    tag(settings, "property", "docked", type="string", key="state")
    tag(settings, "property", "1000", type="double", key="width")
    tag(settings, "property", "700", type="double", key="height")
    tag(plugin, "engine", "ogre2")
    tag(plugin, "scene", "scene")
    tag(plugin, "ambient_light", "0.5 0.5 0.5")
    tag(plugin, "background_color", "0.08 0.15 0.23")
    tag(
        plugin, "camera_pose", f"{cx} {cy - span} {span * 0.9} 0 {math.atan2(0.9, 1)} {math.pi / 2}"
    )
    clip = tag(plugin, "camera_clip")
    tag(clip, "near", "1")
    tag(clip, "far", "200000")
    for filename in (
        "GzSceneManager",
        "InteractiveViewControl",
        "CameraTracking",
        "EntityContextMenuPlugin",
        "SelectEntities",
        "EntityTree",
        "MarkerManager",
    ):
        child = tag(gui, "plugin", filename=filename, name=filename)
        settings = tag(child, "gz-gui")
        tag(settings, "property", "false", type="bool", key="showTitleBar")
        tag(
            settings,
            "property",
            "docked" if filename == "EntityTree" else "floating",
            type="string",
            key="state",
        )
        if filename != "EntityTree":
            tag(settings, "property", "5", type="double", key="width")
            tag(settings, "property", "5", type="double", key="height")

    _, sea = model(world, "sea_surface_schematic")
    visual(
        sea,
        "water",
        "box",
        {"size": f"{span * 3} {span * 3} 0.1"},
        "0.04 0.25 0.4 0.45",
        f"{cx} {cy} -0.3 0 0 0",
    )
    boundary = Polygon(scene.boundary).buffer(2500)
    attribution = set()
    missing = []
    for filename in ("land.geojson", "depth_bands.geojson"):
        path = root / "web/public/geo" / filename
        if not path.exists():
            missing.append(filename)
            continue
        data = json.loads(path.read_text())
        for index, feature in enumerate(data.get("features", [])):
            properties = feature.get("properties", {})
            if properties.get("licence"):
                attribution.add(properties["licence"])
            geom = projected(feature["geometry"])
            if not geom.is_valid:
                geom = geom.buffer(0)
            geom = geom.intersection(boundary)
            land = filename == "land.geojson"
            # Existing bathymetry ranges, not fabricated high-resolution terrain.
            if not land and properties.get("depth_max_m") is None:
                missing.append(
                    f"{filename} feature {index}: open-ended range has no midpoint surface"
                )
                continue
            height = 3 if land else -(properties["depth_min_m"] + properties["depth_max_m"]) / 2
            name = f"{'land' if land else 'depth_band'}_{index}"
            file = out / f"{name}.dae"
            if mesh_file(list(polygons(geom)), file, height):
                _, link = model(world, name)
                colour = "0.28 0.4 0.22 1" if land else "0.07 0.18 0.25 1"
                visual(link, "surface", "mesh", {"uri": file.as_uri()}, colour)

    _, routes = model(world, "cables_lane_and_boundary_schematic")
    for task in scene.mission.tasks:
        if task.id.startswith("seg:"):
            colour = "0.9 0.15 0.65 1" if task.id.startswith("seg:H:") else "0.55 0.35 0.9 1"
            for i, (a, b) in enumerate(pairwise(task.pts)):
                line(routes, f"{task.id.replace(':', '_')}_{i}", a, b, 0.2, 10, colour)
        else:
            _, link = model(
                world, task.id.replace(":", "_"), f"{task.pts[0][0]} {task.pts[0][1]} 0 0 0 0"
            )
            visual(link, "buoy", "cylinder", {"radius": 20, "length": 10}, "1 0.75 0.1 1")
    ring = (*scene.boundary, scene.boundary[0])
    for i, (a, b) in enumerate(pairwise(ring)):
        line(routes, f"boundary_{i}", a, b, 0.4, 5, "0.9 0.9 0.9 1")
    if len(scene.mission.lane) >= 2:
        from shapely.geometry import LineString

        lane = LineString(scene.mission.lane).buffer(scene.mission.lane_half_m)
        for i, (a, b) in enumerate(pairwise(lane.exterior.coords)):
            line(routes, f"lane_{i}", a, b, 0.6, 5, "1 0.8 0.2 1")
    _, shore = model(
        world, "Korsor_shore_node_0", f"{scene.mission.shore[0]} {scene.mission.shore[1]} 0 0 0 0"
    )
    visual(shore, "station", "box", {"size": "70 50 60"}, "0.9 0.35 0.2 1", "0 0 30 0 0 0")
    infra = root / "web/public/geo/infra.geojson"
    if infra.exists():
        _, bridge = model(world, "infrastructure_schematic_not_clearance_data")
        for i, feature in enumerate(json.loads(infra.read_text()).get("features", [])):
            geom = projected(feature["geometry"])
            if geom.geom_type == "LineString":
                pts = list(geom.coords)
                for j, (a, b) in enumerate(pairwise(pts)):
                    line(bridge, f"infra_{i}_{j}", a, b, 18, 20, "0.65 0.68 0.7 1")
    else:
        missing.append("infra.geojson")
    for boat in scene.mission.boats:
        vessel(world, f"usv_{boat:02d}", vessel_scale)
    file = out / "fleet.sdf"
    xml_write(sdf, file)
    manifest = {
        "world": WORLD_NAME,
        "backend": "read-only evaluator truth visualization",
        "physics_authority": "existing Python World; not Gazebo hydrodynamics",
        "boat_ids": list(scene.mission.boats),
        "shore_xy": list(scene.mission.shore),
        "cable_segments": [t.id for t in scene.mission.tasks if t.id.startswith("seg:")],
        "vessel_display_scale": vessel_scale,
        "missing_assets": missing,
        "attribution": sorted(attribution),
        "limitations": [
            "land/bridge heights and model dimensions schematic, not collision/clearance data",
            "depth-band midpoint surfaces, not resolved bathymetry",
            "no invented roll, pitch, heave, waves or AIS vessels",
            "Gazebo clock is not the authoritative mission clock; use console controls",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return file, manifest


def contact_name(track):
    return "contact_" + hashlib.sha256(str(track).encode()).hexdigest()[:16]


def pose_text(name, x, y, heading, z=0):
    if not all(math.isfinite(float(v)) for v in (x, y, heading, z)):
        raise ValueError("pose coordinates must be finite")
    yaw = math.pi / 2 - math.radians(heading)
    return f"name: {json.dumps(name)} position {{x:{x} y:{y} z:{z}}} orientation {{z:{math.sin(yaw / 2)} w:{math.cos(yaw / 2)}}}"


def marker_text(frame, shore, feed_lost=False):
    """GUI-only radio links and a feed-status beacon; no agent-visible geometry.

    Ogre2 in the installed rendering8 build does not support TEXT markers. Use
    the entity tree and console for IDs/clock, not a falsely successful text RPC.
    """
    markers = ['marker { ns:"edth07_truth" action:DELETE_ALL }']
    shape_name = "BOX" if feed_lost else "SPHERE"
    colour = "r:1 g:0.15 b:0.1" if feed_lost else "r:0.1 g:0.8 b:0.9"
    markers.append(
        f'marker {{ns:"edth07_truth" id:1 action:ADD_MODIFY type:{shape_name} '
        f"pose {{position {{x:{shore[0]} y:{shore[1]} z:250}}}} "
        f"scale {{x:120 y:120 z:120}} material {{diffuse {{{colour} a:1}}}} }}"
    )
    positions = {0: shore}
    positions.update({boat["id"]: (boat["x"], boat["y"]) for boat in frame["boats"]})
    for index, (state, colour) in enumerate(
        [("up", "r:0.2 g:0.6 b:1"), ("cut", "r:1 g:0.2 b:0.2"), ("down", "r:0.5 g:0.5 b:0.5")],
        50000,
    ):
        points = []
        for link in frame.get("links", []):
            if link["state"] == state and link["a"] in positions and link["b"] in positions:
                for endpoint in (link["a"], link["b"]):
                    x, y = positions[endpoint]
                    points.append(f"point {{x:{x} y:{y} z:40}}")
        if points:
            markers.append(
                f'marker {{ns:"edth07_truth" id:{index} action:ADD_MODIFY type:LINE_LIST '
                f"material {{diffuse {{{colour} a:1}}}} {' '.join(points)} }}"
            )
    return " ".join(markers)


class GazeboClient:
    def __init__(self, partition, scale, boat_ids=(), overlays=False, shore=(0, 0)):
        self.env = {**os.environ, "GZ_PARTITION": partition, "GZ_IP": "127.0.0.1"}
        self.overlays = overlays
        self.shore = shore
        self.last_frame = None
        self.last_markers = None
        self.marker_warning = False
        self.scale = scale
        self.contacts = set()
        self.boats = {f"usv_{boat:02d}" for boat in boat_ids}
        self.visible = set()
        self.last_poses = None

    def request(self, operation, reqtype, text):
        result = subprocess.run(
            [
                "gz",
                "service",
                "-s",
                operation if operation.startswith("/") else f"/world/{WORLD_NAME}/{operation}",
                "--reqtype",
                reqtype,
                "--reptype",
                "gz.msgs.Boolean",
                "--timeout",
                "2000",
                "--req",
                text,
            ],
            env=self.env,
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        if result.returncode or "data: true" not in result.stdout:
            raise RuntimeError(f"Gazebo {operation} failed: {result.stdout} {result.stderr}")

    def update(self, frame):
        if frame.get("view") != "truth":
            raise ValueError("only explicit evaluator truth frames are accepted")
        poses = []
        visible = set()
        for boat in frame["boats"]:
            name = f"usv_{int(boat['id']):02d}"
            if name not in self.boats:
                sdf = ET.Element("sdf", version="1.9")
                vessel(sdf, name, self.scale)
                self.request(
                    "create",
                    "gz.msgs.EntityFactory",
                    f"sdf: {json.dumps(ET.tostring(sdf, encoding='unicode'))}",
                )
                self.boats.add(name)
            visible.add(name)
            poses.append(pose_text(name, boat["x"], boat["y"], boat.get("hdg", 0)))
        for contact in frame.get("contacts", []):
            name = contact_name(contact["id"])
            if name not in self.contacts:
                sdf = ET.Element("sdf", version="1.9")
                vessel(sdf, name, self.scale * 2, ais=bool(contact.get("ais")), contact=True)
                self.request(
                    "create",
                    "gz.msgs.EntityFactory",
                    f"sdf: {json.dumps(ET.tostring(sdf, encoding='unicode'))}",
                )
                self.contacts.add(name)
            visible.add(name)
            poses.append(pose_text(name, contact["x"], contact["y"], contact.get("cog", 0)))
        for absent in sorted(self.visible - visible):
            poses.append(pose_text(absent, 0, 0, 0, HIDDEN_Z))
        message = " ".join(f"pose {{{p}}}" for p in poses)
        if poses and message != self.last_poses:
            self.request("set_pose_vector", "gz.msgs.Pose_V", message)
            self.last_poses = message
        self.visible = visible
        self.last_frame = frame
        self.markers()

    def markers(self, feed_lost=False):
        if not self.overlays or self.last_frame is None:
            return
        text = marker_text(self.last_frame, self.shore, feed_lost)
        if text == self.last_markers:
            return
        try:
            self.request("/marker_array", "gz.msgs.Marker_V", text)
            self.last_markers = text
            self.marker_warning = False
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            if not self.marker_warning:
                LOG.warning("GUI overlays unavailable; pose mirror is separate: %s", error)
            self.marker_warning = True


async def mirror(feed, client, hz, children=()):
    from websockets.asyncio.client import connect
    from websockets.exceptions import ConnectionClosed, InvalidHandshake

    queue = asyncio.Queue(maxsize=1)
    connected = asyncio.Event()
    native_lock = asyncio.Lock()

    async def receive():
        while True:
            try:
                async with connect(feed, max_size=8_000_000) as socket:
                    LOG.info("Connected to evaluator /truth; never forwarded to agents or shore")
                    while True:
                        raw = await asyncio.wait_for(socket.recv(), timeout=3)
                        frame = json.loads(raw)
                        if (
                            isinstance(frame, dict)
                            and frame.get("view") == "truth"
                            and "boats" in frame
                        ):
                            connected.set()
                            if queue.full():
                                queue.get_nowait()
                            queue.put_nowait(frame)
            except (OSError, ValueError, ConnectionClosed, InvalidHandshake) as error:
                # Viewer reconnect only; no simulation reset or fabricated movement.
                connected.clear()
                if not queue.empty():
                    queue.get_nowait()
                LOG.warning("FEED LOST: display poses frozen; reconnecting: %s", error)
                async with native_lock:
                    await asyncio.to_thread(client.markers, True)
                await asyncio.sleep(1)

    async def display():
        last_time = None
        while True:
            frame = await queue.get()
            try:
                async with native_lock:
                    if not connected.is_set():
                        continue
                    await asyncio.to_thread(client.update, frame)
                if frame.get("t") != last_time:
                    LOG.info(
                        "Truth t=%ss: %d USVs, %d contacts",
                        frame.get("t"),
                        len(frame["boats"]),
                        len(frame.get("contacts", [])),
                    )
                    last_time = frame.get("t")
            except (RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
                LOG.error("Display update failed (not live): %s", error)
            await asyncio.sleep(1 / hz)

    async def watch_children():
        while True:
            for child in children:
                if child.poll() is not None:
                    raise RuntimeError(
                        f"Gazebo display process {child.pid} exited ({child.returncode}); see display logs"
                    )
            await asyncio.sleep(1)

    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(receive())
        tasks.create_task(display())
        if children:
            tasks.create_task(watch_children())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, default=Path("/tmp/edth07-gazebo-fleet"))
    parser.add_argument("--feed", default="ws://127.0.0.1:8765/truth")
    parser.add_argument("--partition", default="edth07_fleet")
    parser.add_argument("--vessel-scale", type=float, default=20)
    parser.add_argument("--hz", type=float, default=2)
    parser.add_argument("--export-only", action="store_true")
    parser.add_argument(
        "--overlays",
        action="store_true",
        help="Native GUI radio links and feed-status beacon; also enabled by --gui",
    )
    parser.add_argument("--launch-server", action="store_true")
    parser.add_argument(
        "--gui", action="store_true", help="Launch GUI in its own process (macOS safe)"
    )
    args = parser.parse_args()
    if not math.isfinite(args.hz) or args.hz <= 0:
        parser.error("hz must be positive and finite")
    if not args.feed.rstrip("/").endswith("/truth"):
        parser.error("feed must explicitly select /truth, never /shore")
    file, manifest = export_scene(args.root, args.out, args.vessel_scale)
    print(json.dumps(manifest, indent=2), flush=True)
    print(f"Scene: {file}", flush=True)
    if args.export_only:
        return
    if not shutil.which("gz"):
        parser.error("Gazebo is not installed; --export-only works without it")
    env = {**os.environ, "GZ_PARTITION": args.partition, "GZ_IP": "127.0.0.1"}
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    children = []
    logs = []
    try:
        if args.launch_server:
            log = (file.parent / "server.log").open("w")
            logs.append(log)
            children.append(
                subprocess.Popen(
                    ["gz", "sim", "-s", "-r", str(file)], env=env, stdout=log, stderr=log
                )
            )
        if args.gui:
            log = (file.parent / "gui.log").open("w")
            logs.append(log)
            children.append(subprocess.Popen(["gz", "sim", "-g"], env=env, stdout=log, stderr=log))
        print(
            f"GUI (separate process): GZ_IP=127.0.0.1 GZ_PARTITION={args.partition} gz sim -g",
            flush=True,
        )
        print(
            "Read-only TRUTH view. Use the existing console for mission Run/Pause/reset.",
            flush=True,
        )
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        asyncio.run(
            mirror(
                args.feed,
                GazeboClient(
                    args.partition,
                    args.vessel_scale,
                    manifest["boat_ids"],
                    overlays=args.gui or args.overlays,
                    shore=manifest["shore_xy"],
                ),
                args.hz,
                children,
            )
        )
    except KeyboardInterrupt:
        pass
    finally:
        for child in reversed(children):
            child.terminate()
        for child in reversed(children):
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()
