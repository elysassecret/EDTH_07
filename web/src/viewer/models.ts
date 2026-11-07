import * as T from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

function compact(group: T.Group) {
  const batches = new Map<T.Material, T.BufferGeometry[]>();
  for (const child of [...group.children])
    if (child instanceof T.Mesh && !Array.isArray(child.material)) {
      child.updateMatrix();
      const geometry = child.geometry.index
        ? child.geometry.toNonIndexed()
        : child.geometry.clone();
      geometry.applyMatrix4(child.matrix);
      geometry.clearGroups();
      const list = batches.get(child.material) ?? [];
      list.push(geometry);
      batches.set(child.material, list);
      group.remove(child);
      child.geometry.dispose();
    }
  for (const [material, geometries] of batches) {
    const merged = mergeGeometries(geometries);
    for (const geometry of geometries) geometry.dispose();
    if (merged) {
      const mesh = new T.Mesh(merged, material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      group.add(mesh);
    }
  }
  return group;
}

const paint = (colour: string, roughness = 0.5, metalness = 0.05) =>
  new T.MeshStandardMaterial({ color: colour, roughness, metalness });
const white = paint("#e9edf0", 0.32),
  navy = paint("#162b38", 0.4),
  rubber = paint("#172025", 0.82),
  steel = paint("#acbec5", 0.24, 0.8);
const glass = new T.MeshPhysicalMaterial({
  color: "#243f4b",
  roughness: 0.08,
  metalness: 0.4,
  clearcoat: 1,
});
function box(
  group: T.Group,
  size: number[],
  position: number[],
  material: T.Material,
) {
  const m = new T.Mesh(new T.BoxGeometry(size[0], size[1], size[2]), material);
  m.position.set(position[0], position[1], position[2]);
  group.add(m);
  return m;
}
function tube(
  group: T.Group,
  a: T.Vector3,
  b: T.Vector3,
  radius: number,
  material: T.Material,
) {
  const delta = b.clone().sub(a);
  const m = new T.Mesh(
    new T.CylinderGeometry(radius, radius, delta.length(), 8),
    material,
  );
  m.position.copy(a).add(b).multiplyScalar(0.5);
  m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), delta.normalize());
  group.add(m);
}
function hull(length: number, width: number, depth: number) {
  const s = new T.Shape();
  s.moveTo(-width / 2, -length / 2);
  s.lineTo(width / 2, -length / 2);
  s.lineTo(width / 2, length * 0.2);
  s.quadraticCurveTo(width / 2, length * 0.42, 0, length / 2);
  s.quadraticCurveTo(-width / 2, length * 0.42, -width / 2, length * 0.2);
  s.closePath();
  const g = new T.ExtrudeGeometry(s, {
    depth,
    bevelEnabled: true,
    bevelThickness: width * 0.04,
    bevelSize: width * 0.04,
    bevelSegments: 2,
    curveSegments: 8,
  });
  g.rotateX(-Math.PI / 2);
  return g;
}
/** Full 3D display proxy, not calibrated hull dimensions or a new dynamics model. */
export function usvModel() {
  const g = new T.Group();
  for (const x of [-1.05, 1.05]) {
    const pontoon = new T.Mesh(hull(6.4, 0.72, 0.68), white);
    pontoon.position.set(x, -0.3, 0);
    g.add(pontoon);
    const stripe = new T.Mesh(hull(6.45, 0.75, 0.13), rubber);
    stripe.position.set(x, 0.15, 0);
    g.add(stripe);
    box(g, [0.48, 0.35, 0.65], [x, -0.15, 3], navy);
    const prop = new T.Mesh(new T.CylinderGeometry(0.2, 0.2, 0.16, 12), steel);
    prop.rotation.x = Math.PI / 2;
    prop.position.set(x, -0.18, 3.4);
    g.add(prop);
  }
  box(g, [2.25, 0.18, 3.8], [0, 0.68, 0.25], white);
  box(g, [1.5, 0.9, 1.75], [0, 1.2, 0.2], white);
  box(g, [1.32, 0.38, 0.035], [0, 1.38, -0.69], glass);
  box(g, [1.32, 0.38, 0.035], [0, 1.38, 1.09], glass);
  for (const x of [-0.762, 0.762])
    box(g, [0.035, 0.38, 1.5], [x, 1.38, 0.2], glass);
  box(g, [1.7, 0.12, 1.95], [0, 1.73, 0.2], navy);
  // Solar panel frame / cell ribbons.
  box(g, [1.3, 0.04, 1.4], [0, 1.82, 0.2], paint("#183c57", 0.2, 0.45));
  for (let i = -2; i <= 2; i++)
    box(g, [0.016, 0.01, 1.35], [i * 0.25, 1.85, 0.2], steel);
  tube(
    g,
    new T.Vector3(0, 1.75, 0.85),
    new T.Vector3(0, 3.05, 0.85),
    0.045,
    steel,
  );
  box(g, [1.1, 0.12, 0.15], [0, 2.8, 0.85], white);
  const radar = new T.Mesh(new T.CylinderGeometry(0.25, 0.3, 0.14, 16), white);
  radar.position.set(0, 3.08, 0.85);
  g.add(radar);
  const sensor = new T.Mesh(new T.SphereGeometry(0.19, 12, 10), navy);
  sensor.position.set(0, 2.5, 0.6);
  g.add(sensor);
  for (const x of [-0.98, 0.98]) {
    tube(
      g,
      new T.Vector3(x, 0.8, -1.45),
      new T.Vector3(x, 1.25, -1.45),
      0.025,
      steel,
    );
    tube(
      g,
      new T.Vector3(x, 0.8, 1.95),
      new T.Vector3(x, 1.25, 1.95),
      0.025,
      steel,
    );
    tube(
      g,
      new T.Vector3(x, 1.25, -1.45),
      new T.Vector3(x, 1.25, 1.95),
      0.025,
      steel,
    );
    const lamp = new T.Mesh(
      new T.SphereGeometry(0.07, 8, 6),
      new T.MeshStandardMaterial({
        color: x < 0 ? "#fa4949" : "#46f8b1",
        emissive: x < 0 ? "#b71c25" : "#17b76c",
        emissiveIntensity: 1,
      }),
    );
    lamp.position.set(x, 1.35, -1.5);
    g.add(lamp);
  }
  g.traverse((o) => {
    if (o instanceof T.Mesh) {
      o.castShadow = true;
      o.receiveShadow = true;
    }
  });
  return compact(g);
}

