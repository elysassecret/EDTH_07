import type { FeatureCollection } from "geojson";
import { xy } from "./feed";

type Point = readonly [number, number];
type Polygon = Point[][];

function segmentDistance(p: Point, a: Point, b: Point) {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const t = Math.max(0, Math.min(1,
    ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy || 1),
  ));
  return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
}

function insideRing(p: Point, ring: Point[]) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i], b = ring[j];
    if ((a[1] > p[1]) !== (b[1] > p[1]) &&
      p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0])
      inside = !inside;
  }
  return inside;
}

function cross(a: Point, b: Point, p: Point) {
  return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
}

/** Local display safety checks only; never changes truth coordinates or agent routing. */
export class DisplayCoast {
  private polygons: Polygon[] = [];
  private edges: [Point, Point][] = [];

  constructor(geo: FeatureCollection) {
    for (const feature of geo.features) {
      const geometry = feature.geometry;
      const polygons = geometry.type === "Polygon" ? [geometry.coordinates]
        : geometry.type === "MultiPolygon" ? geometry.coordinates : [];
      for (const polygon of polygons) {
        const rings = polygon.map((ring) => ring.map(([lon, lat]) => xy(lon, lat)));
        this.polygons.push(rings);
        for (const ring of rings)
          for (let i = 0; i < ring.length; i++)
            this.edges.push([ring[i], ring[(i + 1) % ring.length]]);
      }
    }
  }

  clearance(p: Point) {
    if (this.polygons.some((rings) => insideRing(p, rings[0]) &&
      !rings.slice(1).some((ring) => insideRing(p, ring)))) return 0;
    return Math.min(Infinity, ...this.edges.map(([a, b]) => segmentDistance(p, a, b)));
  }

  canBlend(a: Point, b: Point, radius = 4) {
    if (this.clearance(a) <= radius || this.clearance(b) <= radius) return false;
    for (const [u, v] of this.edges) {
      if (cross(a, b, u) * cross(a, b, v) < 0 &&
        cross(u, v, a) * cross(u, v, b) < 0) return false;
      if (Math.min(segmentDistance(u, a, b), segmentDistance(v, a, b),
        segmentDistance(a, u, v), segmentDistance(b, u, v)) <= radius) return false;
    }
    return true;
  }
}

/** Four metres encloses the illustrative USV mesh at any heading, not a measured hull. */
export function safeOverviewScale(
  cameraDistance: number, coastClearance: number,
  neighbourDistance: number, stationDistance: number,
) {
  // Harbour meshes stay life-sized. Markers carry visibility at chart-scale distances.
  if (stationDistance < 500) return 1;
  return Math.max(1, Math.min(15, cameraDistance / 2000,
    coastClearance / 4, neighbourDistance / 8));
}
