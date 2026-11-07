import { useEffect, useRef, useState } from "react";
import {
  Anchor,
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
  Eye,
  Focus,
  Info,
  Layers,
  Maximize2,
  Pause,
  Play,
  RotateCcw,
  Settings2,
  Ship,
  Sun,
  Waves,
  WifiOff,
} from "lucide-react";
import type { FeatureCollection } from "geojson";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { dur, utc } from "../format";
import { t0Of } from "../types";
import { MarineScene, type CameraMap } from "./MarineScene";
import { MiniMap } from "./MiniMap";
import { useViewerFeed, viewerFeedUrl } from "./feed";
import { vesselLifecycle } from "./lifecycle";

export function ViewerApp() {
  const feed = useViewerFeed();
  const { snapshot, scene, status } = feed;
  const host = useRef<HTMLDivElement>(null);
  const header = useRef<HTMLElement>(null);
  const engine = useRef<MarineScene | null>(null);
  const [selected, setSelected] = useState<number | string | null>(2);
  const [fleetOpen, setFleetOpen] = useState(() => innerWidth > 760);
  const [traffic, setTraffic] = useState(false);
  const [cables, setCables] = useState(false);
  const [settings, setSettings] = useState(false);
  const [reset, setReset] = useState(false);
  const [waves, setWaves] = useState(
    () => !matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [dusk, setDusk] = useState(false);
  const [links, setLinks] = useState(false);
  const [markers, setMarkers] = useState(true);
  const [scale, setScale] = useState(true);
  const [land, setLand] = useState<FeatureCollection | null>(null);
  const [camera, setCamera] = useState<CameraMap | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [glError, setGlError] = useState<string | null>(null);
  useEffect(() => {
    const node = header.current;
    if (!node) return;
    const measure = () => node.parentElement?.style.setProperty(
      "--viewer-header-bottom", `${node.offsetTop + node.offsetHeight}px`,
    );
    const observer = new ResizeObserver(measure);
    observer.observe(node);
    measure();
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    document.documentElement.classList.add("dark");
    document.documentElement.dataset.display = "dusk";
    try {
      engine.current = new MarineScene(
        host.current!,
        setSelected,
        setCamera,
        setLand,
        setWarning,
      );
    } catch (error) {
      setGlError(error instanceof Error ? error.message : "WebGL2 unavailable");
    }
    return () => {
      engine.current?.dispose();
    };
  }, []);
  useEffect(() => {
    if (snapshot) {
      engine.current?.setFrame(snapshot);
      if (
        selected !== null &&
        !snapshot.boats.some((b) => b.id === selected) &&
        !snapshot.contacts.some((c) => c.id === selected)
      )
        setSelected(null);
    }
  }, [snapshot, selected]);
  useEffect(() => {
    if (scene) engine.current?.setScene(scene);
  }, [scene]);
  useEffect(() => {
    engine.current?.setOptions({
      followed: selected,
      waves,
      dusk,
      links,
      markers,
      overviewScale: scale,
      live: status === "live",
      cables,
    });
  }, [selected, waves, dusk, links, markers, scale, status, cables]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (
        event.ctrlKey ||
        event.metaKey ||
        event.altKey ||
        (event.target as HTMLElement).closest(
          'input,select,textarea,[role="dialog"],[role="combobox"]',
        )
      )
        return;
      if (event.key.toLowerCase() === "o") setSelected(null);
      else if (
        /^[1-9]$/.test(event.key) &&
        snapshot?.boats.some((b) => b.id === Number(event.key))
      )
        setSelected(Number(event.key));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [snapshot]);
  const boat = snapshot?.boats.find((b) => b.id === selected);
  const lifecycle = boat && snapshot ? vesselLifecycle(boat, snapshot) : null;
  const contact = snapshot?.contacts.find((c) => c.id === selected);
  const paused = snapshot?.speed === 0 || snapshot?.warp_mode === "paused";
  const ended = !!snapshot && !!scene && snapshot.t >= scene.horizon_s;
  const dashboard = new URL(viewerFeedUrl());
  dashboard.protocol = dashboard.protocol === "wss:" ? "https:" : "http:";
  dashboard.pathname = "/";
  return (
    <TooltipProvider>
      <main className="viewer-shell relative h-dvh overflow-hidden bg-background text-foreground">
        <div
          ref={host}
          className="absolute inset-0"
          data-testid="maritime-webgl"
        />
        <header ref={header} className="viewer-header absolute inset-x-4 top-4 z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-background/95 px-4 py-3 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg border bg-card">
              <Waves className="size-5" />
            </div>
            <div>
              <h1 className="text-sm font-semibold">
                Great Belt{" "}
                <span className="font-normal text-muted-foreground">
                  / Maritime 3D
                </span>
              </h1>
              <p className="text-xs text-muted-foreground">
                {snapshot?.launch
                  ? <>Shore launch from Korsør<span className="hidden sm:inline"> · boats choose their assignments</span></>
                  : "Same simulation. A different perspective."}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="hidden text-right text-sm sm:block">
              <time>
                {snapshot
                  ? utc(t0Of(snapshot), snapshot.t)
                  : "Waiting for feed"}
              </time>
              <p className="text-xs text-muted-foreground">
                {snapshot
                  ? `T+${dur(snapshot.t)} · ${ended ? "END OF RUN" : paused ? "PAUSED" : `${snapshot.speed}×`}`
                  : "No observations yet"}
              </p>
            </div>
            <Badge variant={status === "lost" ? "destructive" : "outline"}>
              <span
                className={`mr-1.5 inline-block size-1.5 rounded-full ${status === "live" ? "bg-emerald-300" : "bg-muted-foreground"}`}
              />
              {status === "live"
                ? snapshot?.source === "mock"
                  ? "MOCK"
                  : "LIVE SIM"
                : status === "lost"
                  ? "FEED LOST"
                  : "CONNECTING"}
            </Badge>
            <Button
              variant="outline"
              size="sm"
              disabled={status !== "live"}
              aria-label={
                paused ? "Resume shared simulation" : "Pause shared simulation"
              }
              onClick={() => feed.command({ cmd: "pause", on: !paused })}
            >
              {paused ? <Play /> : <Pause />}
              <span className="hidden md:inline">
                {paused ? "Run" : "Pause"}
              </span>
            </Button>
            <Button
              variant="outline"
              size="icon"
              aria-label="Scene settings"
              onClick={() => setSettings(true)}
            >
              <Settings2 />
            </Button>
            <Button variant="ghost" size="icon" asChild>
              <a
                href={dashboard.toString()}
                target="_blank"
                rel="noreferrer"
                aria-label="Open main dashboard"
              >
                <ArrowUpRight />
              </a>
            </Button>
          </div>
        </header>

        <aside
          className="viewer-fleet absolute left-4 top-28 z-10 w-64 max-w-[calc(100%_-_2rem)]"
          aria-label="Fleet camera controls"
        >
          <Card className="gap-0 overflow-hidden bg-background/95 py-0 shadow-xl">
            <CardHeader className="px-4 py-3">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Ship className="size-4" />
                  {traffic ? "Traffic" : "Fleet"}{" "}
                  <Badge variant="secondary">
                    {traffic
                      ? (snapshot?.contacts.length ?? "—")
                      : (snapshot?.boats.length ?? "—")}
                  </Badge>
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={traffic ? "Show fleet" : "Show maritime traffic"}
                  onClick={() => setTraffic(!traffic)}
                >
                  <Anchor className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={fleetOpen ? "Collapse fleet" : "Expand fleet"}
                  aria-expanded={fleetOpen}
                  onClick={() => setFleetOpen(!fleetOpen)}
                >
                  {fleetOpen ? <ChevronUp /> : <ChevronDown />}
                </Button>
              </div>
            </CardHeader>
            {fleetOpen && (
              <CardContent className="max-h-[min(52dvh,30rem)] space-y-1 overflow-y-auto overscroll-contain px-2 pb-2">
                <Button
                  variant={selected === null ? "secondary" : "ghost"}
                  className="w-full justify-start"
                  onClick={() => setSelected(null)}
                >
                  <Maximize2 className="size-4" />
                  Mission overview{" "}
                  <kbd className="ml-auto text-xs text-muted-foreground">O</kbd>
                </Button>
                {!snapshot && (
                  <p className="p-3 text-sm text-muted-foreground">
                    Waiting for the dashboard simulation…
                  </p>
                )}
                {!traffic &&
                  snapshot?.boats.map((b) => (
                    <Button
                      key={b.id}
                      variant={selected === b.id ? "secondary" : "ghost"}
                      className="h-auto w-full items-start justify-between gap-2 py-3 text-left"
                      aria-pressed={selected === b.id}
                      aria-label={`Follow USV ${String(b.id).padStart(2, "0")}`}
                      onClick={() => setSelected(b.id)}
                    >
                      <span className="flex items-center gap-2">
                        <span
                          className={`mt-1 size-2 rounded-full ${b.mode === "UNAVAILABLE" ? "bg-muted-foreground" : "bg-sky-300"}`}
                        />
                        <span>
                          USV {String(b.id).padStart(2, "0")}
                          <span className="mt-1 block text-xs font-normal text-muted-foreground">
                            {vesselLifecycle(b, snapshot).label}
                          </span>
                        </span>
                      </span>
                      <span className="text-xs tabular-nums text-muted-foreground">
                        {Math.round(b.batt / 10)}%
                      </span>
                    </Button>
                  ))}
                {traffic &&
                  snapshot?.contacts.map((c) => (
                    <Button
                      key={c.id}
                      variant={selected === c.id ? "secondary" : "ghost"}
                      className="h-auto w-full justify-between gap-2 py-3 text-left"
                      aria-label={`Follow contact ${c.track}`}
                      onClick={() => setSelected(c.id)}
                    >
                      <span className="truncate">{c.name ?? c.track}</span>
                      <Badge variant="outline">
                        {c.ais ? "AIS" : "NO AIS"}
                      </Badge>
                    </Button>
                  ))}
              </CardContent>
            )}
          </Card>
          {boat && fleetOpen && (
            <Card className="mt-3 gap-2 bg-background/95 py-4 shadow-xl">
              <CardHeader className="px-4">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <Focus className="size-4" />
                  Following USV {String(boat.id).padStart(2, "0")}
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-3 px-4 text-sm">
                {lifecycle && (
                  <div className="col-span-2 flex flex-col gap-1" data-testid="vessel-lifecycle">
                    <Badge variant="outline">{lifecycle.label}</Badge>
                    {lifecycle.detail && (
                      <p className="text-xs text-muted-foreground">{lifecycle.detail}</p>
                    )}
                    {status !== "live" && (
                      <p className="text-xs text-muted-foreground">Last received state · feed unavailable</p>
                    )}
                  </div>
                )}
                <div>
                  <p className="text-xs text-muted-foreground">Ground speed</p>
                  <p>
                    {boat.sog === undefined
                      ? "Not reported"
                      : `${((boat.sog / 1000) * 1.94384).toFixed(1)} kn`}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Course</p>
                  <p>
                    {boat.hdg === undefined
                      ? "Not reported"
                      : `${String(Math.round(boat.hdg)).padStart(3, "0")}°`}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </aside>

        <div className="viewer-caption pointer-events-none absolute bottom-24 left-5 z-10 text-white drop-shadow-md">
          <p className="mb-1 text-xs uppercase tracking-[.18em] text-white/70">
            {selected === null
              ? "The operating environment"
              : "Vessel perspective"}
          </p>
          <h2 className="text-2xl font-medium tracking-tight sm:text-3xl">
            {boat
              ? `USV ${String(boat.id).padStart(2, "0")}`
              : contact
                ? (contact.name ?? contact.track)
                : selected === null
                  ? "Great Belt, Denmark"
                  : "Connecting to the fleet"}
          </h2>
          <p className="mt-2 text-sm text-white/80">
            {selected === null
              ? "Coastline, infrastructure and live maritime traffic."
              : "Drag to orbit · Scroll to approach · Select any vessel to follow"}
          </p>
        </div>
        <div
          className="viewer-toolbar absolute bottom-5 left-4 z-10 flex items-center gap-1 rounded-xl border bg-background/95 p-2 shadow-xl"
          aria-label="View controls"
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={selected === null ? "secondary" : "ghost"}
                size="icon"
                aria-label="Mission overview"
                onClick={() => setSelected(null)}
              >
                <Maximize2 />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Mission overview · O</TooltipContent>
          </Tooltip>
          <Separator orientation="vertical" className="mx-1 h-6" />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={links ? "secondary" : "ghost"}
                size="icon"
                aria-label="Toggle physical radio links"
                aria-pressed={links}
                onClick={() => setLinks(!links)}
              >
                <Layers />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              Physical radio links · evaluator truth
            </TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={dusk ? "secondary" : "ghost"}
                size="icon"
                aria-label="Toggle sunset lighting"
                aria-pressed={dusk}
                onClick={() => setDusk(!dusk)}
              >
                <Sun />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Visual daylight / sunset</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Reset shared simulation"
                disabled={status !== "live"}
                onClick={() => setReset(true)}
              >
                <RotateCcw />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Review shared simulation reset</TooltipContent>
          </Tooltip>
          <Separator orientation="vertical" className="mx-1 h-6" />
          <span className="flex items-center gap-1.5 px-2 text-xs text-muted-foreground">
            <Eye className="size-3.5" />
            Evaluator truth
          </span>
        </div>
        <div className="viewer-map-dock absolute bottom-4 right-4 z-10">
          <MiniMap
            snapshot={snapshot}
            scene={scene}
            land={land}
            selected={selected}
            camera={camera}
            onFollow={setSelected}
            onOverview={() => setSelected(null)}
          />
        </div>
        {(status === "lost" || glError || feed.error) && (
          <div
            role="alert"
            className="absolute left-1/2 top-28 z-20 w-[min(30rem,calc(100%_-_2rem))] -translate-x-1/2 rounded-xl border bg-background p-4 shadow-xl"
          >
            <div className="mb-1 flex items-center gap-2 font-medium">
              <WifiOff className="size-4" />
              {glError
                ? "3D renderer unavailable"
                : status === "lost"
                  ? "Feed lost · view frozen"
                  : "Command not sent"}
            </div>
            <p className="text-sm text-muted-foreground">
              {glError ??
                feed.error ??
                "Last-known positions only. Reconnecting to the same simulator automatically."}
            </p>
          </div>
        )}
        <Dialog open={settings} onOpenChange={setSettings}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Scene settings</DialogTitle>
              <DialogDescription>
                Rendering preferences only. Motion and state come from the same
                simulation as the dashboard.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-5">
              {[
                ["Visual wave motion", waves, setWaves],
                ["Physical radio links", links, setLinks],
                ["Cable display overlay", cables, setCables],
                ["Overview vessel markers", markers, setMarkers],
                ["Exaggerate offshore USVs", scale, setScale],
              ].map(([label, on, toggle]) => (
                <div
                  key={String(label)}
                  className="flex items-center justify-between gap-3"
                >
                  <label htmlFor={String(label)} className="text-sm">
                    {String(label)}
                  </label>
                  <Switch
                    id={String(label)}
                    checked={Boolean(on)}
                    onCheckedChange={toggle as (v: boolean) => void}
                  />
                </div>
              ))}
              <div className="flex items-center justify-between">
                <span className="text-sm">Lighting</span>
                <Select
                  value={dusk ? "sunset" : "daylight"}
                  onValueChange={(v) => setDusk(v === "sunset")}
                >
                  <SelectTrigger className="w-36" aria-label="Visual lighting">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daylight">Daylight</SelectItem>
                    <SelectItem value="sunset">Sunset</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Separator />
              <p className="flex gap-2 text-sm text-muted-foreground">
                <Info className="size-4 shrink-0" />
                Vessel models, pontoons and terrain heights are schematic proxies,
                not surveyed harbour infrastructure. Sea motion is decorative, not
                measured wave or hull physics. USVs remain life-sized near the
                harbour; offshore enlargement is limited by coastline and vessel
                clearance. Display motion blends received samples only and snaps
                across unsafe coastal chords; it never predicts future positions. Coastline © OpenStreetMap contributors. Optional
                local terrain imagery contains modified Copernicus Sentinel
                data.
              </p>
              {warning && (
                <p className="text-sm text-muted-foreground">{warning}</p>
              )}
            </div>
          </DialogContent>
        </Dialog>
        <Dialog open={reset} onOpenChange={setReset}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Start a new shared run?</DialogTitle>
              <DialogDescription>
                This resets the simulation in the main dashboard too. Current
                injections and progress are discarded; run logs remain on the
                server.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setReset(false)}>
                Keep this run
              </Button>
              <Button
                disabled={status !== "live"}
                onClick={() => {
                  feed.command({ cmd: "reset", seed: snapshot?.seed ?? 1 });
                  setReset(false);
                }}
              >
                Reset shared run
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </TooltipProvider>
  );
}
