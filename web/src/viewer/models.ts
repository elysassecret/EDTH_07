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

// USV specific materials matching the CAD reference & screenshots
const marineBlue = paint("#2b5c7f", 0.42, 0.15),
  keelBlue = paint("#244e6b", 0.45, 0.12),
  cabinSilver = paint("#c5ccd3", 0.35, 0.35),
  cabinTop = paint("#b8c0c8", 0.4, 0.3),
  sprayWhite = paint("#dde4e9", 0.35, 0.1),
  deckPad = paint("#20282e", 0.85, 0.05),
  hatchGrey = paint("#525e66", 0.55, 0.18),
  latchRed = paint("#d93535", 0.35, 0.1),
  jetSteel = paint("#85939e", 0.28, 0.72),
  jetNozzle = paint("#454e55", 0.4, 0.6),
  radomeWhite = paint("#edf2f6", 0.22, 0.05),
  mastBlack = paint("#192025", 0.7, 0.2),
  visorTint = new T.MeshPhysicalMaterial({
    color: "#12191f",
    roughness: 0.1,
    metalness: 0.45,
    clearcoat: 1,
  });

function box(
  group: T.Group,
  size: number[],
  position: number[],
  material: T.Material,
  rotation?: number[],
) {
  const m = new T.Mesh(new T.BoxGeometry(size[0], size[1], size[2]), material);
  m.position.set(position[0], position[1], position[2]);
  if (rotation) m.rotation.set(rotation[0], rotation[1], rotation[2]);
  group.add(m);
  return m;
}

function cylinder(
  group: T.Group,
  radiusTop: number,
  radiusBottom: number,
  height: number,
  segments: number,
  position: number[],
  rotation: number[] | null,
  material: T.Material,
) {
  const m = new T.Mesh(
    new T.CylinderGeometry(radiusTop, radiusBottom, height, segments),
    material,
  );
  m.position.set(position[0], position[1], position[2]);
  if (rotation) m.rotation.set(rotation[0], rotation[1], rotation[2]);
  group.add(m);
  return m;
}

function sphere(
  group: T.Group,
  radius: number,
  position: number[],
  material: T.Material,
  segments = 12,
) {
  const m = new T.Mesh(new T.SphereGeometry(radius, segments, segments), material);
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
  segments = 8,
) {
  const delta = b.clone().sub(a);
  const m = new T.Mesh(
    new T.CylinderGeometry(radius, radius, delta.length(), segments),
    material,
  );
  m.position.copy(a).add(b).multiplyScalar(0.5);
  m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), delta.normalize());
  group.add(m);
  return m;
}

