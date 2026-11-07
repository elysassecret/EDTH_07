// Owner: C. Static infrastructure from data/scene-coordinates.json, bundled at build time.
// Public approximate cable routes (few-vertex OSM lines), not surveyed routes.
import raw from "../../../data/scene-coordinates.json";
import type { Feature, FeatureCollection } from "geojson";
type LatLon = [number, number]; // data/scene-coordinates.json stores [lat, lon]

interface SceneFile {
  box: { corners_wgs84: Record<"NW" | "NE" | "SE" | "SW", { lat: number; lon: number }> };
  cables: Record<string, { kind: string; lat_lon: LatLon[] }>;
  lane_measured_from_ais: { centreline: { lat: number; lon: number }[] };
  shore_sites: Record<string, { lat: number; lon: number }>;
}
const scene = raw as unknown as SceneFile;

// Cables the scenario uses (config/scene.toml scenario_lines); others are drawn lighter.
export const SCENARIO_CABLES = ["HVDC_Storebaelt_I", "MV_60kV_Sprogo_Funen", "Great_Belt_1_fibre"];

export const CABLE_LABEL: Record<string, string> = {
  HVDC_Storebaelt_I: "HVDC Storebælt I",
  MV_60kV_Sprogo_Funen: "60 kV Sprogø–Funen",
  Great_Belt_1_fibre: "Great Belt 1 fibre",
  Great_Belt_2_fibre: "Great Belt 2 fibre",
  GC3_fibre_schematic: "GC3 fibre (schematic)",
};

const ll = (p: LatLon): [number, number] => [p[1], p[0]]; // [lat, lon] -> [lon, lat]

const c = scene.box.corners_wgs84;
export const boxRing: [number, number][] = (["NW", "NE", "SE", "SW", "NW"] as const).map(
  (k) => [c[k].lon, c[k].lat],
);

export const boxBounds: [[number, number], [number, number]] = [
  [Math.min(...boxRing.map((p) => p[0])), Math.min(...boxRing.map((p) => p[1]))],
  [Math.max(...boxRing.map((p) => p[0])), Math.max(...boxRing.map((p) => p[1]))],
];

export const cablesGeo: FeatureCollection = {
  type: "FeatureCollection",
  features: Object.entries(scene.cables).map(([id, cb]) => ({
    type: "Feature",
    properties: { id, kind: cb.kind, scenario: SCENARIO_CABLES.includes(id) },
    geometry: { type: "LineString", coordinates: cb.lat_lon.map(ll) },
  })),
};

export const laneGeo: Feature = {
  type: "Feature",
  properties: {},
  geometry: {
    type: "LineString",
    coordinates: scene.lane_measured_from_ais.centreline.map((p) => [p.lon, p.lat]),
  },
};

export const boxGeo: Feature = {
  type: "Feature",
  properties: {},
  geometry: { type: "Polygon", coordinates: [boxRing] },
};

// ref: "boat:3" or a contact id, so the selected one keeps its label (map/declutter.ts);
// band: segment-age colour; geoKind: the depth/infra kind of a geo label
export interface Label {
  pos: [number, number]; text: string; kind: string; ref?: string;
  band?: "recent" | "due" | "over" | "none"; geoKind?: string;
}

/** Cable names at a middle vertex inside the box. */
export function cableLabels(): Label[] {
  return Object.entries(scene.cables).map(([id, cb]) => {
    const mid = cb.lat_lon[Math.floor(cb.lat_lon.length / 2)];
    return { pos: ll(mid), text: CABLE_LABEL[id] ?? id, kind: "cable" };
  });
}

export const shoreSites = scene.shore_sites;
