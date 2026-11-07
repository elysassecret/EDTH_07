import { describe, expect, it } from "vitest";
import { Vector3, Box3, Mesh } from "three";
import { FEED_POLL_MS, FEED_STALE_MS, feedExpired, headingYaw, xy } from "./feed";
import { usvModel, shipModel } from "./models";

describe("viewer feed deadline", () => {
  it("reserves watchdog headroom inside the two-second requirement", () => {
    expect(FEED_STALE_MS + FEED_POLL_MS).toBeLessThan(2000);
  });
  it("expires at the same boundary for watchdog and command dispatch", () => {
    expect(feedExpired(100, 100 + FEED_STALE_MS - 1)).toBe(false);
    expect(feedExpired(100, 100 + FEED_STALE_MS)).toBe(true);
    expect(feedExpired(100, 100 + FEED_STALE_MS + 1)).toBe(true);
    expect(feedExpired(1800, 1801)).toBe(false);
  });
  it("distinguishes no observation from a valid observation at clock zero", () => {
    expect(feedExpired(null, 0)).toBe(true);
    expect(feedExpired(0, 0)).toBe(false);
    expect(feedExpired(0, FEED_STALE_MS)).toBe(true);
  });
});

describe("shared-simulation 3D display", () => {
  it("uses the same local metre origin as the dashboard and Python World", () => {
    expect(xy(11, 55.4)).toEqual([0, 0]);
    expect(xy(11.1303, 55.3316)).toEqual([8237, -7605]);
  });
  it("maps navigation north/east to the WebGL axes", () => {
    const forward = new Vector3(0, 0, -1);
    const east = forward
      .clone()
      .applyAxisAngle(new Vector3(0, 1, 0), headingYaw(90));
    expect(east.x).toBeCloseTo(1);
    expect(east.z).toBeCloseTo(0);
    expect(
      forward.clone().applyAxisAngle(new Vector3(0, 1, 0), headingYaw(0)).z,
    ).toBe(-1);
  });
  it("builds volumetric meshes, not flat vessel sprites", () => {
    for (const model of [usvModel(), shipModel(true)]) {
      const size = new Box3().setFromObject(model).getSize(new Vector3());
      expect(size.x).toBeGreaterThan(2);
      expect(size.y).toBeGreaterThan(2);
      expect(size.z).toBeGreaterThan(5);
      let vertices = 0,
        draws = 0;
      model.traverse((o) => {
        if (o instanceof Mesh) {
          vertices += o.geometry.attributes.position.count;
          draws++;
        }
      });
      expect(vertices).toBeGreaterThan(500);
      expect(draws).toBeLessThan(20);
    }
  });
});
