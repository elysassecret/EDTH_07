// Owner: C. Resizable console panels: the fleet list (left), the attention workspace (right)
// and the event timeline (bottom). Pure rules, no DOM, so they are unit-tested.
// - A drag never makes a panel bigger than its maximum, or than the room left for the chart.
// - A drag never closes a panel: below the minimum it gives a little (DRAG_SLACK_PX, so the
//   edge still follows the hand) and settles back at the minimum on release. Collapsing to the
//   icon sidebar is a deliberate act: the collapse icon in the panel header, or Enter on the edge.
// Sizes are screen pixels (layout only, not sim data).

export type PanelId = "fleet" | "attention" | "timeline";

export interface Limits {
  min: number;
  max: number;
  def: number;
}

export const LIMITS: Record<PanelId, Limits> = {
  fleet: { min: 240, max: 520, def: 280 }, // width
  attention: { min: 320, max: 720, def: 380 }, // width
  timeline: { min: 72, max: 480, def: 96 }, // height of the event list
};

export const DRAG_SLACK_PX = 24; // a drag may go this far under the minimum; released, it settles back
export const STEP_PX = 16; // arrow key step on a splitter (Shift: 4 steps)
export const CHART_MIN_W = 360; // the chart always keeps at least this much width
export const TIMELINE_MAX_SHARE = 0.5; // the event list never takes more than half the window height

export interface PanelState {
  size: number; // last open size, kept while closed
  open: boolean;
}
export type Layout = Record<PanelId, PanelState>;

export const DEFAULT_LAYOUT: Layout = {
  fleet: { size: LIMITS.fleet.def, open: true },
  attention: { size: LIMITS.attention.def, open: true },
  timeline: { size: LIMITS.timeline.def, open: true },
};

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** Largest size allowed now: the panel's maximum, or the room left, never below its minimum. */
export function maxSize(id: PanelId, room: number): number {
  const { min, max } = LIMITS[id];
  return Math.max(min, Math.min(max, Math.floor(room)));
}

/** Where a drag to `requested` px leaves the panel while the button is held: between the
 * minimum less DRAG_SLACK_PX and the largest allowed. It never closes the panel. */
export function dragTo(id: PanelId, requested: number, room: number): PanelState {
  const { min } = LIMITS[id];
  return { size: clamp(Math.round(requested), min - DRAG_SLACK_PX, maxSize(id, room)), open: true };
}

/** Where the panel settles when the drag ends: back inside its limits. */
export function settle(id: PanelId, size: number, room: number): number {
  return clamp(size, LIMITS[id].min, maxSize(id, room));
}

/** Which panels are shown inline at this window width (narrower windows use drawers). */
export function inline(vw: number): { fleet: boolean; attention: boolean } {
  return { fleet: vw >= 1440, attention: vw >= 1280 };
}

/** Sizes to draw at this window size: open, inline panels shrink (down to their minimum) so the
 * chart keeps CHART_MIN_W. 0 = not drawn. The attention panel keeps its size first. */
export function fit(layout: Layout, vw: number, vh: number): Record<PanelId, number> {
  const show = inline(vw);
  const fleetOn = show.fleet && layout.fleet.open;
  const attOn = show.attention && layout.attention.open;
  const att = attOn
    ? Math.min(layout.attention.size, maxSize("attention", vw - CHART_MIN_W - (fleetOn ? LIMITS.fleet.min : 0)))
    : 0;
  const fleet = fleetOn ? Math.min(layout.fleet.size, maxSize("fleet", vw - CHART_MIN_W - att)) : 0;
  const timeline = layout.timeline.open
    ? Math.min(layout.timeline.size, maxSize("timeline", vh * TIMELINE_MAX_SHARE))
    : 0;
  return { fleet, attention: att, timeline };
}

/** Room a panel may grow into: the chart keeps CHART_MIN_W (or half the height for the timeline). */
export function roomFor(id: PanelId, vw: number, vh: number, drawn: Record<PanelId, number>): number {
  if (id === "timeline") return vh * TIMELINE_MAX_SHARE;
  const other = id === "fleet" ? drawn.attention : drawn.fleet;
  return vw - CHART_MIN_W - other;
}

/** A stored layout, checked: unknown or broken values fall back to the defaults. */
export function parseLayout(raw: string | null): Layout {
  let data: unknown = null;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {
    data = null;
  }
  const out = { ...DEFAULT_LAYOUT };
  if (!data || typeof data !== "object") return out;
  for (const id of Object.keys(LIMITS) as PanelId[]) {
    const p = (data as Record<string, unknown>)[id] as Partial<PanelState> | undefined;
    if (!p || typeof p.size !== "number" || !Number.isFinite(p.size) || typeof p.open !== "boolean") continue;
    out[id] = { size: clamp(Math.round(p.size), LIMITS[id].min, LIMITS[id].max), open: p.open };
  }
  return out;
}
