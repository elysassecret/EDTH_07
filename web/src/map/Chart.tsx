// Owner: C. Feature 17: offline chart. MapLibre draws the static vector layers;
// deck.gl draws everything that moves, and all text (no online glyphs in the style).
import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { StyleSpecification } from "maplibre-gl";
// Bundle MapLibre's worker with its imports so it loads offline in dev and in dist.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { LineLayer, PathLayer, PolygonLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import type { Layer } from "@deck.gl/core";
import { useStore } from "../store";
import type { Boat, Contact } from "../types";
import { boxBounds, boxGeo, cableLabels, cablesGeo, laneGeo, type Label } from "./scene";
import * as T from "./theme";

maplibregl.setWorkerUrl(workerUrl);

const FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif";
const M_PER_DEG_LAT = 111_320;

/** Offset a lon/lat point by metres east/north. */
function offset(lon: number, lat: number, e: number, n: number): [number, number] {
  return [lon + e / (M_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180)), lat + n / M_PER_DEG_LAT];
}

function square(lon: number, lat: number, half: number): [number, number][] {
  return [
    offset(lon, lat, -half, -half), offset(lon, lat, half, -half),
    offset(lon, lat, half, half), offset(lon, lat, -half, half),
  ];
}

const style: StyleSpecification = {
  version: 8,
  sources: {
    // absolute URL: the worker resolves relative URLs against its own location
    land: { type: "geojson", data: new URL("geo/land.geojson", window.location.href).href },
    box: { type: "geojson", data: boxGeo },
    cables: { type: "geojson", data: cablesGeo },
    lane: { type: "geojson", data: laneGeo },
  },
  layers: [
    { id: "sea", type: "background", paint: { "background-color": T.SEA } },
    { id: "land", type: "fill", source: "land", paint: { "fill-color": T.LAND } },
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
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  const conn = useStore((s) => s.conn);

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
    const overlay = new MapboxOverlay({ interleaved: false, layers: [] });
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
    map.on("load", async () => {
      setLoaded(true);
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
        map.addLayer({ id: "s2", type: "raster", source: "s2", layout: { visibility: "none" } }, "lane");
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
    }
  }, [satellite, loaded]);

  useEffect(() => {
    overlayRef.current?.setProps({ layers: buildLayers(snap, scene, conn === "lost") });
  }, [snap, scene, conn]);

  return <div ref={el} className="chart" />;
}

function buildLayers(
  snap: ReturnType<typeof useStore.getState>["snap"],
  scene: ReturnType<typeof useStore.getState>["scene"],
  frozen: boolean,
): Layer[] {
  const layers: Layer[] = [];
  const labels: Label[] = cableLabels();

  if (scene) {
    const st = Object.entries(scene.stations).map(([k, p]) => ({ k, pos: [p[1], p[0]] as [number, number] }));
    layers.push(
      new ScatterplotLayer({
        id: "stations", data: st, getPosition: (d) => d.pos, radiusUnits: "pixels", getRadius: 6,
        stroked: true, filled: false, getLineColor: T.c(T.TEXT, 200), lineWidthUnits: "pixels", getLineWidth: 1.5,
      }),
      new PolygonLayer({
        id: "shore", data: [square(scene.shore[1], scene.shore[0], 250)], getPolygon: (d) => d,
        getFillColor: T.c(T.SHORE, 220), getLineColor: T.c(T.SHORE), stroked: true,
      }),
    );
    for (const s of st) {
      const name = s.k === "relay" ? "Relay station" : s.k === "pick:N" ? "Picket N" : "Picket S";
      labels.push({ pos: s.pos, text: name, kind: "station" });
    }
    labels.push({ pos: [scene.shore[1], scene.shore[0]], text: "Korsør (shore)", kind: "station" });
  }

  if (snap) {
    const staleAfter = scene?.stale_after_s ?? 60;
    const isStale = (b: Boat) => frozen || b.heard === false || snap.t - b.last_heard > staleAfter;
    const boatColor = (b: Boat) => (isStale(b) ? T.STALE : T.FRIEND);
    const contactColor = (k: Contact) => (frozen ? T.STALE : k.ais ? T.NEUTRAL : T.UNKNOWN);

    layers.push(
      new PathLayer<Contact>({
        id: "trails", data: snap.contacts.filter((k) => (k.trail?.length ?? 0) > 1),
        getPath: (k) => (k.trail ?? []).map((p): [number, number] => [p[1], p[0]]), getColor: (k) => T.c(contactColor(k), 120),
        widthUnits: "pixels", getWidth: 1.5,
      }),
      new PolygonLayer<Contact>({
        id: "contacts", data: snap.contacts, getPolygon: (k) => square(k.lon, k.lat, 180),
        getFillColor: (k) => T.c(contactColor(k), k.ais ? 90 : 60), getLineColor: (k) => T.c(contactColor(k)),
        getLineWidth: 2, lineWidthUnits: "pixels", stroked: true,
      }),
      new LineLayer<Boat>({
        id: "boat-heading", data: snap.boats,
        getSourcePosition: (b) => [b.lon, b.lat],
        getTargetPosition: (b) => {
          const r = ((b.hdg ?? 0) * Math.PI) / 180;
          return offset(b.lon, b.lat, Math.sin(r) * 700, Math.cos(r) * 700);
        },
        getColor: (b) => T.c(boatColor(b)), getWidth: 2, widthUnits: "pixels",
      }),
      new ScatterplotLayer<Boat>({
        id: "boats", data: snap.boats, getPosition: (b) => [b.lon, b.lat], radiusUnits: "pixels",
        getRadius: 9, getFillColor: (b) => T.c(boatColor(b), isStale(b) ? 120 : 230),
        stroked: true, getLineColor: [10, 20, 30, 255], lineWidthUnits: "pixels", getLineWidth: 1.5,
      }),
    );
    for (const b of snap.boats) {
      labels.push({ pos: [b.lon, b.lat], text: String(b.id).padStart(2, "0"), kind: isStale(b) ? "boat-stale" : "boat" });
    }
    for (const k of snap.contacts) {
      const tag = k.ais ? (k.name ?? k.track) : `${k.track} NO AIS`;
      labels.push({ pos: [k.lon, k.lat], text: tag, kind: k.ais ? "ais" : "dark" });
    }
  }

  layers.push(
    new TextLayer<Label>({
      id: "labels", data: labels, getPosition: (d) => d.pos, getText: (d) => d.text,
      fontFamily: FONT, characterSet: "auto", getSize: (d) => (d.kind === "boat" || d.kind === "boat-stale" ? 15 : 13),
      getColor: (d) =>
        d.kind === "cable" ? [215, 160, 205, 230]
          : d.kind === "dark" ? T.c(T.UNKNOWN)
            : d.kind === "boat-stale" ? T.c(T.STALE)
              : T.c(T.TEXT, 235),
      getPixelOffset: (d) => (d.kind === "boat" || d.kind === "boat-stale" ? [0, -20] : d.kind === "cable" ? [0, -10] : [0, 16]),
      outlineWidth: 3, outlineColor: [12, 20, 28, 255], fontSettings: { sdf: true },
    }),
  );
  return layers;
}
