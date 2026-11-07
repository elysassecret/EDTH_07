import { useEffect, useState } from "react";
import { CircleAlert, FileCheck, Settings2 } from "lucide-react";
import { toast } from "sonner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Switch } from "@/components/ui/switch";
import { actionsFor, alertAction, endpoint, groupAlerts, sortedAlerts, usv, type AlertGroup } from "../console-model";
import type { DecisionFlow } from "./LiveDecisions";
import { dur, utc } from "../format";
import { apiUrl, useStore } from "../store";
import { t0Of, type Alert as AlertRecord, type Command } from "../types";

// Each level has its own shape and colour, so it reads without colour too (ship's bridge style):
// ALARM red triangle · WARNING orange circle · CAUTION yellow square.
export function LevelIcon({ level }: { level: AlertRecord["level"] }) {
  const fill = level === "alarm" ? "fill-red-500" : level === "warning" ? "fill-orange-400" : "fill-yellow-300";
  return (
    <svg aria-hidden="true" data-level={level} viewBox="0 0 18 18" className={`size-5 shrink-0 ${fill}`}>
      {level === "alarm" && <path d="M9 1.5 17 16.5H1z" />}
      {level === "warning" && <circle cx="9" cy="9" r="7.5" />}
      {level === "caution" && <rect x="2" y="2" width="14" height="14" />}
      <text x="9" y={level === "alarm" ? 14.5 : 13} textAnchor="middle" fontSize="11" fontWeight="700" className="fill-neutral-950">!</text>
    </svg>
  );
}

export function PriorityAlert() {
  const snap = useStore((s) => s.snap);
  const conn = useStore((s) => s.conn);
  const channel = useStore((s) => s.channel);
  const send = useStore((s) => s.send);
  const setDigest = useStore((s) => s.setDigest);
  const top = sortedAlerts(snap?.alerts ?? []).find((a) => !a.ack && a.level === "alarm"); // #88: the banner is for alarms only
  if (!top) return null;
  return <section aria-label="Priority alert" role="alert" className="flex shrink-0 items-center gap-3 border-b px-4 py-2 text-sm">
    <LevelIcon level={top.level} /><strong>{top.level.toUpperCase()}</strong><span className="min-w-0 flex-1 truncate" title={top.text}>{top.text}</span>
    <Button variant="outline" size="sm" disabled={conn !== "live" || channel !== "shore"} onClick={() => { if (send({ cmd: "ack", id: top.id })) setDigest(true); }}>Acknowledge</Button>
  </section>;
}

/** #88 item 5: one card per boat, cable, contact or picket; the newest alert open with what the
 * operator can do (answer a held decision) or "No action: information only"; the rest folded. */
export function LiveAlerts({ flow }: { flow: DecisionFlow }) {
  const snap = useStore((s) => s.snap);
  if (!snap) return null;
  const groups = groupAlerts(snap.alerts, snap);
  const open = snap.alerts.filter((a) => !a.ack).length;
  return (
    <section className="space-y-2" aria-label="Alerts">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Alerts</h3>
        <Badge variant="outline">{open} unacknowledged</Badge>
      </div>
      {groups.length === 0 && <p className="text-sm text-muted-foreground">No alerts in this picture.</p>}
      {groups.map((g) => <AlertGroupCard key={g.subject.key} group={g} flow={flow} />)}
    </section>
  );
}

