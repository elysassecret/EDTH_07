// Owner: C. Feature 17: offline chart. MapLibre draws the static vector layers;
// deck.gl draws everything that moves, and all text (no online glyphs in the style).
import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
// Bundle MapLibre's worker with its imports so it loads offline in dev and in dist.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { IconLayer, LineLayer, PathLayer, PolygonLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import type { Layer } from "@deck.gl/core";
import { useStore } from "../store";
import { dur } from "../format";
import type { Boat, Contact } from "../types";
import { boxBounds, boxGeo, cableLabels, cablesGeo, laneGeo, type Label } from "./scene";
import { GEO_FILES, depthLabels, infraLabels, loadGeo, type GeoFile, type GeoName, type LineLabel } from "./geo";
import * as T from "./theme";
import { commsLayers } from "./comms";
import { evaluatorLayers } from "./evaluator";
import type { EvalData } from "../types";
import { segAges, type Band } from "../coverage";
import { isDocked } from "../roles";
import { spreadLabels, spreads, type Spread } from "../uncertainty";
import { PRIORITY, keepNonOverlapping, textBox } from "./declutter";
import { hmShort } from "../format";
import { PathStyleExtension, type PathStyleExtensionProps } from "@deck.gl/extensions";
import type { Decision } from "../types";

// Feature 24: a wide band under each cable segment, coloured by revisit age (legend in the
// coverage box; the age is also written on the chart, so colour is never the only cue).
export const BAND_RGB: Record<Band, [number, number, number]> = {
  recent: [90, 190, 170], due: [232, 208, 112], over: [224, 140, 48], none: [150, 156, 162],
};

function coverageLayers(snap: NonNullable<ReturnType<typeof useStore.getState>["snap"]>,
  scene: NonNullable<ReturnType<typeof useStore.getState>["scene"]>, frozen: boolean): Layer[] {
  const segs = segAges(snap, scene).map((a) => ({ ...a, path: scene.segments[a.id] ?? [] }))
    .filter((a) => a.path.length > 1);
  const alpha = frozen ? 70 : 140;
  const solid = segs.filter((a) => a.band !== "none");
  return [
    new PathLayer<(typeof segs)[number]>({
      id: "coverage", data: solid, getPath: (a) => a.path, getColor: (a) => [...BAND_RGB[a.band], alpha],
      getWidth: (a) => (a.band === "over" ? 11 : 8), widthUnits: "pixels", capRounded: true,
    }),
    new PathLayer<(typeof segs)[number], PathStyleExtensionProps<(typeof segs)[number]>>({
      id: "coverage-none", data: segs.filter((a) => a.band === "none"), getPath: (a) => a.path,
      getColor: [...BAND_RGB.none, alpha], getWidth: 8, widthUnits: "pixels",
      getDashArray: [2, 1.5], dashJustified: true, extensions: [new PathStyleExtension({ dash: true })],
    }),
  ];
}

/** Feature 22: dashed "ghost" route of what an open decision would make a boat do. */
function ghostRoutes(snap: NonNullable<ReturnType<typeof useStore.getState>["snap"]>, hover: string | null): Layer[] {
  const open = snap.decisions.filter((d) => d.state === "pending" && d.route && d.route.length > 1);
  return [
    new PathLayer<Decision, PathStyleExtensionProps<Decision>>({
      id: "ghost-routes", data: open, getPath: (d) => d.route ?? [],
      getColor: (d) => (d.id === hover ? [255, 255, 255, 255] : [230, 236, 242, 150]),
      getWidth: (d) => (d.id === hover ? 3.5 : 2), widthUnits: "pixels",
      getDashArray: [4, 3], dashJustified: true, extensions: [new PathStyleExtension({ dash: true })],
      updateTriggers: { getColor: hover, getWidth: hover },
    }),
    new ScatterplotLayer<Decision>({
      id: "ghost-ends", data: open, getPosition: (d) => d.route![d.route!.length - 1], radiusUnits: "pixels",
      getRadius: 7, filled: false, stroked: true, getLineColor: [230, 236, 242, 220], lineWidthUnits: "pixels", getLineWidth: 2,
    }),
  ];
}

maplibregl.setWorkerUrl(workerUrl);

