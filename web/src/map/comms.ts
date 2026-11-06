// Owner: C. Feature 21: comms overlay. Who can talk to whom, each boat's route to shore,
// and lost links drawn dashed with a cross, so the operator sees why a boat is cut off.
// The shore only knows links that boats report; this is the shore's picture, not radio truth.
import { IconLayer, LineLayer, PathLayer, TextLayer } from "@deck.gl/layers";
import { PathStyleExtension, type PathStyleExtensionProps } from "@deck.gl/extensions";
import type { Layer } from "@deck.gl/core";
import type { Boat, Link, LonLat, Snapshot } from "../types";

const UP: [number, number, number, number] = [120, 170, 210, 110];
const ROUTE: [number, number, number, number] = [150, 200, 255, 230];
const CUT: [number, number, number, number] = [235, 95, 85, 255];
const DOWN: [number, number, number, number] = [140, 146, 152, 170];
// inline SVG mask (offline), tinted red: the cross marks an injected link cut
const ICON_CROSS = {
  id: "x", width: 32, height: 32, mask: true,
  url: `data:image/svg+xml;charset=utf-8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><path d="M6 6L26 26M26 6L6 26" stroke="#fff" stroke-width="6" stroke-linecap="round"/></svg>')}`,
};
const FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif";

interface Seg { from: LonLat; to: LonLat; link: Link }

export function commsLayers(snap: Snapshot, shore: LonLat | null, frozen: boolean): Layer[] {
  const pos = new Map<number, LonLat>(snap.boats.map((b) => [b.id, [b.lon, b.lat]]));
  if (shore) pos.set(0, shore);
  const at = (n: number | "shore") => pos.get(n === "shore" ? 0 : n);

  const segs: Seg[] = [];
  for (const link of snap.links) {
    const a = at(link.a);
    const b = at(link.b);
    if (a && b) segs.push({ from: a, to: b, link });
  }
  const up = segs.filter((s) => s.link.state === "up");
  const broken = segs.filter((s) => s.link.state !== "up");

  // each boat's next hop toward shore (via), drawn brighter on top of the plain links
  // A peer-linked boat never routes straight to shore (via 0): the shore's path guess can
  // treat a one-way link as two-way, so that line would contradict the cut it sits on.
  const routes = snap.boats
    .filter((b: Boat) => b.link !== "none" && b.via !== null && b.via !== undefined && pos.has(b.via))
    .filter((b: Boat) => (b.link === "direct") === (b.via === 0))
    .map((b) => ({ from: [b.lon, b.lat] as LonLat, to: pos.get(b.via as number)! }));

  const mid = (s: Seg): LonLat => [(s.from[0] + s.to[0]) / 2, (s.from[1] + s.to[1]) / 2];
  const dim = (c: [number, number, number, number]) =>
    (frozen ? [c[0], c[1], c[2], Math.round(c[3] * 0.5)] : c) as [number, number, number, number];

  return [
    new LineLayer<Seg>({
      id: "comms-up", data: up, getSourcePosition: (s) => s.from, getTargetPosition: (s) => s.to,
      getColor: dim(UP), getWidth: 1.5, widthUnits: "pixels",
    }),
    new LineLayer<{ from: LonLat; to: LonLat }>({
      id: "comms-route", data: routes, getSourcePosition: (s) => s.from, getTargetPosition: (s) => s.to,
      getColor: dim(ROUTE), getWidth: 3, widthUnits: "pixels",
    }),
    // LineLayer has no dashes; a two-point PathLayer does, via PathStyleExtension
    new PathLayer<Seg, PathStyleExtensionProps<Seg>>({
      id: "comms-broken", data: broken,
      getPath: (s: Seg) => [s.from, s.to],
      getColor: (s: Seg) => dim(s.link.state === "cut" ? CUT : DOWN),
      getWidth: 2.5, widthUnits: "pixels",
      getDashArray: [6, 4], dashJustified: true,
      extensions: [new PathStyleExtension({ dash: true })],
    }),
    new IconLayer<Seg>({
      id: "comms-cross", data: broken.filter((s) => s.link.state === "cut"),
      getPosition: mid, getIcon: () => ICON_CROSS, getSize: 18, sizeUnits: "pixels", getColor: dim(CUT),
    }),
    new TextLayer<Seg>({
      id: "comms-cut-label", data: broken.filter((s) => s.link.state === "cut"),
      getPosition: mid, getText: () => "LINK CUT", getSize: 12, getColor: dim(CUT), getPixelOffset: [0, 16],
      fontFamily: FONT, outlineWidth: 3, outlineColor: [12, 20, 28, 255], fontSettings: { sdf: true },
    }),
  ];
}