function AlertGroupCard({ group, flow }: { group: AlertGroup; flow: DecisionFlow }) {
  const snap = useStore((s) => s.snap)!;
  const conn = useStore((s) => s.conn);
  const channel = useStore((s) => s.channel);
  const send = useStore((s) => s.send);
  const setDigest = useStore((s) => s.setDigest);
  const select = useStore((s) => s.select);
  const selectContact = useStore((s) => s.selectContact);
  const selectSegment = useStore((s) => s.selectSegment);
  const [more, setMore] = useState(false);
  const [top, ...rest] = group.alerts;
  const live = conn === "live" && channel === "shore";
  const { subject } = group;
  const d = alertAction(top, snap) === "answer" ? subject.decision : undefined;
  const show = subject.boat !== undefined ? () => select(subject.boat!)
    : subject.contact ? () => selectContact(subject.contact!)
    : subject.segment ? () => selectSegment(subject.segment!) : null;
  const ack = (id: string) => { if (send({ cmd: "ack", id })) setDigest(true); };
  return (
    <Alert variant={top.level === "alarm" && !top.ack ? "destructive" : "default"} aria-label={`Alerts: ${subject.title}`}>
      <LevelIcon level={top.level} />
      <AlertTitle className="flex flex-wrap items-center justify-between gap-2">
        <span>{subject.title} · {top.level.toUpperCase()}</span>
        <time className="font-normal text-muted-foreground">{utc(t0Of(snap), top.t)}</time>
      </AlertTitle>
      <AlertDescription className="space-y-2">
        <p>{top.text}</p>
        <div className="flex flex-wrap items-center gap-2">
          {d ? actionsFor(d).map((action) => (
            <Button key={action} size="sm" variant={action === "approve" || action === "confirm" ? "default" : "outline"}
              disabled={!live || !!flow.held} onClick={() => flow.begin(d, action)}>
              {action === "approve" ? "Review & approve" : action[0].toUpperCase() + action.slice(1)}
            </Button>
          )) : <span className="text-muted-foreground">No action: information only</span>}
          {top.ack ? <span className="text-muted-foreground">Acknowledged · condition may still be active</span>
            : <Button variant="outline" size="sm" disabled={!live} onClick={() => ack(top.id)}>Acknowledge</Button>}
          {show && <Button variant="ghost" size="sm" onClick={show}>Show</Button>}
        </div>
        {rest.length > 0 && (
          <Button variant="ghost" size="sm" className="-ml-2" aria-expanded={more} onClick={() => setMore(!more)}>
            {more ? "Hide older" : `+${rest.length} older`}
          </Button>
        )}
        {more && (
          <ul className="space-y-1">
            {rest.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-2">
                <LevelIcon level={a.level} />
                <span className="min-w-0 flex-1">{utc(t0Of(snap), a.t)} · {a.text}</span>
                {!a.ack && <Button variant="outline" size="sm" disabled={!live} onClick={() => ack(a.id)}>Acknowledge</Button>}
              </li>
            ))}
          </ul>
        )}
      </AlertDescription>
    </Alert>
  );
}

export function DigestSummary() {
  const snap = useStore((s) => s.snap);
  const open = useStore((s) => s.digestOpen);
  const since = useStore((s) => s.lastLookT);
  const set = useStore((s) => s.setDigest);
  useEffect(() => {
    let timer: number;
    const arm = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => set(true), 120000);
    };
    const events = ["pointerdown", "keydown", "wheel"];
    events.forEach((event) =>
      window.addEventListener(event, arm, { passive: true }),
    );
    arm();
    return () => {
      window.clearTimeout(timer);
      events.forEach((event) => window.removeEventListener(event, arm));
    };
  }, [set]);
  if (!open || !snap) return null;
  const lines = (snap.narration ?? [])
    .filter((n) => since === null || n.t > since)
    .slice(-5);
  return (
    <Alert className="shrink-0 rounded-none border-x-0 border-t-0">
      <CircleAlert />
      <AlertTitle>Since you last looked</AlertTitle>
      <AlertDescription>
        <ul>
          {lines.length ? (
            lines.map((line, i) => (
              <li key={`${line.t}-${i}`}>
                {utc(t0Of(snap), line.t)} · {line.text}
              </li>
            ))
          ) : (
            <li>No reported changes.</li>
          )}
        </ul>
        <Button variant="outline" size="sm" onClick={() => set(false, snap.t)}>
          Got it
        </Button>
      </AlertDescription>
    </Alert>
  );
}

/** Exercise conditions still in effect, from the server, with one-click undo. An undo is an
 * ordinary inject (link_on / boat_restore), so it is logged and shown as EXERCISE like any other. */
