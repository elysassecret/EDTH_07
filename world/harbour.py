"""Schematic water-side launch berths; not surveyed navigation infrastructure.

The layout is shared with the 3D viewer. Validate it against the bundled coastline
at startup rather than silently placing vessels on land or shifting their display.
The shore radio station and the agents' existing home point stay unchanged.
"""

import hashlib
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

from contract.geo import to_xy
from contract.mission import Point as MetrePoint


def coastline(root: Path):
    raw = json.loads((root / "web/public/geo/land.geojson").read_text())
    polygons = []
    for feature in raw["features"]:
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            rings = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            rings = geometry["coordinates"]
        else:
            continue
        for polygon in rings:
            projected = [[to_xy(lat, lon) for lon, lat in ring] for ring in polygon]
            polygons.append(Polygon(projected[0], projected[1:]))
    if not polygons:
        raise ValueError("harbour validation requires a polygon coastline")
    return unary_union(MultiPolygon(polygons))


@dataclass(frozen=True)
class Harbour:
    station: MetrePoint
    berths: tuple[MetrePoint, ...]
    heading: int
    clearance: int
    departure_m: int
    pontoon: tuple[MetrePoint, MetrePoint]
    gangway: tuple[MetrePoint, MetrePoint]
    source_sha256: str

    def validate(self, land, station: MetrePoint, boats: int, dock_m: int) -> None:
        if self.station != station or len(self.berths) != boats:
            raise ValueError("harbour layout does not match the mission station/fleet")
        for berth in self.berths:
            if Point(berth).distance(Point(station)) > dock_m:
                raise ValueError(f"berth {berth} is outside the existing dock radius")
            # The schematic launch points face west into open water. A disk covers
            # the proxy hull at any heading; the outbound corridor includes it too.
            exit_point = (berth[0] - self.departure_m, berth[1])
            if not LineString([berth, exit_point]).buffer(self.clearance).disjoint(land):
                raise ValueError(f"berth/departure corridor {berth} intersects land")
        for a, b in combinations(self.berths, 2):
            if Point(a).distance(Point(b)) <= 2 * self.clearance:
                raise ValueError("harbour berth hull envelopes overlap")


def load_harbour(root: Path, station: MetrePoint, boats: int, dock_m: int) -> Harbour:
    content = (root / "world/harbour.json").read_bytes()
    raw = json.loads(content)
    harbour = Harbour(
        tuple(raw["station"]), tuple(tuple(p) for p in raw["berths"]),
        raw["departure_heading_deg"], raw["hull_clearance_m"], raw["departure_check_m"],
        tuple(tuple(p) for p in raw["pontoon"]), tuple(tuple(p) for p in raw["gangway"]),
        hashlib.sha256(content).hexdigest(),
    )
    if harbour.heading != 270 or harbour.clearance <= 0 or harbour.departure_m <= 0:
        raise ValueError("harbour layout requires positive clearance and a westbound departure")
    harbour.validate(coastline(root), station, boats, dock_m)
    return harbour