const cargoPaints = ["#6f8079", "#526e83", "#7c6252", "#9b8170"].map((c) =>
  paint(c, 0.8),
);
export function shipModel(ais: boolean) {
  if (!ais) {
    const g = new T.Group();
    g.add(new T.Mesh(hull(10, 3.3, 1.2), paint("#555d62", 0.6)));
    box(g, [2.5, 0.2, 7], [0, 1.1, 0], paint("#a9a69a", 0.8));
    box(g, [2.2, 1.4, 2.4], [0, 1.9, 1.4], white);
    box(g, [2, 0.5, 0.04], [0, 2.1, 0.18], glass);
    box(g, [2.4, 0.12, 2.6], [0, 2.65, 1.4], navy);
    tube(g, new T.Vector3(0, 2.6, 1.5), new T.Vector3(0, 4, 1.5), 0.06, steel);
    return compact(g);
  }
  const g = new T.Group();
  const hullMat = paint(ais ? "#344d59" : "#4c4240", 0.62),
    red = paint("#743d36", 0.8);
  g.add(new T.Mesh(hull(68, 12, 4), hullMat));
  const lower = new T.Mesh(hull(68.2, 12.2, 1.2), red);
  lower.position.y = -0.8;
  g.add(lower);
  box(g, [10, 0.35, 53], [0, 4, 0], paint("#899498", 0.7));
  box(g, [9, 6, 9], [0, 7, 21], white);
  box(g, [10, 2.3, 6], [0, 11.1, 20], white);
  box(g, [9.5, 1, 6.1], [0, 11.2, 19.9], glass);
  box(g, [3.2, 5, 3], [0, 12, 25], red);
  for (let row = 0; row < 4; row++)
    for (let col = 0; col < 3; col++) {
      const m = cargoPaints[(row + col) % cargoPaints.length];
      box(g, [3.05, 3.1, 9.2], [(col - 1) * 3.2, 5.8, 9 - row * 10], m);
      if (row % 2 === 0)
        box(g, [3.05, 3.1, 9.2], [(col - 1) * 3.2, 8.95, 9 - row * 10], m);
    }
  tube(g, new T.Vector3(0, 12.3, 20), new T.Vector3(0, 17, 20), 0.15, steel);
  return compact(g);
}

export function selectionRing() {
  const mesh = new T.Mesh(
    new T.RingGeometry(6, 6.18, 96),
    new T.MeshBasicMaterial({
      color: "#78e4e6",
      side: T.DoubleSide,
      transparent: true,
      opacity: 0.8,
      depthWrite: false,
    }),
  );
  mesh.rotation.x = -Math.PI / 2;
  return mesh;
}
