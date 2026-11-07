import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  Check,
  CheckCheck,
  CircleAlert,
  Eye,
  Keyboard,
  Menu,
  Pause,
  Play,
  Radio,
  Settings2,
  Ship,
  TriangleAlert,
  Unplug,
  Waves,
  WifiOff,
} from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
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
import { Toaster } from "@/components/ui/sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { TooltipProvider } from "@/components/ui/tooltip";
import { OperationalMap } from "./OperationalMap";
import {
  canSubmit,
  fleet,
  initialEvents,
  isLocked,
  scenarios,
  type CommandState,
  type Scenario,
  type Selection,
} from "./model";

export function App() {
  const [scenario, setScenario] = useState<Scenario>("monitoring");
  const [selection, setSelection] = useState<Selection>(null);
  const [command, setCommand] = useState<CommandState>("idle");
  const [preview, setPreview] = useState(false);
  const [scenarioOpen, setScenarioOpen] = useState(false);
  const [exerciseOpen, setExerciseOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [confirm, setConfirm] = useState<"approve" | "decline" | "stop" | null>(
    null,
  );
  const [outcome, setOutcome] = useState<
    "accepted" | "rejected" | "unconfirmed"
  >("accepted");
  const [submittedAction, setSubmittedAction] = useState<"approve" | "stop">(
    "approve",
  );
  const [acknowledged, setAcknowledged] = useState(false);
  const [gapClosed, setGapClosed] = useState(false);
  const [revision, setRevision] = useState(3);
  const [events, setEvents] = useState(initialEvents);
  const [eventFilter, setEventFilter] = useState("All events");
  const [timelineOpen, setTimelineOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("attention");
  const [drawer, setDrawer] = useState<"fleet" | "attention" | null>(null);
  const [wall, setWall] = useState(() => new Date());
  const [sim, setSim] = useState(0);
  const [speed, setSpeed] = useState("1×");
  const [paused, setPaused] = useState(false);
  const [freezeAge, setFreezeAge] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const commandRef = useRef(command);
  commandRef.current = command;
  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;
  const returnFocus = useRef<HTMLElement | null>(null);
  const frozen = scenario === "lost" || scenario === "recovery";
  const locked = isLocked(scenario);
  const gap = scenario === "gap" && !gapClosed;
  const degraded = scenario === "stale" || scenario === "exercise";
  const delegated = scenario === "exercise";
  const contact = scenario === "contact";
  const outstanding = ["idle", "review", "rejected"].includes(command);
  const selectedBoat =
    selection?.kind === "usv" ? fleet.find((b) => b.id === selection.id) : null;
  const title = contact
    ? "Request a closer observation"
    : delegated
      ? "Retain relay coverage"
      : gap
        ? "Revisit cable segment P-04"
        : "Adjust USV-03 patrol route";
  const rationale = contact
    ? "USV-02 reports a camera-only contact near the cable. Additional observation may clarify course and identity."
    : delegated
      ? "The exercise interrupts USV-04’s direct link. Retain USV-03’s relay task while the link is unavailable."
      : gap
        ? "P-04 exceeds the 15-minute revisit target. USV-03 can re-observe the overdue segment."
        : "Shift the south patrol leg east to revisit P-04. USV-02 retains the north sector.";

  function log(
    text: string,
    source = "OPERATOR",
    category = "Command",
    ref = "03",
  ) {
    setEvents((previous) =>
      [{ time: "14:32:18", source, category, text, ref }, ...previous].slice(
        0,
        50,
      ),
    );
  }
  function changeScenario(next: Scenario) {
    if (timer.current) clearTimeout(timer.current);
    const interrupted = commandRef.current === "pending";
    setScenario(next);
    setCommand(interrupted ? "unconfirmed" : "idle");
    setRevision(3);
    setFreezeAge(0);
    setGapClosed(false);
    setAcknowledged(false);
    setConfirm(null);
    setSubmittedAction("approve");
    setScenarioOpen(false);
    setActiveTab("attention");
    setSelection(
      next === "contact"
        ? { kind: "contact", id: "C-024" }
        : next === "stale" || next === "exercise"
          ? { kind: "usv", id: "04" }
          : next === "gap"
            ? { kind: "segment", id: "P-04" }
            : null,
    );
    setPreview(next === "decision" || next === "gap");
    log(
      `Demo scenario: ${scenarios.find((s) => s.id === next)?.label}${interrupted ? " · command delivery UNCONFIRMED" : ""}`,
      "DEMO",
      "Scenario",
    );
  }
  function select(next: Selection) {
    setSelection(next);
    setActiveTab("context");
    if (window.innerWidth < 1280) setDrawer("attention");
  }
  function review(action: "approve" | "decline" | "stop") {
    if (!canSubmit(scenario, command)) return;
    returnFocus.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setConfirm(action);
    if (action === "approve") {
      setCommand("review");
      setPreview(true);
    }
  }
  function send() {
    if (!confirm || !canSubmit(scenarioRef.current, commandRef.current)) return;
    const action = confirm;
    setConfirm(null);
    if (action === "decline") {
      setCommand("declined");
      setPreview(false);
      log("Route proposal declined · current task retained");
      return;
    }
    setSubmittedAction(action);
    setCommand("pending");
    log(
      `CMD-031 ${action === "stop" ? "stop request" : "authorization"} submitted · awaiting acknowledgment`,
    );
    timer.current = setTimeout(() => {
      if (isLocked(scenarioRef.current)) {
        setCommand("unconfirmed");
        log("CMD-031 delivery UNCONFIRMED · reconcile before retrying");
        return;
      }
      setCommand(outcome);
      if (outcome === "rejected") setRevision((value) => value + 1);
      log(
        outcome === "accepted"
          ? "CMD-031 accepted by asset · operational action not yet completed"
          : outcome === "rejected"
            ? "CMD-031 rejected · proposal revision changed"
            : "CMD-031 delivery UNCONFIRMED · do not assume execution",
        contact ? "USV-02" : "USV-03",
      );
    }, 1800);
  }
  function reconcile() {
    setScenario("monitoring");
    if (command === "unconfirmed") {
      setCommand("rejected");
      log(
        "CMD-031 reconciliation: asset reports NOT RECEIVED · safe to review again",
        "RECONCILIATION",
      );
    } else
      log(
        "Snapshot reconciled · no outstanding acknowledgments",
        "RECONCILIATION",
      );
    toast("Snapshot reconciled. Prototype controls restored.");
  }
  useEffect(() => {
    const tick = setInterval(() => {
      setWall(new Date());
      setFreezeAge((value) => (frozen ? value + 1 : 0));
      if (!paused && !frozen)
        setSim(
          (value) => value + (speed === "240×" ? 240 : speed === "5×" ? 5 : 1),
        );
    }, 1000);
    return () => clearInterval(tick);
  }, [paused, frozen, speed]);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const fleetContent = (
    <div className="flex flex-col gap-1">
      {fleet.map((boat) => {
        const stale = frozen || (scenario === "stale" && boat.id === "04");
        const cut = delegated && boat.id === "04";
        return (
          <Card
            key={boat.id}
            className="fleet-card gap-1 py-1.5"
            data-selected={selection?.id === boat.id}
            data-stale={stale}
          >
            <CardHeader className="gap-0 px-3">
              <div className="flex items-center justify-between gap-2">
                <CardTitle>
                  <Button
                    variant="ghost"
                    size="xs"
                    className="-ml-2"
                    onClick={() => select({ kind: "usv", id: boat.id })}
                    aria-pressed={selection?.id === boat.id}
                  >
                    <Ship data-icon="inline-start" />
                    USV-{boat.id}
                  </Button>
                </CardTitle>
                <Badge variant="outline">{boat.mode}</Badge>
              </div>
              <CardDescription className="flex justify-between gap-2">
                <span>{boat.role}</span>
                <span>{boat.endurance}</span>
              </CardDescription>
            </CardHeader>
            <CardContent className="px-3">
              <div className="flex justify-between gap-2 text-xs text-muted-foreground">
                <span>{boat.battery}% · est.</span>
                <span>Return {boat.returnBy}</span>
              </div>
            </CardContent>
            <CardFooter className="px-3">
              <div className="flex w-full justify-between gap-2 text-xs text-muted-foreground">
                <span>
                  {stale ? "LAST KNOWN" : cut ? "EXERCISE CUT" : boat.link}
                </span>
                <span>
                  {stale
                    ? frozen
                      ? `FROZEN · ${freezeAge}s`
                      : "00:42 ago"
                    : "< 1s"}
                </span>
              </div>
            </CardFooter>
          </Card>
        );
      })}
    </div>
  );

  const attentionContent = (
    <Tabs value={activeTab} onValueChange={setActiveTab} className="gap-4">
      <TabsList className="w-full">
        <TabsTrigger value="attention">
          Attention {outstanding && <Badge variant="secondary">1</Badge>}
        </TabsTrigger>
        <TabsTrigger value="context">Selected</TabsTrigger>
      </TabsList>
      <TabsContent value="attention" className="flex flex-col gap-4">
        <Card
          className="decision-card gap-4 py-4"
          tabIndex={0}
          role="article"
          aria-label="Decision D-031. Focus this card to use decision shortcuts."
          onKeyDown={(event) => {
            if (
              event.target !== event.currentTarget ||
              event.altKey ||
              event.ctrlKey ||
              event.metaKey ||
              locked ||
              !outstanding
            )
              return;
            const key = event.key.toLowerCase();
            if (key === (delegated ? "c" : "a")) {
              event.preventDefault();
              review("approve");
            }
            if (key === (delegated ? "s" : "d")) {
              event.preventDefault();
              review(delegated ? "stop" : "decline");
            }
          }}
        >
          <CardHeader className="gap-2 px-4">
            <div className="flex items-center justify-between gap-2">
              <Badge variant="secondary">
                {delegated ? "DELEGATED" : "HELD"}
              </Badge>
              <span className="text-xs text-muted-foreground">
                00:24 · routine
              </span>
            </div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>
              D-031 · {contact ? "USV-02 / C-024" : "USV-03 / P-04"} · revision{" "}
              {String(revision).padStart(2, "0")}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 px-4">
            <p>{rationale}</p>
            <p className="text-sm text-muted-foreground">
              {contact
                ? "Camera observation: 14:31:46Z. Name not read. Course unconfirmed. No AIS correlation does not establish intent."
                : "Transit conditions are not independently verified. The western patrol leg may be deferred by an estimated 3 min (demo)."}
            </p>
            <Separator />
            <p className="text-sm text-muted-foreground">
              Approval authorizes the action. It does not establish delivery,
              execution, or coverage.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPreview(!preview)}
              aria-pressed={preview}
            >
              {preview
                ? "Hide proposed route"
                : "Preview current & proposed routes"}
              <ArrowRight data-icon="inline-end" />
            </Button>
            {locked && (
              <Alert>
                <Unplug />
                <AlertTitle>Controls unavailable</AlertTitle>
                <AlertDescription>
                  {scenario === "truth"
                    ? "Operator commands are disabled in evaluator view."
                    : "Fresh confirmation is unavailable. Inspect last-known state only."}
                </AlertDescription>
              </Alert>
            )}
            {command === "pending" && (
              <Alert role="status">
                <Activity />
                <AlertTitle>COMMAND PENDING · CMD-031</AlertTitle>
                <AlertDescription>
                  Submitted, not yet acknowledged. Duplicate submission blocked.
                </AlertDescription>
              </Alert>
            )}
            {command === "accepted" && (
              <Alert role="status">
                <CheckCheck />
                <AlertTitle>ACCEPTED BY ASSET</AlertTitle>
                <AlertDescription>
                  {submittedAction === "stop"
                    ? "Stop request accepted. Task termination not yet reported."
                    : "Route accepted. Observation not yet completed."}
                </AlertDescription>
              </Alert>
            )}
            {command === "rejected" && (
              <Alert variant="destructive">
                <CircleAlert />
                <AlertTitle>Proposal rejected</AlertTitle>
                <AlertDescription>
                  Review fresh revision {String(revision).padStart(2, "0")}{" "}
                  before resubmitting.
                </AlertDescription>
              </Alert>
            )}
            {command === "unconfirmed" && (
              <Alert variant="destructive">
                <TriangleAlert />
                <AlertTitle>DELIVERY UNCONFIRMED</AlertTitle>
                <AlertDescription>
                  Do not assume execution. Reconcile the command ID before
                  retrying.
                </AlertDescription>
              </Alert>
            )}
            {command === "declined" && (
              <Alert role="status">
                <Check />
                <AlertTitle>DECLINED</AlertTitle>
                <AlertDescription>
                  Current task retained. No route change sent.
                </AlertDescription>
              </Alert>
            )}
            {command === "completed" && (
              <Alert role="status">
                <Check />
                <AlertTitle>
                  {submittedAction === "stop"
                    ? "TASK STOPPED · ASSET REPORT"
                    : "OBSERVATION RECORDED"}
                </AlertTitle>
                <AlertDescription>
                  {submittedAction === "stop"
                    ? "Task termination reported by the synthetic asset."
                    : gapClosed
                      ? "P-04 re-observed. Gap closed by a new observation."
                      : "Additional observation recorded. Identity remains unconfirmed."}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
          <CardFooter className="flex flex-wrap gap-2 px-4">
            {outstanding && (
              <>
                <Button disabled={locked} onClick={() => review("approve")}>
                  {delegated
                    ? "Confirm"
                    : command === "rejected"
                      ? "Review again"
                      : "Review & approve"}
                </Button>
                <Button
                  variant="outline"
                  disabled={locked}
                  onClick={() => review(delegated ? "stop" : "decline")}
                >
                  {delegated ? "Stop" : "Decline"}
                </Button>
              </>
            )}
            {command === "unconfirmed" && !locked && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setCommand("rejected");
                  log(
                    "CMD-031 status query: not received · retry permitted",
                    "RECONCILIATION",
                  );
                }}
              >
                Query asset command status
              </Button>
            )}
            {command === "accepted" && !locked && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setCommand("completed");
                  if (gap && submittedAction !== "stop") setGapClosed(true);
                  log(
                    submittedAction === "stop"
                      ? "Task termination reported"
                      : gap
                        ? "P-04 re-observed · GAP CLOSED by observation"
                        : "Observation delivered · identity unconfirmed",
                    contact ? "USV-02" : "USV-03",
                    "Observation",
                    gap ? "P-04" : "C-024",
                  );
                }}
              >
                {submittedAction === "stop"
                  ? "Demo: deliver task termination"
                  : "Demo: deliver new observation"}
              </Button>
            )}
          </CardFooter>
        </Card>
        {gap || degraded ? (
          <Alert className="alert-item">
            <CircleAlert />
            <AlertTitle>
              {gap
                ? "P-04 · GAP OPEN"
                : delegated
                  ? "USV-04 · simulated link interrupted"
                  : "USV-04 · observation stale"}
            </AlertTitle>
            <AlertDescription>
              <p>
                {gap
                  ? "18:42 visit age. Target exceeded by 03:42. Approval does not close the gap."
                  : delegated
                    ? "Exercise event, not equipment failure. Last-known task remains visible."
                    : "Last observed 00:42 ago. Cause unknown; other assets remain fresh."}
              </p>
              <span>14:31:36Z · {gap ? "COVERAGE" : "USV-04"}</span>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    select({
                      kind: gap ? "segment" : "usv",
                      id: gap ? "P-04" : "04",
                    })
                  }
                >
                  Inspect context
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={acknowledged}
                  onClick={() => {
                    setAcknowledged(true);
                    log(
                      "Warning acknowledged · underlying condition remains active",
                      "OPERATOR",
                      "System",
                    );
                  }}
                >
                  {acknowledged ? "Acknowledged · active" : "Acknowledge"}
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        ) : (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Check />
            No active alarms or warnings
          </p>
        )}
        <Card className="gap-3 py-4">
          <CardHeader className="px-4">
            <CardTitle>Cable coverage</CardTitle>
            <CardDescription>
              {gap
                ? "GAP OPEN · 03:42 overdue"
                : "1 unknown / unvisited segment"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 px-4">
            <div className="flex justify-between gap-4">
              <div>
                <p className="text-xs text-muted-foreground">
                  Oldest observed visit
                </p>
                <p>{gap ? "18m 42s" : gapClosed ? "08m 12s" : "12m 18s"}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Target revisit</p>
                <p>15m 00s</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-1">
              {["P-01", "P-02", "P-03", "P-04", "D-01", "D-02"].map((id) => (
                <Button
                  key={id}
                  size="sm"
                  variant={id === "P-04" && gap ? "destructive" : "outline"}
                  onClick={() => select({ kind: "segment", id })}
                >
                  {id}
                  {id === "D-02" && " ?"}
                </Button>
              ))}
            </div>
          </CardContent>
          <CardFooter className="px-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => select({ kind: "segment", id: "P-04" })}
            >
              Inspect segment
            </Button>
          </CardFooter>
        </Card>
        <Button
          variant="outline"
          onClick={() => select({ kind: "contact", id: "C-024" })}
        >
          C-024 · NO AIS · cue for a look
          <ArrowRight data-icon="inline-end" />
        </Button>
      </TabsContent>
      <TabsContent
        value="context"
        className="context-content flex flex-col gap-4"
      >
        {!selection ? (
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Ship />
              </EmptyMedia>
              <EmptyTitle>Select an entity</EmptyTitle>
              <EmptyDescription>
                Choose a vessel, contact, or cable segment. The chart and watch
                overview stay in place.
              </EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
              <Button
                variant="outline"
                onClick={() => setActiveTab("attention")}
              >
                Back to attention
              </Button>
            </EmptyContent>
          </Empty>
        ) : (
          <Card className="gap-4 py-4">
            <CardHeader className="px-4">
              <CardTitle>
                {selectedBoat ? `USV-${selectedBoat.id}` : selection.id}
              </CardTitle>
              <CardDescription>
                {selectedBoat
                  ? `${selectedBoat.role} · ${selectedBoat.mode}`
                  : selection.kind === "contact"
                    ? "Delivered contact evidence"
                    : "Delivered coverage observations"}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 px-4">
              {selectedBoat ? (
                <>
                  <Badge variant="outline">
                    {frozen ||
                    (scenario === "stale" && selectedBoat.id === "04")
                      ? "LAST-KNOWN STATE · NOT LIVE"
                      : "SYNTHETIC OBSERVATION"}
                  </Badge>
                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    <dt className="text-muted-foreground">Last observation</dt>
                    <dd>
                      {frozen
                        ? "14:32:18Z · FROZEN"
                        : scenario === "stale" && selectedBoat.id === "04"
                          ? "14:31:36Z · 00:42 ago"
                          : "14:32:18Z · < 1s"}
                    </dd>
                    <dt className="text-muted-foreground">Link</dt>
                    <dd>
                      {degraded && selectedBoat.id === "04"
                        ? "CURRENT LINK UNKNOWN"
                        : selectedBoat.link}
                    </dd>
                    <dt className="text-muted-foreground">
                      Endurance estimate
                    </dt>
                    <dd>{selectedBoat.endurance}</dd>
                    <dt className="text-muted-foreground">Return by</dt>
                    <dd>{selectedBoat.returnBy}</dd>
                    <dt className="text-muted-foreground">Energy trend</dt>
                    <dd>{selectedBoat.trend}</dd>
                  </dl>
                  <Alert>
                    <Radio />
                    <AlertTitle>Radio context</AlertTitle>
                    <AlertDescription>
                      {selectedBoat.id === "03"
                        ? "USV-03 → USV-04 → Korsør"
                        : "Path information is from the last received snapshot, not a guarantee of reachability."}
                    </AlertDescription>
                  </Alert>
                  <Button
                    variant="outline"
                    disabled={
                      locked ||
                      (scenario === "stale" && selectedBoat.id === "04")
                    }
                    onClick={() => {
                      setActiveTab("attention");
                      setPreview(true);
                    }}
                  >
                    Review proposed assignment
                  </Button>
                </>
              ) : selection.kind === "contact" ? (
                <>
                  <Badge variant="outline">
                    {selection.id === "C-024"
                      ? "CAMERA ONLY · NO AIS CORRELATION"
                      : "AIS OBSERVATION"}
                  </Badge>
                  <p>Last observation 14:31:46Z · 00:32 ago · USV-02.</p>
                  <p className="text-muted-foreground">
                    {selection.id === "C-024"
                      ? "NAME NOT READ · COURSE UNCONFIRMED · SPEED UNKNOWN · ANCHOR NOT SEEN. Missing AIS does not establish intent."
                      : "Reported identity and course are self-reported, not independently verified."}
                  </p>
                  <Empty>
                    <EmptyHeader>
                      <EmptyMedia variant="icon">
                        <Eye />
                      </EmptyMedia>
                      <EmptyTitle>Image evidence not supplied</EmptyTitle>
                      <EmptyDescription>
                        This prototype contains no camera imagery.
                      </EmptyDescription>
                    </EmptyHeader>
                  </Empty>
                  <Button
                    disabled={locked}
                    onClick={() => {
                      changeScenario("contact");
                      setActiveTab("attention");
                    }}
                  >
                    Review observation request
                  </Button>
                </>
              ) : (
                <>
                  <Badge variant="outline">
                    {selection.id === "D-02"
                      ? "UNKNOWN / UNVISITED"
                      : gap && selection.id === "P-04"
                        ? "GAP OPEN"
                        : "OBSERVATION AVAILABLE"}
                  </Badge>
                  <dl className="grid grid-cols-2 gap-3">
                    <dt className="text-muted-foreground">Visit age</dt>
                    <dd>
                      {selection.id === "D-02"
                        ? "UNKNOWN"
                        : gap && selection.id === "P-04"
                          ? "18m 42s"
                          : "12m 18s"}
                    </dd>
                    <dt className="text-muted-foreground">Target</dt>
                    <dd>15m 00s</dd>
                  </dl>
                  <p className="text-sm text-muted-foreground">
                    Coverage changes only after a delivered observation, not a
                    planned route or accepted command.
                  </p>
                  <Button
                    variant="outline"
                    disabled={locked}
                    onClick={() => changeScenario("gap")}
                  >
                    Review corrective action
                  </Button>
                </>
              )}
            </CardContent>
            <CardFooter className="px-4">
              <Button variant="ghost" onClick={() => setActiveTab("attention")}>
                Return to attention · keep selection
              </Button>
            </CardFooter>
          </Card>
        )}
      </TabsContent>
    </Tabs>
  );

  const filteredEvents = events
    .filter(
      (event) => eventFilter === "All events" || event.category === eventFilter,
    )
    .slice(0, timelineOpen ? 12 : 2);
  return (
    <TooltipProvider>
      <div className="flex h-dvh min-h-[720px] flex-col bg-background text-foreground">
        <header className="flex min-h-16 shrink-0 flex-wrap items-center gap-4 border-b px-4 py-3">
          <a href="#main" className="flex items-center gap-2 font-semibold">
            <Waves />
            EDTH_07
          </a>
          <Separator orientation="vertical" className="hidden h-7 sm:block" />
          <span className="hidden text-sm text-muted-foreground min-[1400px]:block">
            Great Belt · cable watch
          </span>
          <div className="ml-auto flex items-center gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Wall UTC</p>
              <p className="tabular-nums">
                {wall.toISOString().slice(11, 19)}Z
              </p>
            </div>
            <div className="hidden md:block">
              <p className="text-xs text-muted-foreground">Simulation</p>
              <p className="tabular-nums">
                T+
                {Math.floor(sim / 3600)
                  .toString()
                  .padStart(2, "0")}
                :
                {Math.floor((sim / 60) % 60)
                  .toString()
                  .padStart(2, "0")}
                :{(sim % 60).toString().padStart(2, "0")}
              </p>
            </div>
            <Button
              variant="outline"
              size="icon"
              disabled={frozen}
              onClick={() => setPaused(!paused)}
              aria-label={paused ? "Resume simulation" : "Pause simulation"}
            >
              {paused ? <Play /> : <Pause />}
            </Button>
            <Select value={speed} onValueChange={setSpeed} disabled={frozen}>
              <SelectTrigger
                aria-label="Simulation speed"
                size="sm"
                className="hidden w-20 md:flex"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {["Auto", "1×", "5×", "240×"].map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <ToggleGroup
              type="single"
              variant="outline"
              size="sm"
              value={scenario === "truth" ? "truth" : "shore"}
              onValueChange={(value) => {
                if (
                  value &&
                  value !== (scenario === "truth" ? "truth" : "shore")
                )
                  changeScenario(value === "truth" ? "truth" : "monitoring");
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
            <Button
              variant="outline"
              size="sm"
              onClick={() => setExerciseOpen(true)}
            >
              <Settings2 data-icon="inline-start" />
              <span className="hidden lg:inline">Exercise</span>
            </Button>
            <Badge variant={frozen ? "destructive" : "outline"}>
              {scenario === "lost"
                ? "FEED LOST"
                : scenario === "recovery"
                  ? "RECONCILING"
                  : "LOCAL DEMO"}
            </Badge>
          </div>
        </header>
        <div className="flex shrink-0 items-center justify-between gap-3 border-b px-4 py-2">
          <p className="text-xs text-muted-foreground">
            Synthetic demonstration · no operational connection
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setScenarioOpen(true)}
          >
            Scenarios
          </Button>
        </div>
        {scenario === "lost" && (
          <Alert
            variant="destructive"
            className="shrink-0 rounded-none border-x-0 border-t-0"
          >
            <WifiOff />
            <AlertTitle>FEED LOST — display frozen at 14:32:18Z</AlertTitle>
            <AlertDescription>
              <p>
                Frozen for {freezeAge}s. All positions are last-known. Commands
                disabled.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setScenario("recovery");
                  log(
                    "Transport restored · reconciliation required",
                    "FEED",
                    "System",
                  );
                }}
              >
                Simulate reconnect
                <ArrowRight data-icon="inline-end" />
              </Button>
            </AlertDescription>
          </Alert>
        )}
        {scenario === "recovery" && (
          <Alert className="shrink-0 rounded-none border-x-0 border-t-0">
            <Activity />
            <AlertTitle>FEED RESTORED · RECONCILIATION REQUIRED</AlertTitle>
            <AlertDescription>
              <p>Frozen picture retained. Command outcomes are not assumed.</p>
              <Button variant="outline" size="sm" onClick={reconcile}>
                Review & reconcile
              </Button>
            </AlertDescription>
          </Alert>
        )}
        {delegated && (
          <Alert className="shrink-0 rounded-none border-x-0 border-t-0">
            <Settings2 />
            <AlertTitle>EXERCISE ACTIVE · SIMULATED LINK CUT</AlertTitle>
            <AlertDescription>
              <p>USV-04 ↔ shore · not an actual equipment failure</p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setScenario("monitoring");
                  log(
                    "Exercise ended · synthetic direct link restored",
                    "EXERCISE",
                    "System",
                    "04",
                  );
                }}
              >
                End exercise
              </Button>
            </AlertDescription>
          </Alert>
        )}
        {scenario === "truth" && (
          <Alert className="shrink-0 rounded-none border-x-0 border-t-0">
            <Eye />
            <AlertTitle>EVALUATOR / TRUTH VIEW</AlertTitle>
            <AlertDescription>
              <p>
                Truth-only annotations are not shore observations. Operator
                commands disabled.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => changeScenario("monitoring")}
              >
                Return to SHORE
              </Button>
            </AlertDescription>
          </Alert>
        )}
        <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
          <div className="flex items-center gap-3 text-sm">
            <span>
              {degraded ? "4" : "5"}/5 assets{" "}
              {frozen ? "last-known" : "reporting"}
            </span>
            <Separator orientation="vertical" className="h-4" />
            <span>{gap ? "1 GAP OPEN" : "Coverage: 1 unknown segment"}</span>
          </div>
          <Badge variant="secondary">
            {outstanding ? "1" : "0"} {delegated ? "delegated" : "held"}{" "}
            decision
          </Badge>
        </div>
        <div className="flex shrink-0 justify-between border-b p-2 xl:hidden">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDrawer("fleet")}
          >
            <Menu data-icon="inline-start" />
            Fleet · 5
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setDrawer("attention")}
          >
            Attention · {outstanding ? "1" : "0"} decision
          </Button>
        </div>
        <main
          id="main"
          className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[260px_minmax(0,1fr)_352px]"
        >
          <aside
            className="fleet-panel hidden min-h-0 flex-col gap-3 overflow-y-auto border-r p-2 xl:flex"
            aria-label="Fleet overview"
          >
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Fleet overview</h2>
              <Badge variant="outline">05</Badge>
            </div>
            {fleetContent}
          </aside>
          <OperationalMap
            scenario={scenario}
            selection={selection}
            onSelect={select}
            command={command}
            preview={preview}
            onPreview={() => setPreview(!preview)}
            gapClosed={gapClosed}
          />
          <aside
            className="attention-panel hidden min-h-0 flex-col gap-3 overflow-y-auto border-l p-3 xl:flex"
            aria-label="Operator attention workspace"
          >
            <h2 className="py-1 font-semibold">Operator attention</h2>
            {attentionContent}
          </aside>
        </main>
        <section className="shrink-0 border-t" aria-label="Event timeline">
          <div className="flex items-center justify-between gap-3 border-b px-4 py-2">
            <span className="flex items-center gap-2 text-sm">
              <Activity />
              Event timeline<Badge variant="secondary">{events.length}</Badge>
            </span>
            <div className="flex gap-2">
              <Select value={eventFilter} onValueChange={setEventFilter}>
                <SelectTrigger
                  size="sm"
                  aria-label="Filter event timeline"
                  className="w-32"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {[
                      "All events",
                      "Coordination",
                      "Observation",
                      "Coverage",
                      "Command",
                      "System",
                      "Scenario",
                    ].map((value) => (
                      <SelectItem key={value} value={value}>
                        {value}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setTimelineOpen(!timelineOpen)}
                aria-expanded={timelineOpen}
              >
                {timelineOpen ? "Collapse" : "Expand"}
              </Button>
            </div>
          </div>
          <div className="max-h-44 overflow-y-auto">
            {filteredEvents.length ? (
              filteredEvents.map((event, index) => (
                <Button
                  key={`${index}-${event.text}`}
                  variant="ghost"
                  className="flex h-auto w-full justify-start gap-4 rounded-none px-4 py-2"
                  onClick={() =>
                    select({
                      kind: event.ref.startsWith("C-")
                        ? "contact"
                        : event.ref.startsWith("P-")
                          ? "segment"
                          : "usv",
                      id: event.ref,
                    })
                  }
                >
                  <time className="shrink-0 tabular-nums">{event.time}Z</time>
                  <span className="w-20 shrink-0 text-left">
                    {event.source}
                  </span>
                  <span className="hidden w-24 shrink-0 text-left text-muted-foreground md:block">
                    {event.category}
                  </span>
                  <span className="truncate text-muted-foreground">
                    {event.text}
                  </span>
                </Button>
              ))
            ) : (
              <Empty className="p-3">
                <EmptyHeader>
                  <EmptyTitle>No matching events</EmptyTitle>
                </EmptyHeader>
              </Empty>
            )}
          </div>
        </section>
        <footer className="flex shrink-0 items-center justify-between gap-3 border-t px-4 py-2 text-xs text-muted-foreground">
          <span>Korsør shore station · offline template</span>
          <Button variant="ghost" size="sm" onClick={() => setHelpOpen(true)}>
            <Keyboard data-icon="inline-start" />
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
            className="overflow-y-auto"
          >
            <SheetHeader>
              <SheetTitle>
                {drawer === "fleet" ? "Fleet overview" : "Operator attention"}
              </SheetTitle>
              <SheetDescription>
                Synthetic observations · no operational connection
              </SheetDescription>
            </SheetHeader>
            <div className="px-4 pb-4">
              {drawer === "fleet" ? fleetContent : attentionContent}
            </div>
          </SheetContent>
        </Sheet>
        <Dialog
          open={confirm !== null}
          onOpenChange={(open) => {
            if (!open) {
              setConfirm(null);
              if (command === "review") setCommand("idle");
            }
          }}
        >
          <DialogContent
            onCloseAutoFocus={(event) => {
              if (returnFocus.current?.isConnected) {
                event.preventDefault();
                returnFocus.current.focus();
              }
            }}
          >
            <DialogHeader>
              <DialogTitle>
                {confirm === "approve"
                  ? "Approve proposed action"
                  : confirm === "stop"
                    ? "Stop delegated task?"
                    : "Decline proposed route?"}
              </DialogTitle>
              <DialogDescription>
                D-031 · CMD-031 · synthetic demonstration
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4">
              <Badge variant="outline">
                {delegated
                  ? "DELEGATED TASK · CONTROL REQUEST"
                  : "PROPOSED · NOT EXECUTING"}
              </Badge>
              <p>{title}</p>
              <p className="text-sm text-muted-foreground">{rationale}</p>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <dt className="text-muted-foreground">Affected entity</dt>
                <dd>{contact ? "USV-02 / C-024" : "USV-03 / P-04"}</dd>
                <dt className="text-muted-foreground">Proposal revision</dt>
                <dd>
                  {String(revision).padStart(2, "0")} · latest synthetic
                  snapshot
                </dd>
                <dt className="text-muted-foreground">Reversibility</dt>
                <dd>Requires another acknowledged proposal.</dd>
              </dl>
              <Alert>
                <CircleAlert />
                <AlertTitle>Authorization is not completion</AlertTitle>
                <AlertDescription>
                  Wait for asset acknowledgment. Coverage changes only after a
                  delivered observation. A stop request also requires
                  acknowledgment and a task-termination report.
                </AlertDescription>
              </Alert>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Back to review</Button>
              </DialogClose>
              <Button disabled={!canSubmit(scenario, command)} onClick={send}>
                {confirm === "approve"
                  ? "Authorize & send"
                  : confirm === "stop"
                    ? "Stop task"
                    : "Decline proposal"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <Dialog open={scenarioOpen} onOpenChange={setScenarioOpen}>
          <DialogContent className="max-h-[85dvh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Operational scenarios</DialogTitle>
              <DialogDescription>
                Local synthetic states only. No backend or real commands.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-2">
              {scenarios.map((item) => (
                <Button
                  key={item.id}
                  variant="outline"
                  className="h-auto justify-start whitespace-normal py-3 text-left"
                  onClick={() => changeScenario(item.id)}
                >
                  {item.label}
                  <span className="sr-only"> · {item.description}</span>
                </Button>
              ))}
            </div>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="command-outcome">
                  Next synthetic command response
                </FieldLabel>
                <Select
                  value={outcome}
                  onValueChange={(value) => setOutcome(value as typeof outcome)}
                >
                  <SelectTrigger
                    id="command-outcome"
                    aria-label="Next synthetic command response"
                    className="w-full"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      <SelectItem value="accepted">
                        Accepted after 1.8s
                      </SelectItem>
                      <SelectItem value="rejected">
                        Rejected · revision changed
                      </SelectItem>
                      <SelectItem value="unconfirmed">
                        Unconfirmed · no acknowledgment
                      </SelectItem>
                    </SelectGroup>
                  </SelectContent>
                </Select>
                <FieldDescription>
                  Controls only the next local demonstration response.
                </FieldDescription>
              </Field>
            </FieldGroup>
          </DialogContent>
        </Dialog>
        <Dialog open={exerciseOpen} onOpenChange={setExerciseOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Exercise controls</DialogTitle>
              <DialogDescription>
                Evaluator controls, separate from operational authority.
              </DialogDescription>
            </DialogHeader>
            <Alert>
              <Settings2 />
              <AlertTitle>Simulated link interruption</AlertTitle>
              <AlertDescription>
                Cut USV-04 ↔ shore in the demonstration. A persistent EXERCISE
                banner identifies the simulated condition. No actual connection
                changes.
              </AlertDescription>
            </Alert>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Cancel</Button>
              </DialogClose>
              <Button
                onClick={() => {
                  changeScenario("exercise");
                  setExerciseOpen(false);
                }}
              >
                Start link-cut exercise
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <Dialog open={helpOpen} onOpenChange={setHelpOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Watch guide & keyboard</DialogTitle>
              <DialogDescription>
                Supervise the swarm. Approve decisions, not steering commands.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 text-sm">
              <p>
                Tab moves focus. Enter or Space selects controls and chart
                entities. Arrow keys navigate tabs and option groups. Escape
                closes overlays.
              </p>
              <p>
                Focus the decision card itself: A/D review held actions; C/S
                review delegated actions. Shortcuts never submit directly and
                never act from another control.
              </p>
              <Separator />
              <p>
                Feed loss freezes observations and locks commands. Recovery
                requires explicit reconciliation. Alert acknowledgment does not
                resolve the condition. An accepted route does not close a
                coverage gap.
              </p>
              <p>
                All observations and ages are synthetic. The runtime has no
                operational feed. Satellite imagery and camera frames are not
                supplied.
              </p>
            </div>
          </DialogContent>
        </Dialog>
        <Toaster theme="dark" closeButton />
      </div>
    </TooltipProvider>
  );
}
