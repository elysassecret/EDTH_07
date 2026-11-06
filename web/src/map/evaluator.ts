// Owner: C. Evaluator overlay (truth), drawn only while the evaluator view is on.
// Purple everywhere, hollow and dashed, so it never looks like the operator's own picture:
//   - a hollow purple ring where each boat really is, a thin line from where the shore last
//     heard it, and the gap in metres when it is more than a few boat lengths;
//   - true contacts the shore picture does not have, labelled "truth only".
import { LineLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import type { Layer } from "@deck.gl/core";
import type { EvalData, LonLat } from "../types";

export const TRUTH: [number, number, number] = [190, 140, 255];
const FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif";
const LABEL_FROM_M = 100; // write the offset only when it is visible at chart scale

type B = EvalData["boats"][number];
type C = EvalData["contacts"][number];

export function evaluatorLayers(ev: EvalData): Layer[] {
  const moved = ev.boats.filter((b) => b.shore && (b.offset_m ?? 0) > 0);
  const hidden = ev.contacts.filter((c) => !c.on_shore);
  return [
    new LineLayer<B>({
      id: "eval-offset", data: moved, getSourcePosition: (b) => b.shore as LonLat, getTargetPosition: (b) => b.true,
      getColor: [...TRUTH, 200], getWidth: 1.5, widthUnits: "pixels",
    }),
    new ScatterplotLayer<B>({
      id: "eval-true-boats", data: ev.boats, getPosition: (b) => b.true, radiusUnits: "pixels", getRadius: 9,
      filled: false, stroked: true, getLineColor: [...TRUTH, 255], lineWidthUnits: "pixels", getLineWidth: 2,
    }),
    new TextLayer<B>({
      id: "eval-offset-label", data: moved.filter((b) => (b.offset_m ?? 0) >= LABEL_FROM_M),
      getPosition: (b) => b.true, getText: (b) => `true ${String(b.id).padStart(2, "0")} · ${b.offset_m} m off`,
      getSize: 11, getColor: [...TRUTH, 255], getPixelOffset: [0, 18],
      fontFamily: FONT, outlineWidth: 3, outlineColor: [12, 20, 28, 255], fontSettings: { sdf: true },
    }),
    new ScatterplotLayer<C>({
      id: "eval-hidden-contacts", data: hidden, getPosition: (c) => c.pos, radiusUnits: "pixels", getRadius: 11,
      filled: false, stroked: true, getLineColor: [...TRUTH, 255], lineWidthUnits: "pixels", getLineWidth: 2,
    }),
    new TextLayer<C>({
      id: "eval-hidden-label", data: hidden, getPosition: (c) => c.pos,
      getText: (c) => `${c.track ?? c.id} · truth only, not on shore picture`,
      getSize: 11, getColor: [...TRUTH, 255], getPixelOffset: [0, -18],
      fontFamily: FONT, outlineWidth: 3, outlineColor: [12, 20, 28, 255], fontSettings: { sdf: true },
    }),
  ];
}
