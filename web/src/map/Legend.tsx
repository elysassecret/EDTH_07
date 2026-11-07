// Owner: C. #88 item 2: an always-visible legend, drawn from the same colour constants the map
// uses (theme.ts, comms.ts, Chart.tsx BAND_RGB), so a change to the map changes the legend.
import { useState, type ReactElement } from "react";
import * as T from "./theme";
import { CUT, ROUTE, UP } from "./comms";
import { BAND_RGB, RING_DETECT, RING_KEEP, RING_STANDOFF } from "./Chart";

const rgba = (c: readonly number[], a?: number) =>
  `rgba(${c[0]},${c[1]},${c[2]},${a ?? (c.length > 3 ? (c[3] as number) / 255 : 1)})`;

function Line({ color, width = 2, dash }: { color: string; width?: number; dash?: string }) {
  return <svg width="28" height="14" aria-hidden="true"><line x1="1" y1="7" x2="27" y2="7" stroke={color} strokeWidth={width} strokeDasharray={dash} strokeLinecap="round" /></svg>;
}

const SWATCH: Record<string, ReactElement> = {
  power: <Line color={T.CABLE_POWER} width={3} />,
  data: <Line color={T.CABLE_DATA} width={3} />,
  lane: <Line color={T.LANE} dash="6 4" />,
  box: <Line color={T.BOX} width={1.5} dash="2 2" />,
  usv: <svg width="28" height="14" aria-hidden="true"><line x1="14" y1="7" x2="27" y2="2" stroke={rgba(T.FRIEND)} strokeWidth="2" /><circle cx="10" cy="7" r="5" fill={rgba(T.FRIEND, 0.9)} stroke="#0a141e" /></svg>,
  stale: <svg width="28" height="14" aria-hidden="true"><circle cx="10" cy="7" r="5" fill={rgba(T.STALE, 0.47)} stroke="#0a141e" /></svg>,
  ais: <svg width="28" height="14" aria-hidden="true"><rect x="5" y="2" width="10" height="10" fill={rgba(T.NEUTRAL, 0.35)} stroke={rgba(T.NEUTRAL)} strokeWidth="2" /></svg>,
  dark: <svg width="28" height="14" viewBox="0 0 28 14" aria-hidden="true"><g fill={rgba(T.UNKNOWN, 0.35)} stroke={rgba(T.UNKNOWN)} strokeWidth="1.2"><circle cx="10" cy="3.5" r="3" /><circle cx="10" cy="10.5" r="3" /><circle cx="6.5" cy="7" r="3" /><circle cx="13.5" cy="7" r="3" /></g></svg>,
  link: <svg width="28" height="14" aria-hidden="true"><line x1="1" y1="4" x2="27" y2="4" stroke={rgba(UP)} strokeWidth="1.5" /><line x1="1" y1="10" x2="27" y2="10" stroke={rgba(ROUTE)} strokeWidth="3" /></svg>,
  cut: <svg width="28" height="14" aria-hidden="true"><line x1="1" y1="7" x2="27" y2="7" stroke={rgba(CUT)} strokeWidth="2" strokeDasharray="6 4" /><path d="M10 2L18 12M18 2L10 12" stroke={rgba(CUT)} strokeWidth="2.5" strokeLinecap="round" /></svg>,
  rings: <svg width="28" height="14" aria-hidden="true"><circle cx="14" cy="7" r="6" fill={rgba(RING_KEEP, 0.25)} stroke={rgba(RING_DETECT, 0.8)} strokeWidth="1" /></svg>,
  standoff: <svg width="28" height="14" aria-hidden="true"><circle cx="14" cy="7" r="6" fill="none" stroke={rgba(RING_STANDOFF, 0.9)} strokeWidth="1.5" strokeDasharray="3 2" /></svg>,
  ghost: <Line color="rgba(230,236,242,0.8)" dash="4 3" />,
  band: <svg width="28" height="14" aria-hidden="true">{(["recent", "due", "over"] as const).map((b, i) => <line key={b} x1={1 + i * 9} y1="7" x2={8 + i * 9} y2="7" stroke={rgba(BAND_RGB[b], 0.9)} strokeWidth={b === "over" ? 8 : 6} />)}</svg>,
  none: <Line color={rgba(BAND_RGB.none, 0.9)} width={6} dash="3 2" />,
};

export const LEGEND_ROWS: [keyof typeof SWATCH, string][] = [
  ["power", "Power cable (ECDIS magenta)"],
  ["data", "Data cable"],
  ["lane", "Shipping lane"],
  ["box", "Patrol box"],
  ["usv", "USV, line shows heading"],
  ["stale", "USV not heard: last known place"],
  ["ais", "Contact with AIS"],
  ["dark", "Contact, NO AIS: a cue for a look"],
  ["rings", "Ring: camera range (ship, day) · fill: keep-in-view (model)"],
  ["standoff", "1 nm stand-off around a NO AIS contact"],
  ["link", "Radio link · thick: route to shore"],
  ["cut", "Link cut"],
  ["band", "Cable visited: recent · due · over target"],
  ["none", "Cable segment: no visit confirmed"],
  ["ghost", "Route a waiting decision proposes"],
];

export function Legend() {
  // open by default where it fits beside the box; on a 1280 px projector it starts folded to one line
  const [open, setOpen] = useState(() => window.matchMedia("(min-width: 1440px)").matches);
  return (
    <section aria-label="Chart legend" className="absolute bottom-9 left-2 z-10 max-w-[calc(100%_-_1rem)] rounded-md border bg-background/90 px-2 py-1 text-sm shadow-md">
      <button type="button" className="font-medium" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? "Legend ▾" : "Legend ▸"}
      </button>
      {open && (
        <ul className="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5">
          {LEGEND_ROWS.map(([k, text]) => (
            <li key={k} className="flex items-center gap-2 whitespace-nowrap">{SWATCH[k]}<span>{text}</span></li>
          ))}
        </ul>
      )}
    </section>
  );
}
