import type { FeatureCollection, Polygon, MultiPolygon } from "geojson";
import { Map, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { boxRing } from "../map/scene";
import type { SceneMsg, Snapshot } from "../types";
import type { CameraMap } from "./MarineScene";
import { xy } from "./feed";

export function MiniMap({
  snapshot,
  scene,
  land,
  selected,
  camera,
  onFollow,
  onOverview,
}: {
  snapshot: Snapshot | null;
  scene: SceneMsg | null;
  land: FeatureCollection | null;
  selected: number | string | null;
  camera: CameraMap | null;
  onFollow: (id: number | string) => void;
  onOverview: () => void;
}) {
  const width = 300,
    height = 205;
  const corners = boxRing.map((p) => xy(...p));
  const minX = Math.min(...corners.map((p) => p[0])) - 900,
    maxX = Math.max(...corners.map((p) => p[0])) + 900;
  const minY = Math.min(...corners.map((p) => p[1])) - 900,
    maxY = Math.max(...corners.map((p) => p[1])) + 900;
  const scale = Math.min(width / (maxX - minX), height / (maxY - minY));
  const project = ([x, y]: number[]) => [
    (width - (maxX - minX) * scale) / 2 + (x - minX) * scale,
    (height - (maxY - minY) * scale) / 2 + (maxY - y) * scale,
  ];
  const path = (ring: number[][]) =>
    ring
      .map(
        (point, i) =>
          `${i ? "L" : "M"}${project(xy(point[0], point[1])).join(",")}`,
      )
      .join(" ") + "Z";
  return (
    <section
      className="viewer-minimap overflow-hidden rounded-xl border bg-background/95 shadow-xl"
      aria-label="Live mission minimap"
    >
      <div className="flex items-center justify-between border-b px-3 py-2 text-sm">
        <span className="flex items-center gap-2 font-medium">
          <Map className="size-4" />
          Mission chart
        </span>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Fleet overview from minimap"
          onClick={onOverview}
        >
          <Maximize2 className="size-4" />
        </Button>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="block w-full bg-[#142b38]"
        role="img"
        aria-label="North-up map of cables, vessels and current camera"
      >
        <defs>
          <pattern
            id="sea-grid"
            width="30"
            height="30"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M30 0H0V30"
              fill="none"
              stroke="#45616b"
              strokeWidth=".4"
              opacity=".4"
            />
          </pattern>
        </defs>
        <rect width={width} height={height} fill="url(#sea-grid)" />
        {land?.features.flatMap((f, index) => {
          const g = f.geometry as Polygon | MultiPolygon;
          if (g.type !== "Polygon" && g.type !== "MultiPolygon") return [];
          return (g.type === "Polygon" ? [g.coordinates] : g.coordinates).map(
            (poly, i) => (
              <path
                key={`${index}-${i}`}
                d={poly.map(path).join(" ")}
                fill="#35463d"
                stroke="#768375"
                strokeWidth=".55"
                fillRule="evenodd"
              />
            ),
          );
        })}
        <path
          d={boxRing
            .map((p, i) => `${i ? "L" : "M"}${project(xy(...p)).join(",")}`)
            .join(" ")}
          fill="none"
          stroke="#c9d7d9"
          strokeDasharray="3 3"
          strokeWidth=".65"
          opacity=".55"
        />
        {scene &&
          Object.entries(scene.segments).map(([id, points]) => (
            <polyline
              key={id}
              points={points.map((p) => project(xy(...p)).join(",")).join(" ")}
              fill="none"
              stroke={id.startsWith("seg:H") ? "#d986c2" : "#a196d2"}
              strokeWidth="1.4"
            />
          ))}
        {scene && (
          <rect
            x={project(xy(...scene.shore))[0] - 2.5}
            y={project(xy(...scene.shore))[1] - 2.5}
            width="5"
            height="5"
            fill="#e9e8db"
          />
        )}
        {camera && (
          <line
            x1={project([camera.x, camera.y])[0]}
            y1={project([camera.x, camera.y])[1]}
            x2={project([camera.targetX, camera.targetY])[0]}
            y2={project([camera.targetX, camera.targetY])[1]}
            stroke="#a4dce4"
            strokeWidth=".8"
            opacity=".5"
          />
        )}
        {snapshot?.contacts.map((c) => {
          const [x, y] = project([c.x, c.y]);
          return (
            <g
              key={c.id}
              role="button"
              tabIndex={0}
              aria-label={`Follow contact ${c.track} on minimap`}
              onClick={() => onFollow(c.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onFollow(c.id);
                }
              }}
              className="cursor-pointer"
            >
              <rect
                x={x - 4}
                y={y - 4}
                width="8"
                height="8"
                fill="transparent"
              />
              <rect
                x={x - 1.4}
                y={y - 1.4}
                width="2.8"
                height="2.8"
                fill={c.ais ? "#a3cab2" : "#f4c77c"}
              />
              {selected === c.id && (
                <circle cx={x} cy={y} r="7" fill="none" stroke="#f4d2a4" />
              )}
            </g>
          );
        })}
        {snapshot?.boats.map((b) => {
          const [x, y] = project([b.x, b.y]);
          return (
            <g
              key={b.id}
              role="button"
              tabIndex={0}
              aria-label={`Follow USV ${String(b.id).padStart(2, "0")} on minimap`}
              onClick={() => onFollow(b.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onFollow(b.id);
                }
              }}
              className="cursor-pointer"
              transform={`translate(${x},${y})`}
            >
              <circle
                r={selected === b.id ? 9 : 6}
                fill={selected === b.id ? "#86dce6" : "#70b9ed"}
                opacity=".2"
              />
              <path
                d="M0 -5L3.7 4L0 2.5L-3.7 4Z"
                transform={`rotate(${b.hdg ?? 0})`}
                fill={
                  b.mode === "UNAVAILABLE"
                    ? "#8e999d"
                    : selected === b.id
                      ? "#b8f1ed"
                      : "#7ec7fc"
                }
                stroke="#101c25"
                strokeWidth=".6"
              />
              {selected === b.id && (
                <text x="7" y="4" fontSize="14" fill="#ecf0f0">
                  {String(b.id).padStart(2, "0")}
                </text>
              )}
            </g>
          );
        })}
        <text x="14" y="18" fill="#d2dde1" fontSize="14">
          N ↑
        </text>
      </svg>
      <div className="flex flex-wrap justify-between gap-1 border-t px-3 py-2 text-xs text-muted-foreground">
        <span>Great Belt · north up</span>
        <span>© OpenStreetMap</span>
      </div>
    </section>
  );
}
