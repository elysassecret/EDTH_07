import { describe, expect, it } from "vitest";
import type { FeatureCollection } from "geojson";
import { DisplayCoast, safeOverviewScale } from "./coast";
import { Box3, Vector3 } from "three";
import { usvModel } from "./models";
import harbour from "../../../world/harbour.json";

const ring = (points: number[][]) => points.map(([x, y]) => [11 + x / 63212, 55.4 + y / 111190]);
const geo: FeatureCollection = {
  type: "FeatureCollection",
  features: [{ type: "Feature", properties: {}, geometry: {
    type: "Polygon", coordinates: [ring([[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]])],
  } }],
};

describe("truth-preserving coastal display", () => {
  const coast = new DisplayCoast(geo);
  it("rejects interpolation across land even when both snapshots are in water", () => {
    expect(coast.clearance([-10, 50])).toBe(10);
    expect(coast.clearance([50, 110])).toBe(10);
    expect(coast.canBlend([-10, 50], [50, 110])).toBe(false);
    expect(coast.canBlend([-10, -10], [-10, 110])).toBe(true);
  });
  it("checks the hull envelope, not just its centre", () => {
    expect(coast.canBlend([-3, -10], [-3, 110])).toBe(false);
    expect(coast.canBlend([-5, -10], [-5, 110])).toBe(true);
    expect(coast.canBlend([50, 50], [-10, -10])).toBe(false);
  });
  it("handles holes and multipolygons in the local coastline", () => {
    const withHole: FeatureCollection = {
      type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: {
        type: "MultiPolygon", coordinates: [[
          (geo.features[0].geometry as { coordinates: number[][][] }).coordinates[0],
          ring([[30, 30], [30, 70], [70, 70], [70, 30], [30, 30]]),
        ]],
      } }],
    };
    const lake = new DisplayCoast(withHole);
    expect(lake.clearance([50, 50])).toBe(20);
    expect(lake.clearance([20, 50])).toBe(0);
    expect(lake.canBlend([40, 50], [60, 50])).toBe(true);
  });
});

describe("clearance-limited overview meshes", () => {
  it("always keeps boats life-sized in the harbour, even at maximum zoom-out", () => {
    expect(safeOverviewScale(100000, 1000, 1000, 49)).toBe(1);
    expect(safeOverviewScale(100000, 0, 0, 0)).toBe(1);
  });
  it("caps enlargement at coastline and neighbouring hull envelopes", () => {
    expect(safeOverviewScale(100000, 12, 1000, 2000)).toBe(3);
    expect(safeOverviewScale(100000, 1000, 16, 2000)).toBe(2);
    expect(safeOverviewScale(100000, 1000, 1000, 2000)).toBe(15);
    expect(safeOverviewScale(500, 1000, 1000, 2000)).toBe(1);
  });
  it("uses a clearance envelope that encloses the actual illustrative hull mesh", () => {
    const bounds = new Box3().setFromObject(usvModel());
    for (const x of [bounds.min.x, bounds.max.x])
      for (const z of [bounds.min.z, bounds.max.z])
        expect(new Vector3(x, 0, z).length()).toBeLessThan(harbour.hull_clearance_m);
  });
});