export function ExercisesInEffect({ onSend }: { onSend: (commands: Command[]) => void }) {
  const snap = useStore((s) => s.snap);
  const conn = useStore((s) => s.conn);
  const items = snap?.exercises;
  if (!snap || items === undefined) return null;
  const undoable = items.flatMap((i) => i.undo ?? []);
  return (
    <section aria-label="Exercise conditions in effect" className="space-y-2">
      <h3 className="text-sm font-medium">In effect now · {items.length}</h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No exercise condition is in effect.</p>
      ) : (
        <ul className="space-y-1">
          {items.map((i, n) => (
            <li key={`${i.kind}-${i.t}-${n}`} className="flex items-start justify-between gap-2 rounded-md border p-2 text-sm">
              <span className="min-w-0">
                <span className="block">{i.text.replace(/^EXERCISE: /, "").replace(/ \[[^\]]*\]$/, "")}</span>
                <span className="text-xs text-muted-foreground">
                  since {utc(t0Of(snap), i.t)} · {i.origin}
                  {i.undo === null && " · cannot be undone in this run (no recharge in the simulator yet); a reset clears it"}
                </span>
              </span>
              {i.undo && (
                <Button variant="outline" size="sm" disabled={conn !== "live"} onClick={() => onSend(i.undo!)}>
                  Undo
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
      {undoable.length > 1 && (
        <Button variant="outline" disabled={conn !== "live"} onClick={() => onSend(undoable)}>
          Undo all {undoable.length} that can be undone
        </Button>
      )}
    </section>
  );
}

function ExerciseAction({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3 rounded-md border p-2">
      <Button variant="outline" size="sm" className="w-32 shrink-0" disabled={disabled} onClick={onClick}>
        {label}
      </Button>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}

export function ExerciseTools({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const snap = useStore((s) => s.snap);
  const conn = useStore((s) => s.conn);
  const send = useStore((s) => s.send);
  const placing = useStore((s) => s.placing);
  const setPlacing = useStore((s) => s.setPlacing);
  const ack = useStore((s) => s.lastAck);
  const [boat, setBoat] = useState("1");
  const [other, setOther] = useState("shore");
  const [both, setBoth] = useState(false);
  const [ais, setAis] = useState(false);
  const [seed, setSeed] = useState("1");
  const [resetReview, setResetReview] = useState(false);
  useEffect(() => {
    if (open) {
      setSeed(String(useStore.getState().snap?.seed ?? 1));
      setResetReview(false);
      const sel = useStore.getState().selected; // the boat you have selected on the chart
      if (sel !== null) setBoat(String(sel));
    }
  }, [open]);
  const ids = snap?.boats.map((b) => b.id).sort((a, b) => a - b) ?? [];
  const id = ids.includes(Number(boat)) ? Number(boat) : ids[0];
  const target =
    other === "shore" || ids.some((i) => i !== id && String(i) === other)
      ? other
      : "shore";
  const disabled = conn !== "live" || id === undefined;
  function fire(commands: Command[]) {
    for (const c of commands)
      if (!send(c)) {
        toast.error("Not sent: fresh feed unavailable.");
        break;
      }
  }
  function link(kind: "link_off" | "link_on") {
    if (id === undefined) return;
    const to = target === "shore" ? "shore" : Number(target);
    const commands: Command[] = [{ cmd: "inject", kind, a: id, b: to }];
    if (both && to !== "shore")
      commands.push({ cmd: "inject", kind, a: to, b: id });
    fire(commands);
  }
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85dvh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Exercise controls</DialogTitle>
          <DialogDescription>
            Test the swarm by breaking something on purpose. Nothing happens unless you press a
            button here: 1. pick a boat, 2. pick what goes wrong. Each one is marked EXERCISE on
            the chart and in the timeline, and Undo puts it back.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <ExercisesInEffect onSend={fire} />
          <Separator />
          <div role="group" aria-label="Exercise boat" className="space-y-2">
            <p className="text-sm font-medium">1. Pick a boat</p>
            <div className="flex flex-wrap gap-2">
              {ids.map((i) => {
                const b = snap?.boats.find((x) => x.id === i);
                return (
                  <Button
                    key={i}
                    variant={i === id ? "default" : "outline"}
                    size="sm"
                    aria-pressed={i === id}
                    aria-label={usv(i)}
                    onClick={() => setBoat(String(i))}
                  >
                    {usv(i)}
                    <span className="text-xs opacity-70">{b?.mode === "UNAVAILABLE" ? "OFF" : b?.mode}</span>
                  </Button>
                );
              })}
              {!ids.length && <span className="text-sm text-muted-foreground">Waiting for the first boat report.</span>}
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">2. What goes wrong{id !== undefined ? ` on ${usv(id)}` : ""}</p>
            <ExerciseAction
              label="Battery low"
              disabled={disabled}
              onClick={() => id !== undefined && fire([{ cmd: "inject", kind: "battery_low", a: id }])}
            >
              Its battery drops to just enough to get home. It goes back to Korsør by itself, gets a
              battery swap (about 10 min) and comes back; the others take over its work meanwhile.
            </ExerciseAction>
            <ExerciseAction
              label="Switch off"
              disabled={disabled}
              onClick={() => id !== undefined && fire([{ cmd: "inject", kind: "boat_off", a: id }])}
            >
              The boat stops dead: no motion, no radio. The shore only knows it went quiet; the
              others take over its tasks once its lease runs out.
            </ExerciseAction>
            <ExerciseAction
              label="Switch back on"
              disabled={disabled}
              onClick={() => id !== undefined && fire([{ cmd: "inject", kind: "boat_restore", a: id }])}
            >
              The same boat and agent again, with the battery it had. Reports come back only when
              the shore hears it.
            </ExerciseAction>
          </div>
          <Field>
            <FieldLabel>Link to</FieldLabel>
            <Select value={target} onValueChange={setOther}>
              <SelectTrigger aria-label="Link destination">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="shore">shore</SelectItem>
                  {ids
                    .filter((i) => i !== id)
                    .map((i) => (
                      <SelectItem key={i} value={String(i)}>
                        {usv(i)}
                      </SelectItem>
                    ))}
                </SelectGroup>
              </SelectContent>
            </Select>
            <FieldDescription>
              Node 0 is shore. A docked USV remains a separate peer.
            </FieldDescription>
          </Field>
          {target !== "shore" && (
            <Field orientation="horizontal">
              <Switch
                id="both-directions"
                checked={both}
                onCheckedChange={setBoth}
              />
              <FieldLabel htmlFor="both-directions">Both directions</FieldLabel>
            </Field>
          )}
          <p className="text-sm text-muted-foreground">
            {id === undefined
              ? "Waiting for a boat report."
              : `${usv(id)} ${both && target !== "shore" ? "↔" : "→"} ${target === "shore" ? "shore" : endpoint(Number(target))}`}
            . A one-way cut does not cut the reverse direction.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              disabled={disabled}
              onClick={() => link("link_off")}
            >
              Cut link
            </Button>
            <Button
              variant="outline"
              disabled={disabled}
              onClick={() => link("link_on")}
            >
              Restore link
            </Button>
          </div>
          <Separator />
          <Field orientation="horizontal">
            <Switch id="synthetic-ais" checked={ais} onCheckedChange={setAis} />
            <FieldLabel htmlFor="synthetic-ais">
              Synthetic contact has AIS
            </FieldLabel>
          </Field>
          <Button
            variant="outline"
            disabled={disabled}
            onClick={() => {
              setPlacing(placing ? null : { ais });
              onOpenChange(false);
            }}
          >
            <Settings2 />
            {placing ? "Cancel placement" : "Place synthetic contact on chart"}
          </Button>
          <p className="text-sm text-muted-foreground">
            The next chart click places a contact on a cable sample. It remains
            truth-only until a boat reports it.
          </p>
          <Separator />
          <Field>
            <FieldLabel htmlFor="reset-seed">Reset seed</FieldLabel>
            <input
              id="reset-seed"
              className="h-10 rounded-md border bg-transparent px-3 text-base"
              inputMode="numeric"
              type="number"
              step="1"
              value={seed}
              onChange={(e) => {
                setSeed(e.target.value);
                setResetReview(false);
              }}
            />
            <FieldDescription>
              A reset starts a fresh run and clears pending commands/injections.
            </FieldDescription>
          </Field>
          {!resetReview ? (
            <Button
              variant="outline"
              disabled={
                conn !== "live" ||
                seed.trim() === "" ||
                !Number.isSafeInteger(Number(seed))
              }
              onClick={() => setResetReview(true)}
            >
              Review simulation reset
            </Button>
          ) : (
            <Alert>
              <CircleAlert />
              <AlertTitle>Discard this run and reset?</AlertTitle>
              <AlertDescription>
                <p>
                  This cannot restore the current simulation state. Any run log
                  remains on the server.
                </p>
                <Button
                  disabled={conn !== "live"}
                  onClick={() => {
                    fire([{ cmd: "reset", seed: Number(seed) }]);
                    onOpenChange(false);
                  }}
                >
                  Reset simulation to seed {seed}
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {ack?.cmd === "inject" && (
            <p role="status" className="text-sm">
              {ack.ok
                ? ack.placed
                  ? `Server placed ${ack.placed} on ${ack.on}; not yet a shore observation.`
                  : "Server accepted injection."
                : `Rejected: ${ack.error ?? "unspecified reason"}`}
            </p>
          )}
        </FieldGroup>
      </DialogContent>
    </Dialog>
  );
}

interface Tamper {
  ok: boolean;
  error?: string;
  changed?: string;
  original?: { ok: boolean; messages: string[] };
  tampered?: { ok: boolean; messages: string[] };
}
export function EvidenceTools({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const snap = useStore((s) => s.snap);
  const [result, setResult] = useState<Tamper | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function check() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(apiUrl("/api/tamper-demo"));
      if (!response.ok) throw new Error((await response.text()).trim());
      setResult((await response.json()) as Tamper);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  const t = Math.floor(snap?.t ?? 0);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Evidence log</DialogTitle>
          <DialogDescription>
            Actual server report and integrity checks. No imagery or forensic
            admissibility is implied.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild>
            <a
              href={apiUrl(
                `/api/report.md?from=${Math.max(0, t - 1800)}&to=${t}`,
              )}
              download
            >
              Report · last 30 min
            </a>
          </Button>
          <Button variant="outline" asChild>
            <a href={apiUrl("/api/report.md")} download>
              Whole run
            </a>
          </Button>
        </div>
        <Button variant="outline" disabled={busy} onClick={() => void check()}>
          <FileCheck />
          {busy ? "Checking…" : "Tamper demo · change one character"}
        </Button>
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Report unavailable</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {result && (
          <Card>
            <CardHeader>
              <CardTitle>
                {result.ok ? "Server integrity check" : "Check unavailable"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {result.ok ? (
                <>
                  <p>Original: {result.original?.messages.join(" ")}</p>
                  <p>Changed in a copy: {result.changed}</p>
                  <p>
                    Copy verification: {result.tampered?.messages.join(" ")}
                  </p>
                </>
              ) : (
                <p>{result.error}</p>
              )}
            </CardContent>
          </Card>
        )}
        <p className="text-sm text-muted-foreground">
          Shows whether records changed after they were written, not whether a
          sensor was right. Requires real-sim run logging.
        </p>
      </DialogContent>
    </Dialog>
  );
}

export function ConnectionContext() {
  const snap = useStore((s) => s.snap);
  return (
    <Card className="gap-3 py-4">
      <CardHeader className="px-4">
        <CardTitle>Picture provenance</CardTitle>
        <CardDescription>
          Observation age is not connection status.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 px-4 text-sm">
        <p>
          Source: {snap?.source ?? "Not supplied"}. Seed:{" "}
          {snap?.seed ?? "Not supplied"}.
        </p>
        <p>
          {snap?.view === "truth"
            ? "Physical evaluator state, not shore knowledge."
            : "Reports actually delivered to shore. Stale boats stay at their last known position."}
        </p>
        <p className="text-muted-foreground">
          Simulation time {snap ? dur(snap.t) : "not supplied"}. Pausing the
          simulator does not mean the network is lost.
        </p>
      </CardContent>
    </Card>
  );
}
