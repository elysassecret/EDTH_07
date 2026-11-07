// Owner: C. Panel layout state (remembered in this browser) and the drag handle (splitter)
// between a panel and the chart. Rules live in ../panels.ts.
import { useEffect, useRef, useState } from "react";
import {
  Activity,
  Bell,
  ClipboardCheck,
  PanelBottomOpen,
  PanelLeftOpen,
  PanelRightOpen,
  Radar,
} from "lucide-react";
import { staleBoat, usv } from "../console-model";
import { useStore } from "../store";
import { create } from "zustand";
import {
  DEFAULT_LAYOUT,
  LIMITS,
  STEP_PX,
  dragTo,
  settle,
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

  const apply = (requested: number) => setPanel(id, dragTo(id, requested, room));
  // end of a drag, however it ends (button up, cancel, capture lost, or this edge unmounting):
  // settle back inside the limits and give the page its normal cursor and text selection back
  const end = () => {
    if (!start.current) return;
    start.current = null;
    setDragging(false);
    delete document.documentElement.dataset.resizing;
    const now = useLayout.getState().layout[id];
    if (now.size !== settle(id, now.size, room)) setPanel(id, { ...now, size: settle(id, now.size, room) });
  };
  useEffect(
    () => () => {
      if (start.current) delete document.documentElement.dataset.resizing;
    },
    [],
  );

  return (
    <div
      role="separator"
      tabIndex={0}
      aria-orientation={vertical ? "vertical" : "horizontal"}
      aria-label={`Resize ${NAME[id]}`}
      aria-valuemin={LIMITS[id].min}
      aria-valuemax={hi}
      aria-valuenow={size}
      title="Drag to resize. Double-click: default size. Collapse with the icon in the panel header."
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
        if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
        end();
      }}
      onPointerCancel={end}
      onLostPointerCapture={end}
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

/**
 * A collapsed panel stays on screen as a narrow icon sidebar on its own edge: the minimum to keep
 * an eye on, and one click to expand. Fleet: one numbered dot per boat (dashed when its report
 * is old). Attention: decisions waiting, unacknowledged alerts, contacts. Timeline: event count.
 */
function RailButton({
  label,
  onClick,
  children,
  tone = "",
  pressed,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
  tone?: string;
  pressed?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={pressed}
      title={label}
      className={[
        "relative grid size-9 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors",
        "hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring",
        tone,
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function Count({ n, tone = "" }: { n: number; tone?: string }) {
  return (
    <span
      className={`absolute -right-1 -top-1 min-w-4 rounded-full border bg-background px-1 text-center text-[10px] leading-4 tabular-nums ${tone}`}
    >
      {n}
    </span>
  );
}

export function FleetRail({ onExpand }: { onExpand: () => void }) {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  const conn = useStore((s) => s.conn);
  const selected = useStore((s) => s.selected);
  const select = useStore((s) => s.select);
  const boats = [...(snap?.boats ?? [])].sort((a, b) => a.id - b.id);
  return (
    <nav aria-label="Fleet sidebar" className="flex w-12 shrink-0 flex-col items-center gap-2 overflow-y-auto border-r bg-muted/20 py-2">
      <RailButton label="Expand fleet panel" onClick={onExpand}>
        <PanelLeftOpen className="size-4" />
      </RailButton>
      {boats.map((b) => {
        const stale = snap ? staleBoat(b, snap, scene, conn) : true;
        const away = b.mode === "UNAVAILABLE" || b.mode === "RETURNING";
        return (
          <RailButton
            key={b.id}
            label={`${usv(b.id)} · ${b.mode}${stale ? " · report old" : ""}`}
            onClick={() => select(selected === b.id ? null : b.id)}
            pressed={selected === b.id}
            tone={selected === b.id ? "bg-muted text-foreground" : ""}
          >
            <span
              className={[
                "grid size-7 place-items-center rounded-full border-2 text-xs font-semibold tabular-nums",
                stale ? "border-dashed border-muted-foreground/60" : away ? "border-muted-foreground" : "border-sky-400 text-foreground",
              ].join(" ")}
            >
              {String(b.id).padStart(2, "0")}
            </span>
          </RailButton>
        );
      })}
    </nav>
  );
}

export function AttentionRail({ onExpand }: { onExpand: () => void }) {
  const snap = useStore((s) => s.snap);
  const decisions = snap?.decisions.filter((d) => d.state === "pending").length ?? 0;
  const alerts = snap?.alerts.filter((a) => !a.ack) ?? [];
  const alarm = alerts.some((a) => a.level === "alarm");
  const contacts = snap?.contacts.length ?? 0;
  return (
    <nav aria-label="Attention sidebar" className="flex w-12 shrink-0 flex-col items-center gap-3 border-l bg-muted/20 py-2">
      <RailButton label="Expand attention panel" onClick={onExpand}>
        <PanelRightOpen className="size-4" />
      </RailButton>
      <RailButton label={`Decisions waiting: ${decisions}`} onClick={onExpand} tone={decisions ? "text-amber-600 dark:text-amber-300" : ""}>
        <ClipboardCheck className="size-5" />
        <Count n={decisions} tone={decisions ? "border-amber-400" : ""} />
      </RailButton>
      <RailButton label={`Alerts not acknowledged: ${alerts.length}${alarm ? " (alarm)" : ""}`} onClick={onExpand} tone={alarm ? "text-red-500" : alerts.length ? "text-foreground" : ""}>
        <Bell className="size-5" />
        <Count n={alerts.length} tone={alarm ? "border-red-500" : ""} />
      </RailButton>
      <RailButton label={`Contacts reported: ${contacts}`} onClick={onExpand}>
        <Radar className="size-5" />
        <Count n={contacts} />
      </RailButton>
    </nav>
  );
}

export function TimelineRail({ onExpand }: { onExpand: () => void }) {
  const n = useStore((s) => s.snap?.events.length ?? 0);
  return (
    <button
      type="button"
      onClick={onExpand}
      aria-label={`Expand event timeline, ${n} events`}
      title="Expand event timeline"
      className="flex h-7 w-full shrink-0 items-center gap-2 border-t bg-muted/20 px-3 text-xs text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-ring"
    >
      <PanelBottomOpen className="size-4" />
      <Activity className="size-4" />
      <span className="tabular-nums">{n}</span>
    </button>
  );
}
