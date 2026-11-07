import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { Sky } from "three/addons/objects/Sky.js";
import type { FeatureCollection, Polygon, MultiPolygon } from "geojson";
import type { SceneMsg, Snapshot } from "../types";
import { boxRing } from "../map/scene";
import { xy, headingYaw } from "./feed";
import { usvModel, shipModel, selectionRing } from "./models";
import { oceanMaterial } from "./ocean";
import { DisplayCoast, safeOverviewScale } from "./coast";

export type SceneOptions = {
  followed: number | string | null;
  waves: boolean;
  dusk: boolean;
  links: boolean;
  markers: boolean;
  overviewScale: boolean;
  live: boolean;
  cables: boolean;
};
export type CameraMap = {
  x: number;
  y: number;
  targetX: number;
  targetY: number;
};
export class MarineScene {
  readonly renderer: T.WebGLRenderer;
  private scene = new T.Scene();
  private camera = new T.PerspectiveCamera(48, 1, 1, 200000);
  private controls: OrbitControls;
  private ocean = oceanMaterial();
  private terrain = new T.Group();
  private routes = new T.Group();
  private cables = new T.Group();
  private actors = new Map<string, T.Group>();
  private motion = new Map<
    string,
    {
      from: T.Vector3;
      to: T.Vector3;
      qFrom: T.Quaternion;
      qTo: T.Quaternion;
      at: number;
    }
  >();
  private dots = new Map<string, T.Sprite>();
  private ring = selectionRing();
  private radio: T.LineSegments;
  private options: SceneOptions = {
    followed: 2,
    waves: true,
    dusk: false,
    links: false,
    markers: true,
    overviewScale: true,
    live: true,
    cables: false,
  };
  private snapshot: Snapshot | null = null;
  private coast: DisplayCoast | null = null;
  private animation = 0;
  private disposed = false;
  private observer: ResizeObserver;
  private last = performance.now();
  private waveTime = 0;
  private mapTime = 0;
  private pmrem: T.PMREMGenerator;
  private environment: T.WebGLRenderTarget | null = null;
  private sky = new Sky();
  private sun = new T.Vector3();
  private sunlight = new T.DirectionalLight(0xfff0dc, 3);
  private resizeHandler: () => void;
  private selectedMaterial = new T.SpriteMaterial();
  constructor(
    host: HTMLElement,
    private pick: (id: number | string) => void,
    private cameraChange: (position: CameraMap) => void,
    private geoReady: (geo: FeatureCollection | null) => void,
    private notice: (text: string) => void,
  ) {
    this.renderer = new T.WebGLRenderer({
      antialias: true,
      logarithmicDepthBuffer: true,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.outputColorSpace = T.SRGBColorSpace;
    this.renderer.toneMapping = T.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.65;
    this.renderer.setClearColor(0xb4ccd9);
    this.renderer.domElement.setAttribute(
      "aria-label",
      "Live maritime 3D scene",
    );
    this.renderer.domElement.setAttribute("role", "img");
    this.renderer.domElement.style.touchAction = "none";
    host.append(this.renderer.domElement);
    this.camera.position.set(200, 90, 140);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 12;
    this.controls.maxDistance = 60000;
    this.controls.maxPolarAngle = Math.PI * 0.485;
    this.controls.target.set(0, 0, 0);
    this.scene.fog = new T.FogExp2(0xb4ccd9, 0.0000025);
    this.sky.scale.setScalar(100000);
    this.scene.add(this.sky);
    this.pmrem = new T.PMREMGenerator(this.renderer);
    this.lighting(false);
    this.scene.add(new T.HemisphereLight(0xd6e9f4, 0x385248, 0.9));
    this.scene.add(this.sunlight);
    const water = new T.Mesh(
      new T.PlaneGeometry(140000, 140000, 1, 1).rotateX(-Math.PI / 2),
      this.ocean,
    );
    water.position.y = -0.12;
    this.scene.add(water);
    this.scene.add(this.terrain, this.routes, this.cables, this.ring);
    this.cables.visible = false;
    this.radio = new T.LineSegments(
      new T.BufferGeometry(),
      new T.LineBasicMaterial({
        color: 0xffffff,
        vertexColors: true,
        transparent: true,
        opacity: 0.4,
      }),
    );
    this.scene.add(this.radio);
    this.selectedMaterial = this.dotMaterial();
    this.resizeHandler = () => {
      const w = host.clientWidth,
        h = host.clientHeight;
      if (!w || !h) return;
      this.renderer.setSize(w, h);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
    };
    this.observer = new ResizeObserver(this.resizeHandler);
    this.observer.observe(host);
    this.resizeHandler();
    this.renderer.domElement.addEventListener("pointerdown", this.pointerDown);
    this.renderer.domElement.addEventListener("pointerup", this.pointerUp);
    this.loadLand();
    this.tick();
  }
  private pointerStart = { x: 0, y: 0 };
  private pointerDown = (event: PointerEvent) => {
    this.pointerStart = { x: event.clientX, y: event.clientY };
  };
  private pointerUp = (event: PointerEvent) => {
    if (
      Math.hypot(
        event.clientX - this.pointerStart.x,
        event.clientY - this.pointerStart.y,
      ) > 5
    )
      return;
    const rect = this.renderer.domElement.getBoundingClientRect();
    const ray = new T.Raycaster();
    ray.setFromCamera(
      new T.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        (-(event.clientY - rect.top) / rect.height) * 2 + 1,
      ),
      this.camera,
    );
    for (const hit of ray.intersectObjects(
      [...this.actors.values(), ...this.dots.values()],
      true,
    )) {
      let object: T.Object3D | null = hit.object;
      while (object && !object.userData.boatId && !object.userData.contactId)
        object = object.parent;
      if (object?.userData.boatId || object?.userData.contactId) {
        this.pick(object.userData.boatId ?? object.userData.contactId);
        return;
      }
    }
  };
  private dotMaterial() {
    const canvas = document.createElement("canvas");
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext("2d")!;
    ctx.beginPath();
    ctx.arc(32, 32, 22, 0, Math.PI * 2);
    ctx.fillStyle = "#9ac4d8";
    ctx.fill();
    ctx.lineWidth = 5;
    ctx.strokeStyle = "#172b35";
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(32, 32, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#e9edf0";
    ctx.fill();
    return new T.SpriteMaterial({
      map: new T.CanvasTexture(canvas),
      transparent: true,
      depthTest: false,
    });
  }
  private lighting(dusk: boolean) {
    this.sun.setFromSphericalCoords(
      1,
      T.MathUtils.degToRad(dusk ? 86 : 68),
      T.MathUtils.degToRad(235),
    );
    const u = this.sky.material.uniforms;
    u.turbidity.value = dusk ? 7 : 4;
    u.rayleigh.value = dusk ? 2.5 : 1.7;
    u.mieCoefficient.value = 0.004;
    u.mieDirectionalG.value = 0.82;
    u.sunPosition.value.copy(this.sun);
    this.sunlight.position.copy(this.sun).multiplyScalar(10000);
    this.sunlight.color.set(dusk ? 0xffce9d : 0xfff3dc);
    this.sunlight.intensity = dusk ? 1.5 : 3;
    this.ocean.uniforms.uSun.value.copy(this.sun);
    this.ocean.uniforms.uDusk.value = dusk ? 1 : 0;
    this.environment?.dispose();
    const environmentScene = new T.Scene();
    environmentScene.add(this.sky.clone());
    this.environment = this.pmrem.fromScene(environmentScene, 0, 0.1, 200000);
    this.scene.environment = this.environment.texture;
    this.scene.environmentIntensity = 0.45;
  }
  setOptions(options: SceneOptions) {
    const changed = this.options.followed !== options.followed;
    if (options.dusk !== this.options.dusk) this.lighting(options.dusk);
    this.options = options;
    this.radio.visible = options.links;
    this.cables.visible = options.cables;
    if (changed) this.frameSelection();
  }
  private frameSelection() {
    const target = this.followedPosition();
    if (this.options.followed !== null && target) {
      this.controls.target.copy(target);
      this.camera.position
        .copy(target)
        .add(
          typeof this.options.followed === "number"
            ? this.shore && Math.hypot(target.x - this.shore[0], -target.z - this.shore[1]) < 500
              ? new T.Vector3(-28, 16, 30) // seaward view: never start behind the quay building
              : new T.Vector3(18, 10, 22)
            : this.snapshot?.contacts.find(
                  (c) => c.id === this.options.followed,
                )?.ais
              ? new T.Vector3(110, 50, 120)
              : new T.Vector3(30, 15, 38),
        );
    } else {
      this.controls.target.set(-1500, 0, 600);
      this.camera.position.set(-1500, 22500, 26500);
    }
    this.controls.update();
  }
  private followedPosition() {
    if (this.options.followed === null) return null;
    return (
      this.actors
        .get(
          typeof this.options.followed === "number"
            ? `usv:${this.options.followed}`
            : `ship:${this.options.followed}`,
        )
        ?.position.clone() ?? null
    );
  }
  setFrame(frame: Snapshot) {
    const first = !this.snapshot;
    const reset = !!this.snapshot && frame.t < this.snapshot.t;
    this.snapshot = frame;
    const active = new Set<string>();
    for (const boat of frame.boats) {
      const key = `usv:${boat.id}`;
      active.add(key);
      let model = this.actors.get(key);
      if (!model) {
        model = usvModel();
        model.userData.boatId = boat.id;
        this.actors.set(key, model);
        this.scene.add(model);
        const dot = new T.Sprite(this.selectedMaterial);
        dot.userData.boatId = boat.id;
        this.dots.set(key, dot);
        this.scene.add(dot);
      }
      this.place(
        key,
        model,
        new T.Vector3(boat.x, 0, -boat.y),
        headingYaw(boat.hdg ?? 0),
        reset,
      );
    }
    for (const contact of frame.contacts) {
      const key = `ship:${contact.id}`;
      active.add(key);
      let model = this.actors.get(key);
      if (!model) {
        model = shipModel(contact.ais);
        model.userData.contactId = contact.id;
        this.actors.set(key, model);
        this.scene.add(model);
      }
      this.place(
        key,
        model,
        new T.Vector3(contact.x, -1, -contact.y),
        headingYaw(contact.cog),
        reset,
      );
    }
    for (const [key, model] of this.actors) {
      if (!active.has(key)) {
        this.scene.remove(model);
        model.traverse((o) => {
          if (o instanceof T.Mesh) o.geometry.dispose();
        });
        this.actors.delete(key);
        this.motion.delete(key);
        const dot = this.dots.get(key);
        if (dot) {
          this.scene.remove(dot);
          this.dots.delete(key);
        }
      }
    }
    const locations = new Map<number, [number, number]>(
      frame.boats.map((b) => [b.id, [b.x, b.y]]),
    );
    if (this.shore) locations.set(0, this.shore);
    const points: number[] = [],
      colours: number[] = [];
    for (const link of frame.links) {
      const a = locations.get(link.a),
        b = locations.get(link.b);
      if (a && b) {
        points.push(a[0], 5, -a[1], b[0], 5, -b[1]);
        const colour = new T.Color(
          link.state === "cut"
            ? 0xf09a89
            : link.state === "up"
              ? 0x7dc4ee
              : 0x8c9b9f,
        );
        colours.push(
          colour.r,
          colour.g,
          colour.b,
          colour.r,
          colour.g,
          colour.b,
        );
      }
    }
    this.radio.geometry.dispose();
    this.radio.geometry = new T.BufferGeometry()
      .setAttribute("position", new T.Float32BufferAttribute(points, 3))
      .setAttribute("color", new T.Float32BufferAttribute(colours, 3));
    for (const boat of frame.boats) {
      const actor = this.actors.get(`usv:${boat.id}`)!;
      actor.userData.coastClearance = this.coast?.clearance([boat.x, boat.y]) ?? 0;
      actor.userData.neighbourDistance = Math.min(Infinity,
        ...frame.boats.filter((other) => other.id !== boat.id)
          .map((other) => Math.hypot(other.x - boat.x, other.y - boat.y)),
        // Traffic proxies can be larger than a USV. Reserve their footprint too.
        ...frame.contacts.map((other) => Math.max(0,
          Math.hypot(other.x - boat.x, other.y - boat.y) - (other.ais ? 40 : 7))),
      );
      actor.userData.stationDistance = this.shore
        ? Math.hypot(boat.x - this.shore[0], boat.y - this.shore[1]) : 0;
    }
    if (first) this.frameSelection();
  }
  private place(
    key: string,
    model: T.Group,
    target: T.Vector3,
    yaw: number,
    reset: boolean,
  ) {
    const q = new T.Quaternion().setFromAxisAngle(new T.Vector3(0, 1, 0), yaw);
    if (
      reset ||
      !this.motion.has(key) ||
      !this.options.live ||
      document.hidden ||
      // A straight display chord can cut a coastal corner even when every
      // simulation waypoint is in water. Snap to received truth rather than
      // drawing a fabricated voyage through land; never relocate the target.
      !this.coast?.canBlend([model.position.x, -model.position.z], [target.x, -target.z],
        key.startsWith("usv:") ? 4 : 0)
    ) {
      model.position.copy(target);
      model.quaternion.copy(q);
    }
    this.motion.set(key, {
      from: model.position.clone(),
      to: target,
      qFrom: model.quaternion.clone(),
      qTo: q,
      at: performance.now(),
    });
  }
  private shore: [number, number] | null = null;
  setScene(scene: SceneMsg) {
    for (const group of [this.routes, this.cables])
      for (const child of [...group.children]) {
        group.remove(child);
        if (child instanceof T.Mesh) child.geometry.dispose();
      }
    this.shore = xy(...scene.shore);
    for (const [id, points] of Object.entries(scene.segments)) {
      const curve = points.map((p) => {
        const [x, y] = xy(...p);
        return new T.Vector3(x, 1.2, -y);
      });
      for (let i = 1; i < curve.length; i++)
        this.beam(
          this.cables,
          curve[i - 1],
          curve[i],
          1,
          id.startsWith("seg:H") ? 0xb657a1 : 0x8e83cb,
        );
    }
    const border = boxRing.map((p) => {
      const [x, y] = xy(...p);
      return new T.Vector3(x, 2, -y);
    });
    this.routes.add(
      new T.LineLoop(
        new T.BufferGeometry().setFromPoints(border),
        new T.LineBasicMaterial({
          color: 0x9db2bc,
          transparent: true,
          opacity: 0.35,
        }),
      ),
    );
    for (const [id, p] of Object.entries(scene.stations)) {
      const [x, y] = xy(...p);
      const buoy = new T.Mesh(
        new T.CylinderGeometry(7, 10, 14, 12),
        new T.MeshStandardMaterial({ color: 0xd0a84c, roughness: 0.6 }),
      );
      buoy.position.set(x, 5, -y);
      buoy.name = id;
      this.routes.add(buoy);
    }
    const [sx, sy] = this.shore;
    const station = new T.Mesh(
      new T.BoxGeometry(25, 15, 20),
      new T.MeshStandardMaterial({ color: 0xdee4df }),
    );
    station.position.set(sx, 7, -sy);
    this.routes.add(station);
    const harbour = scene.harbour;
    if (harbour && Math.hypot(sx - harbour.station[0], sy - harbour.station[1]) < 1) {
      const timber = new T.MeshStandardMaterial({ color: 0x736e60, roughness: 0.9 });
      for (const [index, [a, b]] of [harbour.pontoon, harbour.gangway].entries()) {
        const start = new T.Vector3(a[0], 1, -a[1]);
        // The gangway rises to the schematic land surface; the pontoon stays low.
        const end = new T.Vector3(b[0], index === 1 ? 5 : 1, -b[1]);
        const delta = end.clone().sub(start);
        const deck = new T.Mesh(new T.BoxGeometry(1.8, 0.6, delta.length()), timber);
        deck.position.copy(start).add(end).multiplyScalar(0.5);
        deck.quaternion.setFromUnitVectors(new T.Vector3(0, 0, 1), delta.normalize());
        deck.name = "Schematic harbour pontoon";
        this.routes.add(deck);
      }
      for (const [x, y] of harbour.berths) {
        const bollard = new T.Mesh(new T.CylinderGeometry(0.2, 0.3, 0.6, 8), timber);
        bollard.position.set(x + 5, 1.5, -y);
        bollard.name = "Schematic berth";
        this.routes.add(bollard);
      }
    }
  }
  private beam(
    group: T.Group,
    a: T.Vector3,
    b: T.Vector3,
    radius: number,
    colour: number,
  ) {
    const delta = b.clone().sub(a),
      mesh = new T.Mesh(
        new T.CylinderGeometry(radius, radius, delta.length(), 6),
        new T.MeshStandardMaterial({ color: colour, roughness: 0.85 }),
      );
    mesh.position.copy(a).add(b).multiplyScalar(0.5);
    mesh.quaternion.setFromUnitVectors(
      new T.Vector3(0, 1, 0),
      delta.normalize(),
    );
    group.add(mesh);
  }
  private async loadLand() {
    try {
      const response = await fetch("/geo/land.geojson");
      if (!response.ok) throw new Error();
      const geo = (await response.json()) as FeatureCollection;
      if (this.disposed) return;
      this.coast = new DisplayCoast(geo);
      if (this.snapshot) this.setFrame(this.snapshot);
      const canvas = document.createElement("canvas");
      canvas.width = 256;
      canvas.height = 256;
      const ctx = canvas.getContext("2d")!;
      const pixels = ctx.createImageData(256, 256);
      for (let y = 0; y < 256; y++)
        for (let x = 0; x < 256; x++) {
          const n =
            (Math.sin(x * 0.043 + y * 0.017) +
              Math.sin(y * 0.079 - x * 0.025) +
              Math.sin(x * 0.47) * Math.cos(y * 0.37)) *
            0.08;
          const i = (y * 256 + x) * 4;
          pixels.data[i] = 112 + n * 75;
          pixels.data[i + 1] = 125 + n * 90;
          pixels.data[i + 2] = 92 + n * 65;
          pixels.data[i + 3] = 255;
        }
      ctx.putImageData(pixels, 0, 0);
      const texture = new T.CanvasTexture(canvas);
      texture.wrapS = texture.wrapT = T.RepeatWrapping;
      texture.repeat.set(1 / 600, 1 / 600);
      texture.colorSpace = T.SRGBColorSpace;
      const mat = new T.MeshStandardMaterial({
        color: 0x9caa86,
        map: texture,
        roughness: 1,
        metalness: 0,
      });
      let satelliteBounds: [number, number, number, number] | null = null;
      try {
        const response = await fetch("/geo/s2_box.json");
        if (response.ok) {
          const metadata = (await response.json()) as {
            coordinates: [number, number][];
          };
          const points = metadata.coordinates.map((p) => xy(...p));
          const image = await new T.TextureLoader().loadAsync(
            "/geo/s2_box.png",
          );
          if (this.disposed) {
            image.dispose();
            return;
          }
          image.colorSpace = T.SRGBColorSpace;
          image.anisotropy = Math.min(
            4,
            this.renderer.capabilities.getMaxAnisotropy(),
          );
          texture.dispose();
          mat.map = image;
          mat.color.set(0xffffff);
          satelliteBounds = [
            Math.min(...points.map((p) => p[0])),
            Math.min(...points.map((p) => p[1])),
            Math.max(...points.map((p) => p[0])),
            Math.max(...points.map((p) => p[1])),
          ];
        }
      } catch {
        /* optional local imagery; the procedural surface is not claimed to be aerial data */
      }
      for (const feature of geo.features) {
        const geometry = feature.geometry as Polygon | MultiPolygon;
        if (!["Polygon", "MultiPolygon"].includes(geometry.type)) continue;
        const polygons =
          geometry.type === "Polygon"
            ? [geometry.coordinates]
            : geometry.coordinates;
        for (const polygon of polygons) {
          const shape = new T.Shape();
          polygon.forEach((ring, i) => {
            const path = i === 0 ? shape : new T.Path();
            ring.forEach(([lon, lat], j) => {
              const [x, y] = xy(lon, lat);
              if (j === 0) path.moveTo(x, y);
              else path.lineTo(x, y);
            });
            if (i > 0) shape.holes.push(path);
          });
          const mesh = new T.Mesh(
            new T.ExtrudeGeometry(shape, {
              depth: 5,
              bevelEnabled: false,
            }).rotateX(-Math.PI / 2),
            mat,
          );
          if (satelliteBounds) {
            const [minX, minY, maxX, maxY] = satelliteBounds;
            const positions = mesh.geometry.attributes.position;
            const uv = [];
            for (let i = 0; i < positions.count; i++)
              uv.push(
                (positions.getX(i) - minX) / (maxX - minX),
                (-positions.getZ(i) - minY) / (maxY - minY),
              );
            mesh.geometry.setAttribute(
              "uv",
              new T.Float32BufferAttribute(uv, 2),
            );
          }
          mesh.position.y = -0.2;
          this.terrain.add(mesh);
          const coast = polygon[0].map(([lon, lat]) => {
            const [x, y] = xy(lon, lat);
            return new T.Vector3(x, 0.6, -y);
          });
          this.terrain.add(
            new T.LineLoop(
              new T.BufferGeometry().setFromPoints(coast),
              new T.LineBasicMaterial({
                color: 0xaaa68b,
                transparent: true,
                opacity: 0.65,
              }),
            ),
          );
        }
      }
      this.geoReady(geo);
    } catch {
      this.geoReady(null);
      this.notice(
        "Coastline asset unavailable; sea and live fleet remain available.",
      );
    }
    try {
      const r = await fetch("/geo/infra.geojson");
      if (!r.ok) return;
      const geo = (await r.json()) as FeatureCollection;
      if (this.disposed) return;
      for (const f of geo.features) {
        if (f.geometry.type !== "LineString" || f.properties?.kind !== "bridge")
          continue;
        const points = f.geometry.coordinates.map(([lon, lat]) => {
          const [x, y] = xy(lon, lat);
          return new T.Vector3(x, 20, -y);
        });
        for (let i = 1; i < points.length; i++) {
          this.beam(this.terrain, points[i - 1], points[i], 8, 0xaab1af);
          const delta = points[i].clone().sub(points[i - 1]);
          const count = Math.floor(delta.length() / 250);
          for (let j = 0; j <= count; j++) {
            const pos = points[i - 1]
              .clone()
              .addScaledVector(delta, j / Math.max(1, count));
            this.beam(
              this.terrain,
              new T.Vector3(pos.x, -1, pos.z),
              pos,
              4,
              0x929b97,
            );
          }
        }
      }
    } catch {
      /* optional, never substitute an online asset */
    }
  }
  private tick = () => {
    if (this.disposed) return;
    this.animation = requestAnimationFrame(this.tick);
    const now = performance.now(),
      dt = Math.min((now - this.last) / 1000, 0.1);
    this.last = now;
    if (this.options.waves && this.options.live && !document.hidden)
      this.waveTime += dt;
    this.ocean.uniforms.uTime.value = this.waveTime;
    if (this.options.live)
      for (const [key, m] of this.motion) {
        const actor = this.actors.get(key);
        if (actor) {
          const t = Math.min(1, Math.max(0, (now - m.at) / 100));
          actor.position.lerpVectors(m.from, m.to, t);
          actor.quaternion.slerpQuaternions(m.qFrom, m.qTo, t);
        }
      }
    const target = this.followedPosition();
    if (target) {
      const shift = target.clone().sub(this.controls.target);
      this.camera.position.add(shift);
      this.controls.target.copy(target);
    }
    this.controls.update();
    const distance = this.camera.position.distanceTo(this.controls.target);
    for (const [key, dot] of this.dots) {
      const actor = this.actors.get(key)!;
      dot.position.copy(actor.position).add(new T.Vector3(0, 20, 0));
      dot.scale.setScalar(distance * 0.009);
      dot.visible = this.options.markers && distance > 600;
    }
    this.ring.visible = !!target && distance > 300;
    if (target) {
      this.ring.position.copy(target).add(new T.Vector3(0, 0.8, 0));
      this.ring.scale.setScalar(
        typeof this.options.followed === "string"
          ? 8
          : distance > 1000
            ? distance * 0.0008
            : 1,
      );
    }
    for (const [key, actor] of this.actors)
      actor.scale.setScalar(
        key.startsWith("usv") && this.options.overviewScale && distance > 2000
          ? safeOverviewScale(distance, actor.userData.coastClearance ?? 0,
              actor.userData.neighbourDistance ?? 0, actor.userData.stationDistance ?? 0)
          : 1,
      );
    if (now - this.mapTime > 250) {
      this.mapTime = now;
      this.cameraChange({
        x: this.camera.position.x,
        y: -this.camera.position.z,
        targetX: this.controls.target.x,
        targetY: -this.controls.target.z,
      });
    }
    if (!document.hidden) this.renderer.render(this.scene, this.camera);
  };
  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.animation);
    this.observer.disconnect();
    this.controls.dispose();
    this.renderer.domElement.removeEventListener(
      "pointerdown",
      this.pointerDown,
    );
    this.renderer.domElement.removeEventListener("pointerup", this.pointerUp);
    const materials = new Set<T.Material>();
    this.scene.traverse((o) => {
      if (o instanceof T.Mesh || o instanceof T.Line) {
        o.geometry.dispose();
        (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) =>
          materials.add(m),
        );
      }
    });
    materials.forEach((m) => {
      if ("map" in m && m.map instanceof T.Texture) m.map.dispose();
      m.dispose();
    });
    this.selectedMaterial.map?.dispose();
    this.selectedMaterial.dispose();
    this.environment?.dispose();
    this.pmrem.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
