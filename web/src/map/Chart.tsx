// Owner: C. Feature 17: offline chart. MapLibre draws the static vector layers;
// deck.gl draws everything that moves, and all text (no online glyphs in the style).
import { useEffect, useRef, useState } from "react";
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
import * as T from "./theme";

maplibregl.setWorkerUrl(workerUrl);

const FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif";
const M_PER_DEG_LAT = 111_320;

/** Offset a lon/lat point by metres east/north. */
function offset(lon: number, lat: number, e: number, n: number): [number, number] {
  return [lon + e / (M_PER_DEG_LAT * Math.cos((lat * Math.PI) / 180)), lat + n / M_PER_DEG_LAT];
}

// Track symbols as inline SVG masks (no network), tinted by colour, fixed pixel size.
// AIS = square (neutral); camera only = quatrefoil (unknown), so shape alone tells them apart.
const svg = (body: string) =>
  `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">${body}</svg>`)}`;
const ICON_SQUARE = { id: "sq", url: svg('<rect x="10" y="10" width="44" height="44" fill="none" stroke="#fff" stroke-width="7"/><rect x="18" y="18" width="28" height="28" fill="#fff" fill-opacity="0.35"/>'), width: 64, height: 64, mask: true };
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
  const selected = useStore((s) => s.selected);
  const selectedContact = useStore((s) => s.selectedContact);

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
        if (o && typeof o.id === "number") st.select(o.id);
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
    overlayRef.current?.setProps({ layers: buildLayers(snap, scene, conn === "lost", selected, selectedContact) });
  }, [snap, scene, conn, selected, selectedContact]);

  return <div ref={el} className="chart" />;
}

function buildLayers(
  snap: ReturnType<typeof useStore.getState>["snap"],
  scene: ReturnType<typeof useStore.getState>["scene"],
  frozen: boolean,
  selected: number | null,
  selectedContact: string | null,
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
        getPosition: (k) => [k.lon, k.lat], getIcon: (k) => (k.ais ? ICON_SQUARE : ICON_QUATREFOIL),
        getSize: (k) => (k.ais ? 18 : 26), sizeUnits: "pixels", getColor: (k) => T.c(contactColor(k)),
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
    layers.push(
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
        id: "boats", data: snap.boats, getPosition: (b) => [b.lon, b.lat], radiusUnits: "pixels", pickable: true,
        getRadius: 9, getFillColor: (b) => T.c(boatColor(b), isStale(b) ? 120 : 230),
        stroked: true, getLineColor: [10, 20, 30, 255], lineWidthUnits: "pixels", getLineWidth: 1.5,
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
      labels.push({ pos: [b.lon, b.lat], text: String(b.id).padStart(2, "0"), kind: isStale(b) ? "boat-stale" : "boat" });
    }
    for (const k of snap.contacts) {
      const base = k.ais ? (k.name ?? k.track) : `${k.track} NO AIS`;
      const tag = k.source === "fused" ? `${base} · AIS+CAM` : base;
      const text = contactStale(k) && !frozen ? `${tag} · LAST SEEN ${dur(snap.t - k.last_seen)} AGO` : tag;
      labels.push({ pos: [k.lon, k.lat], text, kind: contactStale(k) ? "stale" : k.ais ? "ais" : "dark" });
    }
  }

  layers.push(
    new TextLayer<Label>({
      id: "labels", data: labels, getPosition: (d) => d.pos, getText: (d) => d.text,
      fontFamily: FONT, characterSet: "auto", getSize: (d) => (d.kind === "boat" || d.kind === "boat-stale" ? 15 : 13),
      getColor: (d) =>
        d.kind === "cable" ? [215, 160, 205, 230]
          : d.kind === "dark" ? T.c(T.UNKNOWN)
            : d.kind === "boat-stale" || d.kind === "stale" ? T.c(T.STALE)
              : T.c(T.TEXT, 235),
      getPixelOffset: (d) => (d.kind === "boat" || d.kind === "boat-stale" ? [0, -20] : d.kind === "cable" ? [0, -10] : [0, 16]),
      outlineWidth: 3, outlineColor: [12, 20, 28, 255], fontSettings: { sdf: true },
    }),
  );
  return layers;
}
