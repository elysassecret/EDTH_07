// Live console in the shadcn presentation from web/template. No synthetic template model.
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  CircleAlert,
  Eye,
  Keyboard,
  Menu,
  Pause,
  Play,
  Settings2,
  Waves,
  WifiOff,
} from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
} from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  canOperate,
  coverageRows,
  pendingDecisions,
  staleBoat,
} from "./console-model";
import { dur, utc } from "./format";
import { Chart } from "./map/Chart";
import { useStore, type Display } from "./store";
import { OPERATOR_MODE, t0Of } from "./types";
import {
  DecisionReview,
  DecisionWorkspace,
  useDecisionFlow,
} from "./ui/LiveDecisions";
import {
  ContactOverview,
  CoveragePanel,
  EvaluatorWorkspace,
  EventTimeline,
  FleetOverview,
  SelectedContext,
} from "./ui/LivePanels";
import {
  ConnectionContext,
  DigestSummary,
  EvidenceTools,
  ExerciseTools,
  LiveAlerts,
} from "./ui/LiveTools";

export function App() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  const conn = useStore((s) => s.conn);
  const channel = useStore((s) => s.channel);
  const setChannel = useStore((s) => s.setChannel);
  const display = useStore((s) => s.display);
  const setDisplay = useStore((s) => s.setDisplay);
  const showComms = useStore((s) => s.showComms);
  const toggleComms = useStore((s) => s.toggleComms);
  const panel = useStore((s) => s.panel);
  const setPanel = useStore((s) => s.setPanel);
  const selected = useStore((s) => s.selected);
  const selectedContact = useStore((s) => s.selectedContact);
  const selectedSegment = useStore((s) => s.selectedSegment);
  const placing = useStore((s) => s.placing);
  const setPlacing = useStore((s) => s.setPlacing);
  const evalOn = useStore((s) => s.evalOn);
  const toggleEval = useStore((s) => s.toggleEval);
  const send = useStore((s) => s.send);
  const ack = useStore((s) => s.lastAck);
  const commandError = useStore((s) => s.commandError);
  const [satellite, setSatellite] = useState(false);
  const [satelliteState, setSatelliteState] = useState<
    "checking" | "none" | "ready"
  >("checking");
  const [tab, setTab] = useState("attention");
  const [drawer, setDrawer] = useState<"fleet" | "attention" | null>(null);
  const [wall, setWall] = useState(() => new Date());
  const flow = useDecisionFlow();
  const flowRef = useRef(flow);
  flowRef.current = flow;
  const onSatelliteState = useCallback(
    (state: "none" | "ready") => setSatelliteState(state),
    [],
  );

  useEffect(() => {
    const id = window.setInterval(() => setWall(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => {
    document.documentElement.dataset.display = display;
    document.documentElement.classList.toggle("dark", display !== "day");
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute("content", display === "day" ? "#fafafa" : "#0a0a0a");
  }, [display]);
  useEffect(() => {
    if (selected === null && !selectedContact && !selectedSegment) return;
    setTab("context");
    if (window.matchMedia("(max-width: 1279px)").matches)
      setDrawer("attention");
  }, [selected, selectedContact, selectedSegment]);
  useEffect(() => {
    if (conn !== "live") setPlacing(null);
  }, [conn, setPlacing]);
  useEffect(() => {
    if (!ack) return;
    if (!ack.ok) toast.error(ack.error ?? "Server rejected the command.");
    else if (ack.cmd === "inject")
      toast(
        ack.placed
          ? `Placed ${ack.placed} on ${ack.on}. Truth only until reported.`
          : "Server accepted the exercise injection.",
      );
    else if (ack.cmd === "reset") toast("Server accepted simulation reset.");
  }, [ack]);
  useEffect(() => {
    if (commandError) toast(commandError);
  }, [commandError]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.altKey || event.metaKey) return;
      const element = event.target as HTMLElement | null;
      if (
        element?.isContentEditable ||
        element?.closest(
          'input,textarea,select,[role="dialog"],[role="combobox"],[role="listbox"],[role="menu"]',
        )
      )
        return;
      const state = useStore.getState();
      if (event.key === "?") {
        event.preventDefault();
        state.setPanel("help");
      } else if (event.key === "Escape") {
        if (state.held) flowRef.current.undo();
        else {
          state.setPanel(null);
          state.setPlacing(null);
          state.select(null);
          setDrawer(null);
        }
      } else if (/^[1-9]$/.test(event.key)) {
        const id = Number(event.key);
        if (state.snap?.boats.some((boat) => boat.id === id)) {
          event.preventDefault();
          state.select(state.selected === id ? null : id);
        }
      } else if (
        event.key === " " &&
        !element?.closest('button,a,[role="button"],[role="tab"]') &&
        canOperate(state.conn, state.channel)
      ) {
        const rank = { alarm: 0, warning: 1, caution: 2 };
        const alert = state.snap?.alerts
          .filter((a) => !a.ack)
          .sort((a, b) => rank[a.level] - rank[b.level] || b.t - a.t)[0];
        if (alert) {
          event.preventDefault();
          state.send({ cmd: "ack", id: alert.id });
          state.setDigest(true);
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const open = pendingDecisions(snap);
  const rows = snap ? coverageRows(snap, scene) : [];
  const unknown = rows.filter((r) => r.age === null).length;
  const overdue = rows.filter(
    (r) =>
      r.age !== null &&
      scene?.revisit_target_s !== undefined &&
      r.age > scene.revisit_target_s,
  ).length;
  const fresh =
    snap?.boats.filter((boat) => !staleBoat(boat, snap, scene, conn)).length ??
    0;
  const latestExercise = snap?.events.filter((e) => e.exercise).at(-1);
  const source = snap?.source ?? scene?.source;
  const paused = snap?.speed === 0 || snap?.warp_mode === "paused";
  const speedValue =
    snap?.warp_mode === "auto" || !snap || paused ? "auto" : String(snap.speed);
  const speeds = [
    ...new Set([
      1,
      5,
      60,
      240,
      ...(snap && snap.speed > 0 ? [snap.speed] : []),
    ]),
  ].sort((a, b) => a - b);
  const attention = (
    <Tabs value={tab} onValueChange={setTab} className="min-w-0 gap-4">
      <TabsList className="w-full">
        <TabsTrigger value="attention">
          Attention<Badge variant="secondary">{open.length}</Badge>
        </TabsTrigger>
        <TabsTrigger value="context">Selected</TabsTrigger>
      </TabsList>
      <TabsContent value="attention" className="space-y-4">
        <DecisionWorkspace flow={flow} />
        <LiveAlerts />
        <CoveragePanel />
        <ContactOverview />
        <EvaluatorWorkspace />
      </TabsContent>
      <TabsContent value="context" className="space-y-4">
        <SelectedContext />
        <ConnectionContext />
        <Button variant="ghost" onClick={() => setTab("attention")}>
          Return to attention · keep selection
        </Button>
      </TabsContent>
    </Tabs>
  );

  return (
    <TooltipProvider>
      <div
        className="console-shell flex h-dvh min-h-0 flex-col overflow-hidden bg-background text-foreground"
        data-display={display}
      >
        <a
          href="#main"
          className="sr-only z-50 bg-background p-3 focus:not-sr-only focus:absolute"
        >
          Skip to operational chart
        </a>
        <header className="console-header flex shrink-0 flex-wrap items-center gap-3 border-b px-4 pb-3">
          <a
            href="#main"
            className="flex shrink-0 items-center gap-2 font-semibold"
          >
            <Waves className="size-5" />
            EDTH_07
          </a>
          <Separator orientation="vertical" className="hidden h-7 lg:block" />
          <span className="hidden text-sm text-muted-foreground min-[1400px]:block">
            Great Belt · cable watch
          </span>
          <div className="ml-auto flex flex-wrap items-center justify-end gap-2 md:gap-4">
            <div className="hidden min-[1500px]:block">
              <p className="text-xs text-muted-foreground">Wall UTC</p>
              <time>{wall.toISOString().slice(11, 19)}Z</time>
            </div>
            <div className="hidden sm:block">
              <p className="text-xs text-muted-foreground">
                Scenario UTC · simulation
              </p>
              <time>{snap ? utc(t0Of(snap), snap.t) : "Waiting for feed"}</time>
            </div>
            <Button
              variant="outline"
              size="icon"
              disabled={conn !== "live"}
              aria-label={paused ? "Resume simulation" : "Pause simulation"}
              onClick={() => send({ cmd: "pause", on: !paused })}
            >
              {paused ? <Play /> : <Pause />}
            </Button>
            <Select
              value={speedValue}
              disabled={conn !== "live"}
              onValueChange={(value) =>
                send({
                  cmd: "speed",
                  value: value === "auto" ? "auto" : Number(value),
                })
              }
            >
              <SelectTrigger
                aria-label="Simulation speed"
                size="sm"
                className="hidden w-24 md:flex"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="auto">Auto</SelectItem>
                  {speeds.map((speed) => (
                    <SelectItem key={speed} value={String(speed)}>
                      {speed}×
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            {!OPERATOR_MODE && (
              <ToggleGroup
                type="single"
                variant="outline"
                size="sm"
                value={channel}
                onValueChange={(value) => {
                  if (value === "shore" || value === "truth") setChannel(value);
                }}
                aria-label="Observation view"
              >
                <ToggleGroupItem value="shore" aria-label="SHORE">
                  SHORE
                </ToggleGroupItem>
                <ToggleGroupItem value="truth" aria-label="TRUTH">
                  TRUTH
                </ToggleGroupItem>
              </ToggleGroup>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPanel("inject")}
              aria-label="Exercise controls"
            >
              <Settings2 />
              <span className="hidden lg:inline">Exercise</span>
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setPanel("menu")}
              aria-label="View settings"
            >
              <Menu />
            </Button>
            <Badge variant={conn === "lost" ? "destructive" : "outline"}>
              {conn === "live"
                ? source === "mock"
                  ? "MOCK FEED"
                  : "FEED LIVE"
                : conn === "lost"
                  ? "FEED LOST"
                  : "CONNECTING"}
            </Badge>
          </div>
        </header>
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b px-4 py-2 text-sm text-muted-foreground">
          <span>
            {source === "sim"
              ? "Simulation · modeled boats, sensors and radio"
              : source === "mock"
                ? "MOCK FEED · synthetic demonstration snapshots"
                : "Waiting for source identification"}{" "}
            ·{" "}
            {channel === "shore"
              ? "delivered shore picture"
              : "evaluator truth"}
          </span>
          <span>
            {snap
              ? `T+${dur(snap.t)} · ${paused ? "PAUSED" : `${snap.speed}× ${snap.warp_mode ?? "server"}`}${snap.near_event && snap.warp_mode === "auto" ? " · slowing for event" : ""}`
              : "No observations received"}
          </span>
        </div>
        {conn !== "live" && (
          <Alert
            variant={conn === "lost" ? "destructive" : "default"}
            className="shrink-0 rounded-none border-x-0 border-t-0"
          >
            <WifiOff />
            <AlertTitle>
              {conn === "lost" ? "FEED LOST" : "CONNECTING"} —{" "}
              {snap
                ? `display frozen at ${utc(t0Of(snap), snap.t)}`
                : "no data received"}
            </AlertTitle>
            <AlertDescription>
              Last-known positions only. Commands disabled; queued unsent
              answers are cancelled. Reconnecting automatically.
            </AlertDescription>
          </Alert>
        )}
        {(channel === "truth" || evalOn) && (
          <Alert className="shrink-0 rounded-none border-x-0 border-t-0">
            <Eye />
            <AlertTitle>
              {channel === "truth"
                ? "TRUTH VIEW — evaluator only"
                : "EVALUATOR COMPARISON ENABLED"}
            </AlertTitle>
            <AlertDescription>
              {channel === "truth"
                ? "Not the shore picture. Operator decisions are disabled."
                : "Purple map annotations come from the separate /truth channel, not delivered shore observations."}
            </AlertDescription>
          </Alert>
        )}
        {latestExercise && (
          <Alert className="shrink-0 rounded-none border-x-0 border-t-0 py-2">
            <Settings2 />
            <AlertTitle>
              EXERCISE — injected or scripted simulation condition
            </AlertTitle>
            <AlertDescription className="text-sm">
              {utc(t0Of(snap), latestExercise.t)} ·{" "}
              {latestExercise.text.replace(/^EXERCISE: /, "")}
            </AlertDescription>
          </Alert>
        )}
        {placing && (
          <Alert className="shrink-0 rounded-none border-x-0 border-t-0">
            <CircleAlert />
            <AlertTitle>
              Click the chart to place a synthetic contact
            </AlertTitle>
            <AlertDescription>
              Truth only until a boat reports it.{" "}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPlacing(null)}
              >
                Cancel placement
              </Button>
            </AlertDescription>
          </Alert>
        )}
        <DigestSummary />
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b px-4 py-2 text-sm">
          <div className="flex flex-wrap gap-3">
            <span>
              {snap
                ? `${fresh}/${snap.boats.length} ${channel === "shore" ? "reports" : "truth states"} current`
                : "Waiting for fleet picture"}
            </span>
            <span className="text-muted-foreground">
              {!snap || !scene
                ? "Coverage picture not yet available"
                : `Coverage: ${unknown} unknown · ${scene.revisit_target_s === undefined ? "target not supplied" : `${overdue} over target`}`}
            </span>
          </div>
          <Badge variant="secondary">
            {open.length} pending decision{open.length === 1 ? "" : "s"}
          </Badge>
        </div>
        <div className="flex shrink-0 justify-between gap-2 border-b p-2 xl:hidden">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDrawer("fleet")}
          >
            <ShipIcon />
            Fleet · {snap?.boats.length ?? 0}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDrawer("attention")}
          >
            Attention · {open.length}
          </Button>
        </div>
        <main
          id="main"
          className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[260px_minmax(0,1fr)_352px]"
          tabIndex={-1}
        >
          <aside
            className="hidden min-h-0 flex-col gap-3 overflow-y-auto overscroll-contain border-r p-2 xl:flex"
            aria-label="Fleet overview"
          >
            <div className="flex items-center justify-between p-1">
              <h2 className="font-semibold">Fleet overview</h2>
              <Badge variant="outline">{snap?.boats.length ?? 0}</Badge>
            </div>
            <FleetOverview />
          </aside>
          <section
            className="relative isolate min-h-0 min-w-0 overflow-hidden bg-[#16222d]"
            aria-label="Operational chart"
          >
            <Chart satellite={satellite} onSatelliteState={onSatelliteState} />
          </section>
          <aside
            className="hidden min-h-0 flex-col gap-3 overflow-y-auto overscroll-contain border-l p-3 xl:flex"
            aria-label="Operator attention workspace"
          >
            <h2 className="py-1 font-semibold">Operator attention</h2>
            {attention}
          </aside>
        </main>
        <EventTimeline />
        <footer className="console-footer flex shrink-0 items-center justify-between gap-2 border-t px-4 pt-2 text-sm text-muted-foreground">
          <span>
            Korsør shore station ·{" "}
            {channel === "shore" ? "received reports" : "evaluator truth"}
          </span>
          <Button variant="ghost" size="sm" onClick={() => setPanel("help")}>
            <Keyboard />
            Help
          </Button>
        </footer>
        <Sheet
          open={drawer !== null}
          onOpenChange={(open) => {
            if (!open) setDrawer(null);
          }}
        >
          <SheetContent
            side={drawer === "fleet" ? "left" : "right"}
            className="overflow-y-auto overscroll-contain pb-[max(1rem,env(safe-area-inset-bottom))]"
          >
            <SheetHeader>
              <SheetTitle>
                {drawer === "fleet" ? "Fleet overview" : "Operator attention"}
              </SheetTitle>
              <SheetDescription>
                {channel === "shore"
                  ? "Delivered observations only"
                  : "Evaluator truth"}{" "}
                · {conn === "live" ? "feed connected" : "last-known picture"}
              </SheetDescription>
            </SheetHeader>
            <div className="px-4 pb-4">
              {drawer === "fleet" ? <FleetOverview /> : attention}
            </div>
          </SheetContent>
        </Sheet>
        <DecisionReview flow={flow} />
        <ExerciseTools
          open={panel === "inject"}
          onOpenChange={(open) => {
            if (!open) setPanel(null);
          }}
        />
        <EvidenceTools
          open={panel === "evidence"}
          onOpenChange={(open) => {
            if (!open) setPanel(null);
          }}
        />
        <Dialog
          open={panel === "menu"}
          onOpenChange={(open) => {
            if (!open) setPanel(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>View settings</DialogTitle>
              <DialogDescription>
                Display preferences do not change the mission or invent
                observations.
              </DialogDescription>
            </DialogHeader>
            <FieldGroup>
              <Field orientation="horizontal">
                <Switch
                  id="comms-visible"
                  checked={showComms}
                  onCheckedChange={toggleComms}
                />
                <FieldLabel htmlFor="comms-visible">
                  Communications overlay
                </FieldLabel>
              </Field>
              <Field orientation="horizontal">
                <Switch
                  id="satellite-visible"
                  checked={satellite}
                  onCheckedChange={setSatellite}
                  disabled={satelliteState !== "ready"}
                />
                <FieldLabel htmlFor="satellite-visible">
                  Satellite layer
                </FieldLabel>
                <FieldDescription>
                  {satelliteState === "ready"
                    ? "Local image supplied."
                    : satelliteState === "checking"
                      ? "Checking local image…"
                      : "No satellite image supplied."}
                </FieldDescription>
              </Field>
              <Field>
                <FieldLabel>Display</FieldLabel>
                <Select
                  value={display}
                  onValueChange={(value) => setDisplay(value as Display)}
                >
                  <SelectTrigger aria-label="Display mode">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {["day", "dusk", "night"].map((value) => (
                        <SelectItem key={value} value={value}>
                          {value.toUpperCase()}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
              {!OPERATOR_MODE && (
                <Field orientation="horizontal">
                  <Switch
                    id="evaluator-visible"
                    checked={evalOn}
                    onCheckedChange={toggleEval}
                  />
                  <FieldLabel htmlFor="evaluator-visible">
                    Evaluator comparison · truth-only annotations
                  </FieldLabel>
                </Field>
              )}
              <Separator />
              <Button variant="outline" onClick={() => setPanel("evidence")}>
                Evidence and incident reports
              </Button>
              <Button
                variant="outline"
                onClick={() => useStore.getState().setDigest(true)}
              >
                Since you last looked
              </Button>
            </FieldGroup>
          </DialogContent>
        </Dialog>
        <Dialog
          open={panel === "help"}
          onOpenChange={(open) => {
            if (!open) setPanel(null);
          }}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Watch guide & keyboard</DialogTitle>
              <DialogDescription>
                Supervise the swarm. Approve decisions, not steering commands.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 text-sm">
              <p>
                Tab moves focus. Enter/Space activates controls. Focus a
                decision card itself: A/D reviews held actions, C/S reviews
                delegated actions. Shortcuts open review; they never submit
                directly.
              </p>
              <p>
                1–9 selects an available USV. Space outside a control
                acknowledges the top alert. Esc undoes a queued answer;
                otherwise it cancels placement or selection. ? opens this guide.
              </p>
              <p>
                Review requires a fresh shore feed and an unchanged task record.
                Approve, Decline and Stop have a five-second local undo window.
                Server acceptance is not boat delivery, and delivery is not task
                completion.
              </p>
              <p>
                Coverage updates only from observations. Alert acknowledgment
                does not clear the condition. Stale reports remain last-known;
                evaluator truth is explicitly separated.
              </p>
              <p>
                All boats/radio are modeled. Camera imagery is not supplied;
                satellite may be absent. No scenario fixture, fake identity or
                template command result is used in this live interface.
              </p>
            </div>
          </DialogContent>
        </Dialog>
        <Toaster theme={display === "day" ? "light" : "dark"} closeButton />
      </div>
    </TooltipProvider>
  );
}

function ShipIcon() {
  return <Activity className="size-4" />;
}
