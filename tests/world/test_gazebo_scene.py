"""Full-scene Gazebo export/mirroring; native Gazebo is optional for these tests."""

import json
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from shapely.geometry import Polygon

from contract.geo import to_xy
from world.gazebo_scene import (
    HIDDEN_Z,
    GazeboClient,
    contact_name,
    export_scene,
    marker_text,
    mesh_file,
    pose_text,
    projected,
)

ROOT = Path(__file__).resolve().parents[2]


def test_full_scene_has_five_boats_all_cables_and_offline_geometry(tmp_path):
    file, manifest = export_scene(ROOT, tmp_path)
    world = ET.parse(file).getroot().find("world")
    names = {node.get("name") for node in world.findall("model")}
    assert {f"usv_{boat:02d}" for boat in range(1, 6)} <= names
    assert "Korsor_shore_node_0" in names
    assert {"pick_N", "pick_S", "relay"} <= names
    assert len(manifest["cable_segments"]) == 7
    assert manifest["physics_authority"].startswith("existing Python World")
    for uri in world.findall(".//uri"):
        assert uri.text.startswith("file://")
        assert Path(uri.text.removeprefix("file://")).is_file()
    assert "fuel.gazebosim" not in file.read_text()
    assert "http" not in file.read_text()
    renderer = world.find("gui/plugin[@filename='MinimalScene']/gz-gui")
    assert renderer.findtext("property[@key='state']") == "docked"
    assert float(renderer.findtext("property[@key='height']")) > 0
    for boat in range(1, 6):
        node = world.find(f"model[@name='usv_{boat:02d}']")
        assert float(node.findtext("pose").split()[2]) == HIDDEN_Z
        assert node.findtext("link/kinematic") == "true"


def test_optional_geo_assets_are_missing_not_fabricated(tmp_path):
    root = tmp_path / "root"
    for relative in ("config/scene.toml", "data/scene-coordinates.json"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    file, manifest = export_scene(root, tmp_path / "out")
    assert set(manifest["missing_assets"]) == {
        "land.geojson",
        "depth_bands.geojson",
        "infra.geojson",
    }
    assert file.exists()


def test_projection_matches_world_not_the_old_browser_viewer_origin():
    geom = projected({"type": "Point", "coordinates": [11.1303, 55.3316]})
    assert tuple(geom.coords[0]) == to_xy(55.3316, 11.1303)


def test_land_mesh_retains_holes(tmp_path):
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], holes=[[(3, 3), (6, 3), (6, 6), (3, 6)]])
    file = tmp_path / "land.dae"
    assert mesh_file([poly], file, height=0)
    ns = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
    values = list(map(float, ET.parse(file).find(".//c:float_array", ns).text.split()))
    triangles = [
        Polygon([(values[i + j], values[i + j + 1]) for j in (0, 3, 6)])
        for i in range(0, len(values), 9)
    ]
    assert all(poly.covers(triangle) for triangle in triangles)
    assert sum(triangle.area for triangle in triangles) == pytest.approx(poly.area)


class CaptureClient(GazeboClient):
    def __init__(self):
        super().__init__("test", 20, [1])
        self.calls = []

    def request(self, operation, reqtype, text):
        self.calls.append((operation, reqtype, text))


def test_truth_mirror_creates_actual_contacts_hides_departed_and_reuses_on_reset():
    client = CaptureClient()
    frame = {
        "view": "truth",
        "t": 10,
        "boats": [{"id": 1, "x": 123, "y": -456, "hdg": 90}],
        "contacts": [{"id": 'contact:"unsafe"', "x": 20, "y": 30, "cog": 0, "ais": False}],
    }
    client.update(frame)
    assert client.calls[0][0] == "create"
    assert client.calls[1][0] == "set_pose_vector"
    assert 'name: "usv_01" position {x:123 y:-456 z:0}' in client.calls[1][2]
    name = contact_name(frame["contacts"][0]["id"])
    assert "unsafe" not in name
    client.update(frame)
    assert len(client.calls) == 2  # no fake motion, no repeated subprocess for unchanged poses
    client.update({**frame, "t": 0, "contacts": []})
    assert f"z:{HIDDEN_Z}" in client.calls[-1][2]
    client.update(frame)
    assert sum(call[0] == "create" for call in client.calls) == 1
    with pytest.raises(ValueError, match="truth"):
        client.update({**frame, "view": "shore"})


def test_native_markers_use_actual_truth_links_and_flag_frozen_feed():
    frame = {
        "t": 25,
        "boats": [{"id": 1, "x": 10, "y": 20, "batt": 750, "mode": "PATROL"}],
        "contacts": [],
        "links": [{"a": 0, "b": 1, "state": "cut"}],
    }
    text = marker_text(frame, (100, 200))
    assert "type:SPHERE" in text and "type:TEXT" not in text
    assert "r:1 g:0.2 b:0.2" in text
    assert "point {x:100 y:200 z:40}" in text
    assert "point {x:10 y:20 z:40}" in text
    frozen = marker_text(frame, (100, 200), feed_lost=True)
    assert "type:BOX" in frozen and "r:1 g:0.15 b:0.1" in frozen
    assert "LIVE" not in frozen


def test_gazebo_failed_service_is_not_reported_as_live():
    client = GazeboClient("test", 20)
    result = SimpleNamespace(returncode=0, stdout="data: false", stderr="")
    with (
        patch("world.gazebo_scene.subprocess.run", return_value=result),
        pytest.raises(RuntimeError, match="failed"),
    ):
        client.request("set_pose_vector", "gz.msgs.Pose_V", "")


@pytest.mark.parametrize("scale", [0, -1, math.inf, math.nan])
def test_reject_invalid_visual_scale(tmp_path, scale):
    with pytest.raises(ValueError):
        export_scene(ROOT, tmp_path, vessel_scale=scale)


def test_pose_uses_enu_heading_and_rejects_nonfinite_coordinates():
    assert "orientation {z:0.0 w:1.0}" in pose_text("usv_01", 0, 0, 90)
    assert json.dumps("usv_01") in pose_text("usv_01", 0, 0, 0)
    with pytest.raises(ValueError):
        pose_text("usv_01", math.nan, 0, 0)