type Snap = NonNullable<ReturnType<typeof useStore.getState>["snap"]>;
type Scene = NonNullable<ReturnType<typeof useStore.getState>["scene"]>;
export const RING_DETECT: [number, number, number, number] = [96, 170, 255, 110];
export const RING_KEEP: [number, number, number, number] = [96, 170, 255, 26];
export const RING_STANDOFF: [number, number, number, number] = [240, 210, 80, 200];

/** A closed ring of points r metres around lon/lat (for dashed rings; Scatterplot has no dash). */
function circle(lon: number, lat: number, r: number, n = 72): [number, number][] {
  return Array.from({ length: n + 1 }, (_, i) => {
    const a = (2 * Math.PI * i) / n;
    return offset(lon, lat, Math.sin(a) * r, Math.cos(a) * r);
  });
}

/** #88 rings: camera range (ship, day) and keep-in-view range around live boats; the 1 nm
 * stand-off around NO AIS contacts. Ranges are the boat model's (config/boat.toml), not
 * measured; stale boats get no rings, since their position is only last known. */
function ringLayers(snap: Snap, scene: Scene): Layer[] {
  // per boat / contact from the snapshot (#91); the scene's config/boat.toml ranges otherwise
  const r = scene.ranges;
  const staleAfter = scene.stale_after_s ?? 60;
  const live = snap.boats.filter((b) => b.heard !== false && snap.t - b.last_heard <= staleAfter
    && b.mode !== "UNAVAILABLE" && !isDocked(b, scene));
  const dark = snap.contacts.filter((k) => !k.ais && snap.t - k.last_seen <= staleAfter);
  return [
    new ScatterplotLayer<Boat>({
      id: "ring-keep", data: live, getPosition: (b) => [b.lon, b.lat], radiusUnits: "meters",
      getRadius: (b) => b.keep_in_view_m ?? r?.keep_in_view_m ?? 0, filled: true, getFillColor: RING_KEEP, stroked: false,
    }),
    new ScatterplotLayer<Boat>({
      id: "ring-detect", data: live, getPosition: (b) => [b.lon, b.lat], radiusUnits: "meters",
      getRadius: (b) => b.detect_m ?? r?.detect_ship_day_m ?? 0, filled: false, stroked: true, getLineColor: RING_DETECT,
      lineWidthUnits: "pixels", getLineWidth: 1,
    }),
    new PathLayer<Contact, PathStyleExtensionProps<Contact>>({
      id: "ring-standoff", data: dark, getPath: (k) => circle(k.lon, k.lat, k.standoff_m ?? r?.standoff_m ?? 0),
      getColor: RING_STANDOFF, getWidth: 1.5, widthUnits: "pixels",
      getDashArray: [5, 4], dashJustified: true, extensions: [new PathStyleExtension({ dash: true })],
    }),
  ];
}

// zoom from which depth contours and their labels show (about 0.5 nm on the scale bar)
const DEPTH_DETAIL_ZOOM = 13;
const FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif";
const M_PER_DEG_LAT = 111_320;

/** Offset a lon/lat point by metres east/north. */
function offset(lon: number, lat: number, e: number, n: number): [number, number] {
  return [lon + e / (M_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180)), lat + n / M_PER_DEG_LAT];
}

