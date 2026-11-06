// Owner: C. Optional map files from tools/ (issue #9), all in web/public/geo/, all offline:
//   land.geojson   coastline polygons (OSM land polygons)
//   infra.geojson  lines with {kind: "bridge" | "ferry" | "pier", name}
//   depth.geojson  depth contour lines with {depth_m}
// A missing, empty or broken file just means "not drawn"; the chart says which are missing.
// A file may carry a top-level "attribution" string; otherwise the credit below is used.
import type { Feature, FeatureCollection, Geometry, Position } from "geojson";

export type GeoName = "land" | "infra" | "depth";
export const GEO_FILES: GeoName[] = ["land", "infra", "depth"];

// Credits for the sources named in issue #9. A file's own "attribution" wins.
const DEFAULT_CREDIT: Record<GeoName, string | null> = {
  land: "© OpenStreetMap contributors",
  infra: "© OpenStreetMap contributors",
  depth: null, // source not fixed yet: only the file's own attribution is shown
};

export interface GeoFile { data: FeatureCollection; credit: string | null }

export async function loadGeo(name: GeoName): Promise<GeoFile | null> {
  try {
    const r = await fetch(`geo/${name}.geojson`);
    if (!r.ok) return null;
    const j = (await r.json()) as Partial<FeatureCollection> & { attribution?: unknown };
    if (j.type !== "FeatureCollection" || !Array.isArray(j.features) || j.features.length === 0) return null;
    const credit = typeof j.attribution === "string" ? j.attribution : DEFAULT_CREDIT[name];
    return { data: j as FeatureCollection, credit };
  } catch {
    return null; // e.g. the server answered with index.html because the file does not exist
  }
}

export interface LineLabel { pos: [number, number]; text: string; kind: string }

/** A label point in the middle of each line feature. */
function middle(g: Geometry): Position | null {
  const line = g.type === "LineString" ? g.coordinates : g.type === "MultiLineString" ? g.coordinates[0] : null;
  return line && line.length ? line[Math.floor(line.length / 2)] : null;
}

export function infraLabels(fc: FeatureCollection | null): LineLabel[] {
  if (!fc) return [];
  return fc.features.flatMap((f: Feature) => {
    const name = f.properties?.name;
    const p = middle(f.geometry);
    return typeof name === "string" && p ? [{ pos: [p[0], p[1]] as [number, number], text: name, kind: String(f.properties?.kind ?? "") }] : [];
  });
}

export function depthLabels(fc: FeatureCollection | null): LineLabel[] {
  if (!fc) return [];
  return fc.features.flatMap((f: Feature) => {
    const d = f.properties?.depth_m;
    const p = middle(f.geometry);
    return typeof d === "number" && p ? [{ pos: [p[0], p[1]] as [number, number], text: `${d} m`, kind: "depth" }] : [];
  });
}
