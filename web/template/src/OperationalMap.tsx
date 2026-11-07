import { useState } from "react";
import { Crosshair, Layers3, Minus, Plus, Radio, Route } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import {
  fleet,
  type CommandState,
  type Scenario,
  type Selection,
} from "./model";
import land from "./assets/land.json";
const project = (p: number[]) =>
  `${(((p[0] - 10.76) / 0.46) * 900).toFixed(1)},${(((55.5 - p[1]) / 0.34) * 750).toFixed(1)}`;
const coast = land.features.map((f) =>
  f.geometry.coordinates.map((r) => `M${r.map(project).join("L")}Z`).join(""),
);
export function OperationalMap({
  scenario,
  selection,
  onSelect,
  command,
  preview,
  onPreview,
  gapClosed,
}: {
  scenario: Scenario;
  selection: Selection;
  onSelect: (s: Selection) => void;
  command: CommandState;
  preview: boolean;
  onPreview: () => void;
  gapClosed: boolean;
}) {
  const [zoom, setZoom] = useState(1);
  const [links, setLinks] = useState(true);
  const [legend, setLegend] = useState(false);
  const [layers, setLayers] = useState(false);
  const [cables, setCables] = useState(true);
  const frozen = scenario === "lost" || scenario === "recovery";
  const gap = scenario === "gap" && !gapClosed;
  const cut = scenario === "exercise";
  const stale = scenario === "stale";
  function mapKey(e: React.KeyboardEvent<SVGGElement>, action: () => void) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      action();
    }
  }
  return (
    <section
      className={cn(
        "relative isolate min-h-0 overflow-hidden bg-background",
        frozen && "map-frozen",
      )}
      aria-label="Great Belt operational chart"
    >
      <div className="absolute left-5 top-5 flex flex-col gap-2 bg-background/90 p-2">
        <p className="text-xs text-muted-foreground">AREA OF OPERATIONS</p>
        <h2 className="font-semibold">Great Belt / Denmark</h2>
        <p className="text-sm text-muted-foreground">
          Cable protection sector · Korsør
        </p>
        <Badge variant="outline">
          {frozen ? "FROZEN · 14:32:18Z" : "SYNTHETIC OBSERVATIONS"}
        </Badge>
      </div>
      <svg
        className="operational-chart"
        viewBox="0 0 900 750"
        aria-label="Offline schematic chart. Synthetic vessel positions; not for navigation."
        role="group"
      >
        <defs>
          <pattern
            id="chart-grid"
            width="150"
            height="150"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M150 0H0V150"
              fill="none"
              stroke="#262626"
              strokeWidth=".65"
            />
          </pattern>
          <pattern
            id="lane-hatch"
            width="12"
            height="12"
            patternTransform="rotate(25)"
            patternUnits="userSpaceOnUse"
          >
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="12"
              stroke="#53606a"
              strokeWidth=".5"
            />
          </pattern>
        </defs>
        <rect width="900" height="750" fill="#0a0a0a" />
        <rect width="900" height="750" fill="url(#chart-grid)" />
        <g
          transform={`translate(${450 - 450 * zoom} ${375 - 375 * zoom}) scale(${zoom})`}
        >
          {coast.map((d, i) => (
            <path
              key={i}
              d={d}
              fill="#262626"
              stroke="#404040"
              strokeWidth="1"
            />
          ))}
          <path
            d="M245 -40L85 790M335 -40L175 790"
            stroke="#53616c"
            strokeDasharray="7 8"
            fill="none"
          />
          <path
            d="M245 -40L85 790H175L335 -40Z"
            fill="url(#lane-hatch)"
            opacity=".32"
          />
          <text
            className="sea-label"
            x="340"
            y="340"
            transform="rotate(-77 340 340)"
          >
            G R E A T B E L T
          </text>
          <text className="land-label" x="75" y="615">
            FUNEN
          </text>
          <text className="land-label" x="780" y="230">
            ZEALAND
          </text>
          <text
            className="map-small muted"
            x="145"
            y="450"
            transform="rotate(-77 145 450)"
          >
            TRAFFIC SEPARATION SCHEME
          </text>
          <path d="M190 450L700 340" stroke="#52606a" strokeWidth="4" />
          <path
            d="M190 450L700 340"
            stroke="#8a969c"
            strokeWidth="1"
            strokeDasharray="3 6"
          />
          <text
            className="map-small muted"
            x="495"
            y="365"
            transform="rotate(-12 495 365)"
          >
            GREAT BELT BRIDGE
          </text>
          {cables && (
            <g>
              <path
                d="M180 75C290 150 530 215 780 125"
                fill="none"
                stroke="#c570bc"
                strokeWidth="2"
              />
              <path
                d="M120 570C280 545 360 510 480 553S650 620 805 635"
                fill="none"
                stroke="#c570bc"
                strokeWidth="2"
              />
              <path
                d="M120 600C280 575 360 540 480 583S650 650 805 665"
                fill="none"
                stroke="#9a83d9"
                strokeWidth="2"
              />
              <path
                d="M180 75C250 120 325 155 425 170"
                fill="none"
                stroke="#5bafa2"
                strokeWidth="9"
                opacity=".25"
              />
              <path
                d="M425 170Q560 210 655 170"
                fill="none"
                stroke="#5bafa2"
                strokeWidth="9"
                opacity=".25"
              />
              <path
                d="M120 570Q270 547 365 534"
                fill="none"
                stroke="#5bafa2"
                strokeWidth="9"
                opacity=".25"
              />
              <g
                role="button"
                tabIndex={0}
                aria-label="Inspect coverage segment P-04"
                onClick={() => onSelect({ kind: "segment", id: "P-04" })}
                onKeyDown={(e) =>
                  mapKey(e, () => onSelect({ kind: "segment", id: "P-04" }))
                }
                className="map-entity"
              >
                <path
                  d="M365 534Q430 534 480 553"
                  fill="none"
                  stroke={gap ? "#eda65d" : "#c570bc"}
                  strokeWidth="9"
                  opacity=".4"
                />
                <path
                  d="M365 534Q430 534 480 553"
                  fill="none"
                  stroke="transparent"
                  strokeWidth="26"
                />
                <text
                  className="map-label"
                  x="405"
                  y="580"
                  fill={gap ? "#edb170" : "#d698ce"}
                >
                  {gap ? "P-04 · GAP OPEN" : "P-04"}
                </text>
              </g>
              <text className="map-small" x="540" y="130" fill="#d698ce">
                POWER CABLE · P-01—P-03
              </text>
              <text className="map-small" x="545" y="685" fill="#b29eea">
                DATA CABLE · D-01—D-02
              </text>
            </g>
          )}
          {links && (
            <g fill="none">
              <path
                d="M605 480L568 285L424 175"
                stroke="#467da4"
                strokeWidth="1.2"
                opacity=".6"
              />
              <path
                d="M605 480L388 408"
                stroke="#60a6e6"
                strokeWidth="1.8"
                opacity=".75"
              />
              <path
                d="M715 555L605 480"
                stroke={cut ? "#dc7c7c" : "#60a6e6"}
                strokeWidth="1.8"
                strokeDasharray={cut ? "7 6" : undefined}
                opacity=".75"
              />
              {cut && (
                <>
                  <path
                    d="M647 510l14 14m0-14l-14 14"
                    stroke="#f18181"
                    strokeWidth="3"
                  />
                  <text x="470" y="455" className="map-label" fill="#f18181">
                    EXERCISE CUT · 04 ↔ SHORE
                  </text>
                </>
              )}
            </g>
          )}
          <path
            d="M388 408L377 470L320 515"
            fill="none"
            stroke="#6b98bb"
            strokeWidth="1.5"
            opacity=".7"
          />
          {(preview || command === "accepted" || command === "completed") && (
            <g>
              <path
                d={
                  scenario === "contact"
                    ? "M568 285L554 254L535 230"
                    : scenario === "exercise"
                      ? "M388 408L605 480"
                      : "M388 408L438 468L477 550L547 570"
                }
                fill="none"
                stroke={
                  command === "accepted" || command === "completed"
                    ? "#68abe7"
                    : "#d9ba78"
                }
                strokeWidth="2"
                strokeDasharray={
                  command === "accepted" || command === "completed"
                    ? undefined
                    : "7 6"
                }
              />
              <text
                className="map-small"
                x={scenario === "contact" ? "490" : "465"}
                y={scenario === "contact" ? "310" : "490"}
                fill="#d9ba78"
              >
                {scenario === "exercise"
                  ? "DELEGATED RELAY TASK · LAST KNOWN"
                  : command === "accepted"
                    ? "ACCEPTED · NOT COMPLETED"
                    : command === "completed"
                      ? "OBSERVATION RECORDED"
                      : "PROPOSED · NOT EXECUTING"}
              </text>
            </g>
          )}
          <g
            role="button"
            tabIndex={0}
            onClick={() => onSelect({ kind: "contact", id: "AIS-108" })}
            onKeyDown={(e) =>
              mapKey(e, () => onSelect({ kind: "contact", id: "AIS-108" }))
            }
            aria-label="Select AIS vessel Nordic Freighter"
            className="map-entity"
          >
            <path d="M245 185L251 151" stroke="#6fb99b" />
            <rect
              x="239"
              y="179"
              width="12"
              height="12"
              rx="1"
              fill="#8ac4a6"
            />
            <text className="map-small" x="263" y="191" fill="#9bb8aa">
              NORDIC FREIGHTER
            </text>
          </g>
          <g
            role="button"
            tabIndex={0}
            onClick={() => onSelect({ kind: "contact", id: "AIS-112" })}
            onKeyDown={(e) =>
              mapKey(e, () => onSelect({ kind: "contact", id: "AIS-112" }))
            }
            aria-label="Select fused AIS and camera vessel Baltic Trader"
            className="map-entity"
          >
            <circle cx="207" cy="590" r="12" fill="none" stroke="#dfc678" />
            <rect x="201" y="584" width="12" height="12" fill="#8ac4a6" />
            <text className="map-small" x="228" y="595" fill="#9bb8aa">
              BALTIC TRADER
            </text>
          </g>
          <g
            role="button"
            tabIndex={0}
            onClick={() => onSelect({ kind: "contact", id: "C-024" })}
            onKeyDown={(e) =>
              mapKey(e, () => onSelect({ kind: "contact", id: "C-024" }))
            }
            aria-label="Inspect camera-only contact C-024. No AIS correlation"
            className="map-entity"
          >
            <circle
              cx="535"
              cy="230"
              r={selection?.id === "C-024" ? 24 : 19}
              fill="#ddbd6720"
              stroke="#d9bb70"
              strokeDasharray="3 4"
            />
            <path
              d="M535 218Q543 218 541 224Q549 222 547 230Q549 238 541 236Q543 244 535 242Q527 244 529 236Q521 238 523 230Q521 222 529 224Q527 218 535 218Z"
              fill="#dfc678"
            />
            <text className="map-label" x="560" y="228" fill="#e6cf90">
              C-024
            </text>
            <text className="map-small" x="560" y="244" fill="#c2ad77">
              NO AIS
            </text>
          </g>
          {fleet.map((b) => {
            const old = frozen || (stale && b.id === "04");
            const selected = selection?.id === b.id;
            return (
              <g
                key={b.id}
                className="map-entity"
                role="button"
                tabIndex={0}
                aria-label={`Select USV-${b.id}${old ? ", last-known position" : ""}`}
                onClick={() => onSelect({ kind: "usv", id: b.id })}
                onKeyDown={(e) =>
                  mapKey(e, () => onSelect({ kind: "usv", id: b.id }))
                }
              >
                <circle
                  cx={b.x}
                  cy={b.y}
                  r="25"
                  fill={selected ? "#6aaaea18" : "transparent"}
                  stroke={selected ? "#89bfff" : "transparent"}
                />
                <circle
                  cx={b.x}
                  cy={b.y}
                  r="13"
                  fill="#142639"
                  stroke={old ? "#84929e" : "#76b5f3"}
                  strokeWidth="1.5"
                  strokeDasharray={old ? "3 3" : undefined}
                />
                <path
                  d={`M${b.x} ${b.y - 8}v-21`}
                  stroke={old ? "#84929e" : "#76b5f3"}
                  strokeWidth="2"
                  transform={`rotate(${b.heading} ${b.x} ${b.y})`}
                />
                <circle
                  cx={b.x}
                  cy={b.y}
                  r="4"
                  fill={old ? "#84929e" : "#8ec5fb"}
                />
                <text
                  x={b.x + 22}
                  y={b.y + 4}
                  className="map-label"
                  fill={old ? "#a5adb7" : "#acd1f7"}
                >
                  USV-{b.id}
                </text>
                {old && (
                  <text
                    x={b.x + 22}
                    y={b.y + 19}
                    className="map-small"
                    fill="#a5adb7"
                  >
                    LAST SEEN {frozen ? "14:32:18Z" : "00:42 AGO"}
                  </text>
                )}
              </g>
            );
          })}
          <rect x="739" y="562" width="10" height="10" fill="#a3afb6" />
          <text className="map-label" x="758" y="573" fill="#c4cbd0">
            KORSØR
          </text>
          <text className="map-small muted" x="758" y="590">
            SHORE STATION
          </text>
          {scenario === "truth" && (
            <g>
              <circle
                cx="484"
                cy="249"
                r="17"
                stroke="#bb9cf4"
                strokeDasharray="5 4"
                fill="#bb9cf418"
              />
              <path d="M475 240L493 258M493 240L475 258" stroke="#bb9cf4" />
              <text className="map-label" x="460" y="285" fill="#c4a9f4">
                TRUTH ONLY · synthetic target
              </text>
              <path
                d="M484 249L535 230"
                stroke="#bb9cf4"
                strokeDasharray="2 5"
              />
            </g>
          )}
        </g>
        <text className="grid-label" x="18" y="110">
          55° 27′ N
        </text>
        <text className="grid-label" x="18" y="700">
          55° 11′ N
        </text>
        <text className="grid-label" x="340" y="733">
          10° 56′ E
        </text>
        <text className="grid-label" x="730" y="733">
          11° 08′ E
        </text>
      </svg>
      <div className="absolute right-4 top-5 flex flex-col gap-2">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setZoom((z) => Math.min(1.8, z + 0.2))}
              disabled={zoom >= 1.8}
              aria-label="Zoom in"
            >
              <Plus />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Zoom in</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setZoom((z) => Math.max(0.8, z - 0.2))}
              disabled={zoom <= 0.8}
              aria-label="Zoom out"
            >
              <Minus />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Zoom out</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setZoom(1)}
              aria-label="Fit operating area"
            >
              <Crosshair />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Fit operating area</TooltipContent>
        </Tooltip>
        <Button
          variant="outline"
          size="icon"
          onClick={() => setLayers(true)}
          aria-label="Map layers"
        >
          <Layers3 />
        </Button>
      </div>
      <div className="absolute bottom-9 left-4 right-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setLinks(!links)}
            aria-pressed={links}
          >
            <Radio data-icon="inline-start" />
            Comms {links ? "on" : "off"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onPreview}
            aria-pressed={preview}
          >
            <Route data-icon="inline-start" />
            Route preview {preview ? "on" : "off"}
          </Button>
        </div>
        <Button variant="outline" size="sm" onClick={() => setLegend(true)}>
          <Layers3 data-icon="inline-start" />
          Legend
        </Button>
      </div>
      <Dialog open={layers} onOpenChange={setLayers}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Chart layers</DialogTitle>
            <DialogDescription>All chart assets are local.</DialogDescription>
          </DialogHeader>
          <FieldSet>
            <FieldLegend>Visible layers</FieldLegend>
            <FieldGroup>
              <Field orientation="horizontal">
                <Switch
                  id="layer-cables"
                  checked={cables}
                  onCheckedChange={setCables}
                />
                <FieldLabel htmlFor="layer-cables">
                  Cable infrastructure
                </FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch
                  id="layer-radio"
                  checked={links}
                  onCheckedChange={setLinks}
                />
                <FieldLabel htmlFor="layer-radio">Radio paths</FieldLabel>
              </Field>
            </FieldGroup>
            <FieldDescription>
              Satellite unavailable · no offline imagery supplied.
            </FieldDescription>
          </FieldSet>
        </DialogContent>
      </Dialog>
      <Dialog open={legend} onOpenChange={setLegend}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Operational symbology</DialogTitle>
            <DialogDescription>
              Application conventions. Not NATO symbology.
            </DialogDescription>
          </DialogHeader>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <dt>Blue circle + heading</dt>
            <dd>Friendly USV</dd>
            <dt>Green square</dt>
            <dd>AIS; yellow ring adds camera fusion</dd>
            <dt>Yellow quatrefoil</dt>
            <dd>Camera only · no AIS correlation</dd>
            <dt>Magenta / violet line</dt>
            <dd>Power / data cable</dd>
            <dt>Teal / yellow / orange</dt>
            <dd>Observed / due / overdue</dd>
            <dt>Gray dashed</dt>
            <dd>Unknown / unvisited</dd>
            <dt>Purple dashed overlay</dt>
            <dd>Evaluator truth only</dd>
          </dl>
        </DialogContent>
      </Dialog>
      <p className="absolute bottom-3 left-4 right-4 text-xs text-muted-foreground">
        © OpenStreetMap contributors · schematic, not for navigation
      </p>
    </section>
  );
}