function usvHullPlanform(scaleX = 1, scaleZ = 1) {
  const s = new T.Shape();
  s.moveTo(0, 2.65 * scaleZ);
  s.lineTo(0.96 * scaleX, 2.65 * scaleZ);
  s.lineTo(1.05 * scaleX, 1.2 * scaleZ);
  s.lineTo(1.04 * scaleX, 0.0 * scaleZ);
  s.quadraticCurveTo(
    1.0 * scaleX,
    -1.1 * scaleZ,
    0.72 * scaleX,
    -1.8 * scaleZ,
  );
  s.quadraticCurveTo(
    0.38 * scaleX,
    -2.35 * scaleZ,
    0,
    -2.75 * scaleZ,
  );
  s.quadraticCurveTo(
    -0.38 * scaleX,
    -2.35 * scaleZ,
    -0.72 * scaleX,
    -1.8 * scaleZ,
  );
  s.quadraticCurveTo(
    -1.0 * scaleX,
    -1.1 * scaleZ,
    -1.04 * scaleX,
    0.0 * scaleZ,
  );
  s.lineTo(-1.05 * scaleX, 1.2 * scaleZ);
  s.lineTo(-0.96 * scaleX, 2.65 * scaleZ);
  s.closePath();
  return s;
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

  // 1. Deep-V monohull topsides & deck
  const upperHullGeom = new T.ExtrudeGeometry(usvHullPlanform(1.0, 1.0), {
    depth: 0.52,
    bevelEnabled: true,
    bevelThickness: 0.08,
    bevelSize: 0.05,
    bevelSegments: 2,
    curveSegments: 16,
  });
  upperHullGeom.rotateX(-Math.PI / 2);
  const upperHull = new T.Mesh(upperHullGeom, marineBlue);
  upperHull.position.set(0, -0.05, 0);
  g.add(upperHull);

  // Deep-V lower hull deadrise
  const lowerHullGeom = new T.ExtrudeGeometry(usvHullPlanform(0.88, 0.96), {
    depth: 0.35,
    bevelEnabled: true,
    bevelThickness: 0.06,
    bevelSize: 0.06,
    bevelSegments: 2,
    curveSegments: 16,
  });
  lowerHullGeom.rotateX(-Math.PI / 2);
  const lowerHull = new T.Mesh(lowerHullGeom, keelBlue);
  lowerHull.position.set(0, -0.32, 0.05);
  g.add(lowerHull);

  // Centerline keel skeg strip
  box(g, [0.06, 0.12, 3.8], [0, -0.36, 0.5], mastBlack);

  // 2. Waterline chine spray rails (Crisp White/Silver)
  const sprayRailGeom = new T.ExtrudeGeometry(usvHullPlanform(1.04, 1.01), {
    depth: 0.06,
    bevelEnabled: false,
    curveSegments: 16,
  });
  sprayRailGeom.rotateX(-Math.PI / 2);
  const sprayRail = new T.Mesh(sprayRailGeom, sprayWhite);
  sprayRail.position.set(0, 0.02, 0);
  g.add(sprayRail);

  // 3. Gunwale rub-rail bumper (Black rubber)
  const gunwaleGeom = new T.ExtrudeGeometry(usvHullPlanform(1.055, 1.005), {
    depth: 0.07,
    bevelEnabled: false,
    curveSegments: 16,
  });
  gunwaleGeom.rotateX(-Math.PI / 2);
  const gunwale = new T.Mesh(gunwaleGeom, rubber);
  gunwale.position.set(0, 0.44, 0);
  g.add(gunwale);

  // 4. Deck non-skid pads & foredeck access hatches
  box(g, [0.92, 0.02, 1.3], [0, 0.48, -1.75], deckPad);
  for (const x of [-0.44, 0.44]) {
    box(g, [0.28, 0.035, 0.36], [x, 0.49, -1.6], hatchGrey);
    box(g, [0.035, 0.02, 0.09], [x - 0.07, 0.51, -1.6], latchRed);
    box(g, [0.035, 0.02, 0.09], [x + 0.07, 0.51, -1.6], latchRed);
  }

  // Mooring hardware: Stainless steel bow eye / cleat
  box(g, [0.06, 0.08, 0.16], [0, 0.49, -2.58], steel);
  // Stern mooring cleats
  for (const x of [-0.82, 0.82]) {
    box(g, [0.06, 0.06, 0.14], [x, 0.49, 2.45], steel);
  }

  // 5. Aft modular mission payload bay
  box(g, [1.32, 0.05, 1.35], [0, 0.47, 1.78], deckPad);
  box(g, [1.38, 0.1, 0.05], [0, 0.52, 1.1], mastBlack);
  box(g, [1.38, 0.1, 0.05], [0, 0.52, 2.46], mastBlack);
  box(g, [0.05, 0.1, 1.36], [-0.69, 0.52, 1.78], mastBlack);
  box(g, [0.05, 0.1, 1.36], [0.69, 0.52, 1.78], mastBlack);
  box(g, [0.55, 0.04, 0.42], [0, 0.49, 1.8], hatchGrey);
  box(g, [0.035, 0.02, 0.1], [-0.15, 0.52, 1.8], latchRed);
  box(g, [0.035, 0.02, 0.1], [0.15, 0.52, 1.8], latchRed);

  // 6. Twin electric waterjet pump propulsion units
  for (const x of [-0.42, 0.42]) {
    cylinder(g, 0.13, 0.14, 0.42, 16, [x, -0.06, 2.82], [Math.PI / 2, 0, 0], jetSteel);
    cylinder(g, 0.09, 0.11, 0.14, 16, [x, -0.06, 2.98], [Math.PI / 2, 0, 0], jetNozzle);
    box(g, [0.24, 0.16, 0.18], [x, -0.04, 3.02], jetSteel);
    tube(g, new T.Vector3(x, 0.1, 2.72), new T.Vector3(x, 0.04, 3.0), 0.016, steel);
    box(g, [0.26, 0.02, 0.1], [x, -0.22, 2.76], jetSteel);
  }

  // 7. Cabin / Superstructure cowl
  const cabinShape = new T.Shape();
  cabinShape.moveTo(-0.64, 0.95);
  cabinShape.lineTo(0.64, 0.95);
  cabinShape.lineTo(0.64, -0.4);
  cabinShape.quadraticCurveTo(0.62, -0.95, 0.38, -1.2);
  cabinShape.lineTo(-0.38, -1.2);
  cabinShape.quadraticCurveTo(-0.62, -0.95, -0.64, -0.4);
  cabinShape.closePath();

  const cabinGeom = new T.ExtrudeGeometry(cabinShape, {
    depth: 0.54,
    bevelEnabled: true,
    bevelThickness: 0.06,
    bevelSize: 0.05,
    bevelSegments: 3,
    curveSegments: 12,
  });
  cabinGeom.rotateX(-Math.PI / 2);
  const cabin = new T.Mesh(cabinGeom, cabinSilver);
  cabin.position.set(0, 0.48, 0.08);
  g.add(cabin);

  // Upper cabin roof tier
  box(g, [0.82, 0.14, 1.25], [0, 1.06, 0.05], cabinTop);

  // 8. Tinted wraparound sensor visor / window band
  box(g, [0.74, 0.22, 0.05], [0, 0.78, -1.02], visorTint, [-0.15, 0, 0]);
  box(g, [0.28, 0.22, 0.05], [-0.46, 0.78, -0.88], visorTint, [-0.15, -0.65, 0]);
  box(g, [0.28, 0.22, 0.05], [0.46, 0.78, -0.88], visorTint, [-0.15, 0.65, 0]);
  box(g, [0.05, 0.22, 1.05], [-0.67, 0.78, -0.22], visorTint);
  box(g, [0.05, 0.22, 1.05], [0.67, 0.78, -0.22], visorTint);

  // 9. Navigation lights
  for (const x of [-0.72, 0.72]) {
    box(g, [0.06, 0.05, 0.12], [x, 0.88, 0.2], mastBlack);
    const lamp = new T.Mesh(
      new T.SphereGeometry(0.055, 8, 6),
      new T.MeshStandardMaterial({
        color: x < 0 ? "#fa3838" : "#38f888",
        emissive: x < 0 ? "#d61818" : "#18c858",
        emissiveIntensity: 1.2,
      }),
    );
    lamp.position.set(x + (x < 0 ? -0.04 : 0.04), 0.88, 0.2);
    g.add(lamp);
  }

  // 10. Mast, satellite communications radome dish, whip antennas, EO/IR FLIR gimbal
  box(g, [0.22, 0.38, 0.28], [0, 1.28, 0.22], mastBlack);

  const radome = new T.Mesh(new T.CylinderGeometry(0.36, 0.36, 0.14, 24), radomeWhite);
  radome.rotation.z = Math.PI / 2;
  radome.rotation.y = 0.12;
  radome.position.set(0, 1.76, 0.22);
  g.add(radome);
  cylinder(g, 0.08, 0.08, 0.18, 16, [0, 1.76, 0.22], [0, 0, Math.PI / 2], mastBlack);

  for (const x of [-0.22, 0.22]) {
    cylinder(g, 0.03, 0.035, 0.1, 8, [x, 1.18, 0.3], null, mastBlack);
    tube(g, new T.Vector3(x, 1.22, 0.3), new T.Vector3(x, 2.52, 0.26), 0.012, mastBlack);
  }

  // Forward EO/IR FLIR camera gimbal
  cylinder(g, 0.1, 0.12, 0.08, 16, [0, 1.15, -0.68], null, mastBlack);
  sphere(g, 0.14, [0, 1.26, -0.68], mastBlack, 16);
  cylinder(g, 0.075, 0.075, 0.05, 16, [0, 1.26, -0.79], [Math.PI / 2, 0, 0], visorTint);

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
