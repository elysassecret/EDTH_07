// Owner: C. Panel layout state (remembered in this browser) and the drag handle (splitter)
// between a panel and the chart. Rules live in ../panels.ts.
import { useEffect, useRef, useState } from "react";
import { create } from "zustand";
import {
  DEFAULT_LAYOUT,
  LIMITS,
  STEP_PX,
  dragTo,
  maxSize,
  parseLayout,
  type Layout,
  type PanelId,
  type PanelState,
} from "../panels";

const KEY = "panel-layout";

function load(): Layout {
  try {
    return parseLayout(localStorage.getItem(KEY));
  } catch {
    return { ...DEFAULT_LAYOUT };
  }
}

interface LayoutStore {
  layout: Layout;
  set: (id: PanelId, p: PanelState) => void;
  show: (id: PanelId, open: boolean) => void;
  reset: () => void;
}

const save = (layout: Layout) => {
  try {
    localStorage.setItem(KEY, JSON.stringify(layout));
  } catch {
    /* private window: not remembered */
  }
  return { layout };
};

export const useLayout = create<LayoutStore>((setState, get) => ({
  layout: load(),
  set: (id, p) => setState(save({ ...get().layout, [id]: p })),
  show: (id, open) => setState(save({ ...get().layout, [id]: { ...get().layout[id], open } })),
  reset: () => setState(save({ ...DEFAULT_LAYOUT })),
}));

/** Window size, updated on resize. */
export function useViewport() {
  const [vp, setVp] = useState(() => ({ w: window.innerWidth, h: window.innerHeight }));
  useEffect(() => {
    const on = () => setVp({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return vp;
}

const NAME: Record<PanelId, string> = {
  fleet: "fleet panel",
  attention: "attention panel",
  timeline: "event timeline",
};

/**
 * Drag handle on one edge of a panel. `edge` is the side of the panel it sits on: the fleet
 * panel's handle is on its right, the attention panel's on its left, the timeline's on top.
 * Mouse/touch drag, or focus it and use the arrow keys; Home = minimum, End = largest allowed,
 * Enter hides the panel, double-click restores the default size.
 */
export function Splitter({
  id,
  edge,
  size,
  room,
}: {
  id: PanelId;
  edge: "left" | "right" | "top";
  size: number;
  room: number;
}) {
  const setPanel = useLayout((s) => s.set);
  const start = useRef<{ at: number; size: number } | null>(null);
  const [dragging, setDragging] = useState(false);
  const vertical = edge !== "top";
  const hi = maxSize(id, room);
  const sign = edge === "right" ? 1 : -1; // dragging toward the chart grows the panel

  const apply = (requested: number) => setPanel(id, dragTo(id, requested, room, start.current?.size ?? size));

  return (
    <div
      role="separator"
      tabIndex={0}
      aria-orientation={vertical ? "vertical" : "horizontal"}
      aria-label={`Resize ${NAME[id]}`}
      aria-valuemin={LIMITS[id].min}
      aria-valuemax={hi}
      aria-valuenow={size}
      title="Drag to resize. Push past the smallest size to hide it. Double-click: default size."
      data-dragging={dragging || undefined}
      className={[
        "panel-splitter absolute z-20 touch-none bg-transparent outline-none transition-colors",
        "hover:bg-primary/40 focus-visible:bg-primary/60 data-[dragging]:bg-primary/60",
        vertical ? "inset-y-0 w-1.5 cursor-col-resize" : "inset-x-0 h-1.5 cursor-row-resize",
        edge === "right" ? "-right-[3px]" : edge === "left" ? "-left-[3px]" : "-top-[3px]",
      ].join(" ")}
      onPointerDown={(e) => {
        if (e.button !== 0) return;
        e.preventDefault();
        e.currentTarget.setPointerCapture(e.pointerId);
        start.current = { at: vertical ? e.clientX : e.clientY, size };
        setDragging(true);
        document.documentElement.dataset.resizing = vertical ? "col" : "row";
      }}
      onPointerMove={(e) => {
        if (!start.current) return;
        const d = (vertical ? e.clientX : e.clientY) - start.current.at;
        apply(start.current.size + (edge === "top" ? -d : sign * d));
      }}
      onPointerUp={(e) => {
        e.currentTarget.releasePointerCapture(e.pointerId);
        start.current = null;
        setDragging(false);
        delete document.documentElement.dataset.resizing;
      }}
      onPointerCancel={() => {
        start.current = null;
        setDragging(false);
        delete document.documentElement.dataset.resizing;
      }}
      onDoubleClick={() => setPanel(id, { size: Math.min(LIMITS[id].def, hi), open: true })}
      onKeyDown={(e) => {
        const step = e.shiftKey ? STEP_PX * 4 : STEP_PX;
        const grow = vertical ? (edge === "right" ? "ArrowRight" : "ArrowLeft") : "ArrowUp";
        const shrink = vertical ? (edge === "right" ? "ArrowLeft" : "ArrowRight") : "ArrowDown";
        let next: PanelState | null = null;
        if (e.key === grow) next = { size: Math.min(hi, size + step), open: true };
        else if (e.key === shrink) next = { size: Math.max(LIMITS[id].min, size - step), open: true };
        else if (e.key === "Home") next = { size: LIMITS[id].min, open: true };
        else if (e.key === "End") next = { size: hi, open: true };
        else if (e.key === "Enter") next = { size, open: false };
        if (!next) return;
        e.preventDefault();
        setPanel(id, next);
      }}
    />
  );
}