// Track symbols as inline SVG masks (no network), tinted by colour, fixed pixel size.
// AIS = directional vessel triangle (neutral); camera only = quatrefoil (unknown), so shape alone tells them apart.
const svg = (body: string) =>
  `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">${body}</svg>`)}`;
const ICON_TRIANGLE = { id: "tri", url: svg('<polygon points="32,6 54,54 32,43 10,54" fill="#fff" fill-opacity="0.45" stroke="#fff" stroke-width="6" stroke-linejoin="round"/>'), width: 64, height: 64, mask: true };
const ICON_QUATREFOIL = { id: "qf", url: svg('<g fill="#fff" fill-opacity="0.35" stroke="#fff" stroke-width="5"><circle cx="32" cy="17" r="13"/><circle cx="32" cy="47" r="13"/><circle cx="17" cy="32" r="13"/><circle cx="47" cy="32" r="13"/></g>'), width: 64, height: 64, mask: true };

const VECTOR_S = 360; // course vector shows where the contact will be in 6 minutes

function square(lon: number, lat: number, half: number): [number, number][] {
  return [
    offset(lon, lat, -half, -half), offset(lon, lat, half, -half),
    offset(lon, lat, half, half), offset(lon, lat, -half, half),
  ];
}

const style: StyleSpecification = {
  version: 8,
  sources: {
    // optional files from tools/ (src/map/geo.ts): empty until loaded and checked
    land: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
    infra: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
    depth: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
    depth_bands: { type: "geojson", data: { type: "FeatureCollection", features: [] } },
    box: { type: "geojson", data: boxGeo },
    cables: { type: "geojson", data: cablesGeo },
    lane: { type: "geojson", data: laneGeo },
  },
  layers: [
    { id: "sea", type: "background", paint: { "background-color": T.SEA } },
    // #88: depth as four shades of the sea colour, darker is deeper (bands from #89 when present)
    {
      id: "depth-bands", type: "fill", source: "depth_bands",
      paint: { "fill-color": ["step", ["to-number", ["get", "depth_min_m"], 0], T.DEPTH_0, 10, T.DEPTH_10, 20, T.DEPTH_20, 30, T.DEPTH_30] },
    },
    // contour lines only when zoomed in; at box scale they cluttered the chart (#88)
    { id: "depth", type: "line", source: "depth", minzoom: DEPTH_DETAIL_ZOOM, paint: { "line-color": T.DEPTH, "line-width": 1, "line-opacity": 0.7 } },
    { id: "land", type: "fill", source: "land", paint: { "fill-color": T.LAND } },
    { id: "coast", type: "line", source: "land", paint: { "line-color": T.COAST, "line-width": 1 } },
    {
      id: "infra", type: "line", source: "infra", filter: ["!=", ["get", "kind"], "ferry"],
      paint: { "line-color": T.INFRA, "line-width": ["match", ["get", "kind"], "bridge", 3, 1.5] },
    },
    {
      id: "ferry", type: "line", source: "infra", filter: ["==", ["get", "kind"], "ferry"],
      paint: { "line-color": T.INFRA, "line-width": 1.5, "line-dasharray": [4, 3] },
    },
    {
      id: "lane", type: "line", source: "lane",
      paint: { "line-color": T.LANE, "line-width": 2, "line-dasharray": [6, 4], "line-opacity": 0.8 },
    },
    {
      id: "cables", type: "line", source: "cables",
      paint: {
        "line-color": ["match", ["get", "kind"], "power", T.CABLE_POWER, T.CABLE_DATA],
        "line-width": ["case", ["get", "scenario"], 3, 1.5],
        "line-opacity": ["case", ["get", "scenario"], 0.95, 0.5],
      },
    },
    { id: "box", type: "line", source: "box", paint: { "line-color": T.BOX, "line-width": 1.5, "line-dasharray": [2, 2] } },
  ],
};

interface Props { satellite: boolean; onSatelliteState: (s: "none" | "ready") => void }

export function Chart({ satellite, onSatelliteState }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [geo, setGeo] = useState<Partial<Record<GeoName, GeoFile | null>>>({});
  const [detail, setDetail] = useState(false); // zoomed in far enough for depth labels
  const [view, setView] = useState(0); // bumps after every pan/zoom: labels are re-decluttered
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  const conn = useStore((s) => s.conn);
  const selected = useStore((s) => s.selected);
  const selectedContact = useStore((s) => s.selectedContact);
  const showComms = useStore((s) => s.showComms);
  const showRings = useStore((s) => s.showRings);
  const hoverDecision = useStore((s) => s.hoverDecision);
  const evalData = useStore((s) => s.evalData);

  useEffect(() => {
    if (!el.current) return;
    const map = new maplibregl.Map({
      container: el.current,
      style,
      bounds: boxBounds,
      fitBoundsOptions: { padding: 40 },
      attributionControl: false,
      dragRotate: false,
    });
    map.addControl(new maplibregl.ScaleControl({ unit: "nautical" }), "bottom-left");
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    const overlay = new MapboxOverlay({
      interleaved: false,
      layers: [],
      onClick: (info) => {
        const o = info.object as { id?: unknown } | undefined;
        const st = useStore.getState();
        if (st.placing && info.coordinate) {
          const [lon, lat] = info.coordinate as [number, number];
          st.send({ cmd: "inject", kind: "contact_start", lat, lon, ais: st.placing.ais });
          st.setPlacing(null);
          return;
        }
        if (o && typeof o.id === "number") st.select(o.id);
        else if (o && typeof o.id === "string" && o.id.startsWith("seg:")) st.selectSegment(o.id);
        else if (o && typeof o.id === "string") st.selectContact(o.id);
        else { st.select(null); st.selectContact(null); }
      },
    });
    map.addControl(overlay);
    overlayRef.current = overlay;
    mapRef.current = map;
    if (import.meta.env.DEV) (window as unknown as { __map: unknown }).__map = map; // debugging
    // Keep the box in view when the panel or window changes size.
    const ro = new ResizeObserver(() => {
      map.resize();
      map.fitBounds(boxBounds, { padding: 40, animate: false });
    });
    ro.observe(el.current);
    map.on("error", (e) => console.error("map:", e.error?.message ?? e));
    map.on("zoom", () => setDetail(map.getZoom() >= DEPTH_DETAIL_ZOOM));
    map.on("moveend", () => setView((v) => v + 1));
    map.on("resize", () => setView((v) => v + 1));
    map.on("load", async () => {
      setLoaded(true);
      const files = await Promise.all(GEO_FILES.map(async (n) => [n, await loadGeo(n)] as const));
      for (const [n, f] of files) {
        if (f) (map.getSource(n) as maplibregl.GeoJSONSource | undefined)?.setData(f.data);
      }
      setGeo(Object.fromEntries(files));
      // Satellite: Franco's tools/ writes geo/s2_box.png and geo/s2_box.json
      // ({"coordinates": [[lon,lat] top-left, top-right, bottom-right, bottom-left]}).
      try {
        const r = await fetch("geo/s2_box.json");
        if (!r.ok) throw new Error("missing");
        const meta = (await r.json()) as { coordinates: [number, number][] };
        map.addSource("s2", {
          type: "image",
          url: "geo/s2_box.png",
          coordinates: meta.coordinates as [[number, number], [number, number], [number, number], [number, number]],
        });
        // Under depth, coastline, bridge, lane and cables (#81): only the sea background is below it.
        map.addLayer({ id: "s2", type: "raster", source: "s2", layout: { visibility: "none" } }, "depth");
        onSatelliteState("ready");
      } catch {
        onSatelliteState("none");
      }
    });
    return () => {
      ro.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, [onSatelliteState]);

  useEffect(() => {
    const map = mapRef.current;
    if (loaded && map?.getLayer("s2")) {
      map.setLayoutProperty("s2", "visibility", satellite ? "visible" : "none");
      // the flat land fill would hide the image's land; the coastline line stays on top
      map.setLayoutProperty("land", "visibility", satellite ? "none" : "visible");
    }
  }, [satellite, loaded]);

  const geoText = useMemo(
    () => [...infraLabels(geo.infra?.data ?? null), ...(detail ? depthLabels(geo.depth?.data ?? null) : [])],
    [geo, detail],
  );

  useEffect(() => {
    const map = mapRef.current;
    const project = map ? (p: [number, number]) => { const q = map.project(p); return [q.x, q.y] as [number, number]; } : null;
    overlayRef.current?.setProps({ layers: buildLayers(snap, scene, conn === "lost", selected, selectedContact, showComms, hoverDecision, geoText, evalData, showRings, project) });
  }, [snap, scene, conn, selected, selectedContact, showComms, hoverDecision, geoText, evalData, showRings, view]);

  const credits = [...new Set(GEO_FILES.map((n) => geo[n]?.credit).filter((c): c is string => !!c))];
  if (satellite) credits.push("Contains modified Copernicus Sentinel data");
  const missing = loaded && Object.keys(geo).length ? GEO_FILES.filter((n) => !geo[n]) : [];
  return (
    <>
      <div ref={el} className="chart" />
      <div className="map-credit">
        {[missing.includes("land") ? "No coastline file yet (issue #9)" : null, ...credits].filter(Boolean).join(" · ")}
      </div>
    </>
  );
}

const labelSize = (d: Label) => (d.kind === "boat" || d.kind === "boat-stale" ? 16 : 14);
const labelOffset = (d: Label): [number, number] =>
  d.kind === "boat" || d.kind === "boat-stale" ? [0, -20] : d.kind === "cable" ? [0, -10]
    : d.kind === "docked" ? [-48, -12] : d.kind === "spread" ? [0, -10] : d.kind === "age" ? [0, -14]
      : d.kind === "geo" ? [0, 0] : [0, 16];

function buildLayers(
  snap: ReturnType<typeof useStore.getState>["snap"],
  scene: ReturnType<typeof useStore.getState>["scene"],
  frozen: boolean,
  selected: number | null,
  selectedContact: string | null,
  showComms: boolean,
  hoverDecision: string | null,
  geoText: LineLabel[],
  evalData: EvalData | null,
  showRings = true,
  project: ((p: [number, number]) => [number, number]) | null = null,
): Layer[] {
  const layers: Layer[] = [];
  const labels: Label[] = cableLabels();

  if (scene) {
    const st = Object.entries(scene.stations).map(([k, p]) => ({ k, pos: p }));
    layers.push(
      new ScatterplotLayer({
        id: "stations", data: st, getPosition: (d) => d.pos, radiusUnits: "pixels", getRadius: 6,
        stroked: true, filled: false, getLineColor: T.c(T.TEXT, 200), lineWidthUnits: "pixels", getLineWidth: 1.5,
      }),
      new PolygonLayer({
        id: "shore", data: [square(scene.shore[0], scene.shore[1], 250)], getPolygon: (d) => d,
        getFillColor: T.c(T.SHORE, 220), getLineColor: T.c(T.SHORE), stroked: true,
      }),
    );
    for (const s of st) {
      const name = s.k === "relay" ? "Relay station" : s.k === "pick:N" ? "Picket N" : "Picket S";
      labels.push({ pos: s.pos, text: name, kind: "station" });
    }
    labels.push({ pos: scene.shore, text: "Korsør (shore)", kind: "station" });
  }

  if (snap && scene) layers.push(...coverageLayers(snap, scene, frozen));
  if (snap && scene && showRings && !frozen) layers.push(...ringLayers(snap, scene));
  if (snap && scene) {
    // roadmap item 4: area a stale boat or contact could have reached since its last report
    const sp = spreads(snap, scene, frozen);
    layers.push(new PathLayer<Spread, PathStyleExtensionProps<Spread>>({
      id: "uncertainty", data: sp, getPath: (d) => circle(d.lon, d.lat, d.r_m, 96),
      getColor: T.c(T.STALE, 220), getWidth: 2, widthUnits: "pixels",
      getDashArray: [3, 3], dashJustified: true, extensions: [new PathStyleExtension({ dash: true })],
    }));
    for (const { s: d, text } of spreadLabels(sp)) {
      labels.push({ pos: offset(d.lon, d.lat, 0, d.r_m), text, kind: "spread" });
    }
  }
  if (snap && showComms) layers.push(...commsLayers(snap, scene?.shore ?? null, frozen));
  if (snap) layers.push(...ghostRoutes(snap, hoverDecision));

  if (snap) {
    const staleAfter = scene?.stale_after_s ?? 60;
    const isStale = (b: Boat) => frozen || b.heard === false || snap.t - b.last_heard > staleAfter;
    const boatColor = (b: Boat) => (isStale(b) ? T.STALE : T.FRIEND);
    const contactStale = (k: Contact) => frozen || snap.t - k.last_seen > staleAfter;
    const contactColor = (k: Contact) => (contactStale(k) ? T.STALE : k.ais ? T.NEUTRAL : T.UNKNOWN);
    const boatPos = new Map(snap.boats.map((b) => [b.id, [b.lon, b.lat] as [number, number]]));
    // seen-by lines: always for camera-only contacts, otherwise only for the selected contact
    const seenBy = snap.contacts
      .filter((k) => !contactStale(k) && (!k.ais || k.id === selectedContact))
      .flatMap((k) => k.seen_by.filter((id) => boatPos.has(id)).map((id) => ({ k, from: boatPos.get(id)! })));
    const moving = snap.contacts.filter((k) => !contactStale(k) && k.sog > 250); // > ~0.5 kn
    const squares = snap.contacts.filter((k) => k.ais);
    const dark = snap.contacts.filter((k) => !k.ais);
    const fused = snap.contacts.filter((k) => k.source === "fused" && !contactStale(k));
    const selC = snap.contacts.filter((k) => k.id === selectedContact);

    layers.push(
      new LineLayer<(typeof seenBy)[number]>({
        id: "seen-by", data: seenBy, getSourcePosition: (d) => d.from, getTargetPosition: (d) => [d.k.lon, d.k.lat],
        getColor: (d) => T.c(contactColor(d.k), 110), getWidth: 1, widthUnits: "pixels",
      }),
      new PathLayer<Contact>({
        id: "trails", data: snap.contacts.filter((k) => (k.trail?.length ?? 0) > 1),
        getPath: (k) => [...(k.trail ?? []), [k.lon, k.lat]], getColor: (k) => T.c(contactColor(k), 120),
        widthUnits: "pixels", getWidth: 1.5,
      }),
      new LineLayer<Contact>({
        id: "course-vectors", data: moving, getSourcePosition: (k) => [k.lon, k.lat],
        getTargetPosition: (k) => {
          const r = (k.cog * Math.PI) / 180;
          const d = (k.sog / 1000) * VECTOR_S;
          return offset(k.lon, k.lat, Math.sin(r) * d, Math.cos(r) * d);
        },
        getColor: (k) => T.c(contactColor(k)), getWidth: 1.5, widthUnits: "pixels",
      }),
      new IconLayer<Contact>({
        id: "contacts", data: [...squares, ...dark], pickable: true,
        getPosition: (k) => [k.lon, k.lat], getIcon: (k) => (k.ais ? ICON_TRIANGLE : ICON_QUATREFOIL),
        getAngle: (k) => (k.ais ? (360 - (k.cog ?? 0)) % 360 : 0),
        getSize: (k) => (k.ais ? 22 : 26), sizeUnits: "pixels", getColor: (k) => T.c(contactColor(k)),
      }),
      new ScatterplotLayer<Contact>({
        id: "contacts-fused", data: fused, getPosition: (k) => [k.lon, k.lat], radiusUnits: "pixels",
        getRadius: 11, filled: false, stroked: true, getLineColor: T.c(T.UNKNOWN, 160), lineWidthUnits: "pixels", getLineWidth: 1,
      }),
      new ScatterplotLayer<Contact>({
        id: "contact-selected", data: selC, getPosition: (k) => [k.lon, k.lat], radiusUnits: "pixels",
        getRadius: 20, filled: false, stroked: true, getLineColor: T.c(T.TEXT), lineWidthUnits: "pixels", getLineWidth: 2,
      }),
    );
    // Docked (UNAVAILABLE inside the agents' home radius, src/roles.ts):
    // a hollow ring and "DOCKED", so a boat beside the shore square is never read as the shore.
    const docked = (b: Boat) => isDocked(b, scene);
    const afloat = snap.boats.filter((b) => !docked(b));
    layers.push(
      new LineLayer<Boat>({
        id: "boat-heading", data: afloat,
        getSourcePosition: (b) => [b.lon, b.lat],
        getTargetPosition: (b) => {
          const r = ((b.hdg ?? 0) * Math.PI) / 180;
          return offset(b.lon, b.lat, Math.sin(r) * 700, Math.cos(r) * 700);
        },
        getColor: (b) => T.c(boatColor(b)), getWidth: 2, widthUnits: "pixels",
      }),
      new ScatterplotLayer<Boat>({
        id: "boats", data: afloat, getPosition: (b) => [b.lon, b.lat], radiusUnits: "pixels", pickable: true,
        getRadius: 9, getFillColor: (b) => T.c(boatColor(b), isStale(b) ? 120 : 230),
        stroked: true, getLineColor: [10, 20, 30, 255], lineWidthUnits: "pixels", getLineWidth: 1.5,
      }),
      new ScatterplotLayer<Boat>({
        id: "boats-docked", data: snap.boats.filter(docked), getPosition: (b) => [b.lon, b.lat],
        radiusUnits: "pixels", pickable: true, getRadius: 7, filled: false, stroked: true,
        getLineColor: (b) => T.c(boatColor(b), 230), lineWidthUnits: "pixels", getLineWidth: 2,
      }),
    );
    const sel = snap.boats.filter((b) => b.id === selected);
    layers.push(
      new ScatterplotLayer<Boat>({
        id: "boat-selected", data: sel, getPosition: (b) => [b.lon, b.lat], radiusUnits: "pixels",
        getRadius: 16, filled: false, stroked: true, getLineColor: T.c(T.TEXT), lineWidthUnits: "pixels", getLineWidth: 2,
      }),
    );
    for (const b of snap.boats) {
      const id = String(b.id).padStart(2, "0");
      if (docked(b)) labels.push({ pos: [b.lon, b.lat], text: `${id} DOCKED`, kind: "docked", ref: `boat:${b.id}` });
      else labels.push({ pos: [b.lon, b.lat], text: id, kind: isStale(b) ? "boat-stale" : "boat", ref: `boat:${b.id}` });
    }
    for (const k of snap.contacts) {
      const base = k.ais ? (k.name ?? k.track) : `${k.track} NO AIS`;
      const tag = k.source === "fused" ? `${base} · AIS+CAM` : base;
      const text = contactStale(k) && !frozen ? `${tag} · LAST SEEN ${dur(snap.t - k.last_seen)} AGO` : tag;
      labels.push({ pos: [k.lon, k.lat], text, kind: contactStale(k) ? "stale" : k.ais ? "ais" : "dark", ref: k.id });
    }
  }

  // Cable segment ages join the same overlap test as every other label.
  const ages: Label[] = snap && scene ? segAges(snap, scene).flatMap((a) => {
    const path = scene.segments[a.id] ?? [];
    return path.length > 1 ? [{ pos: path[Math.floor(path.length / 2)], kind: "age",
      text: `${a.id.slice(4)} ${a.age === null ? "no visit" : hmShort(a.age)}`, band: a.band }] : [];
  }) : [];
  // No overlapping text (map/declutter.ts): keep the most important label of any overlap.
  const all: Label[] = [...geoText.map((g) => ({ ...g, kind: "geo", geoKind: g.kind })), ...ages, ...labels];
  const keep = project
    ? keepNonOverlapping(all.map((d) => {
      const [x, y] = project(d.pos);
      const sel = d.ref !== undefined && (d.ref === selectedContact || d.ref === `boat:${selected}`);
      return { box: textBox(x, y, d.text, labelSize(d), labelOffset(d)), p: sel ? PRIORITY.selected : PRIORITY[d.kind] ?? 0 };
    }))
    : all.map(() => true);
  const kept = all.filter((_, i) => keep[i]);
  const geoKept: LineLabel[] = kept.filter((d) => d.kind === "geo").map((d) => ({ pos: d.pos, text: d.text, kind: d.geoKind ?? "" }));
  const agesKept = kept.filter((d) => d.kind === "age");
  const labelsKept = kept.filter((d) => d.kind !== "geo" && d.kind !== "age");
  if (geoKept.length) {
    layers.push(new TextLayer<LineLabel>({
      id: "geo-labels", data: geoKept, getPosition: (d) => d.pos, getText: (d) => d.text,
      getSize: 14,
      getColor: (d) => (d.kind === "depth" ? [120, 150, 175, 220] : [200, 200, 188, 230]),
      fontFamily: FONT, outlineWidth: 3, outlineColor: [12, 20, 28, 255], fontSettings: { sdf: true },
    }));
  }
  layers.push(new TextLayer<Label>({
    id: "coverage-age", data: agesKept, getPosition: (a) => a.pos, getText: (a) => a.text,
    getSize: 14, getColor: (a) => [...BAND_RGB[a.band ?? "none"], 255], getPixelOffset: [0, -14],
    fontFamily: FONT, outlineWidth: 3, outlineColor: [12, 20, 28, 255], fontSettings: { sdf: true },
  }));
  layers.push(
    new TextLayer<Label>({
      id: "labels", data: labelsKept, getPosition: (d) => d.pos, getText: (d) => d.text,
      fontFamily: FONT, characterSet: "auto", getSize: labelSize,
      getColor: (d) =>
        d.kind === "cable" ? [215, 160, 205, 230]
          : d.kind === "dark" ? T.c(T.UNKNOWN)
            : d.kind === "boat-stale" || d.kind === "stale" || d.kind === "docked" || d.kind === "spread" ? T.c(T.STALE)
              : T.c(T.TEXT, 235),
      getPixelOffset: labelOffset,
      outlineWidth: 3, outlineColor: [12, 20, 28, 255], fontSettings: { sdf: true },
    }),
  );
  if (evalData) layers.push(...evaluatorLayers(evalData)); // evaluator view only, on top
  return layers;
}
