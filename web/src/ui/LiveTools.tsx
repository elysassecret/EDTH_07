import { useEffect, useState } from "react";
import { CircleAlert, FileCheck, Settings2, SquareAlert, TriangleAlert } from "lucide-react";
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
import { endpoint, sortedAlerts, usv } from "../console-model";
import { dur, utc } from "../format";
import { apiUrl, useStore } from "../store";
import { t0Of, type Alert as AlertRecord, type Command } from "../types";

export function LevelIcon({ level }: { level: AlertRecord["level"] }) {
  const Icon = level === "alarm" ? TriangleAlert : level === "warning" ? CircleAlert : SquareAlert;
  const colour = level === "alarm" ? "text-red-300" : level === "warning" ? "text-orange-300" : "text-yellow-200";
  return <Icon aria-hidden="true" className={`size-5 shrink-0 ${colour}`} data-level={level} />;
}

export function PriorityAlert() {
  const snap = useStore((s) => s.snap);
  const conn = useStore((s) => s.conn);
  const channel = useStore((s) => s.channel);
  const send = useStore((s) => s.send);
  const setDigest = useStore((s) => s.setDigest);
  const top = sortedAlerts(snap?.alerts ?? []).find((a) => !a.ack && a.level !== "caution");
  if (!top) return null;
  return <section aria-label="Priority alert" role="alert" className="flex shrink-0 items-center gap-3 border-b px-4 py-2 text-sm">
    <LevelIcon level={top.level} /><strong>{top.level.toUpperCase()}</strong><span className="min-w-0 flex-1 truncate" title={top.text}>{top.text}</span>
    <Button variant="outline" size="sm" disabled={conn !== "live" || channel !== "shore"} onClick={() => { if (send({ cmd: "ack", id: top.id })) setDigest(true); }}>Acknowledge</Button>
  </section>;
}

export function LiveAlerts() {
  const snap = useStore((s) => s.snap);
  const conn = useStore((s) => s.conn);
  const channel = useStore((s) => s.channel);
  const send = useStore((s) => s.send);
  const setDigest = useStore((s) => s.setDigest);
  const [all, setAll] = useState(false);
  if (!snap) return null;
  const alerts = sortedAlerts(snap.alerts);
  return (
    <section className="space-y-2" aria-label="Alerts">
      <div className="flex items-center justify-between">
        <h3 className="font-medium">Alerts</h3>
        <Badge variant="outline">
          {alerts.filter((a) => !a.ack).length} unacknowledged
        </Badge>
      </div>
      {alerts.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No alerts in this picture.
        </p>
      )}
      {alerts.slice(0, all ? undefined : 8).map((a) => (
        <Alert
          key={a.id}
          variant={a.level === "alarm" ? "destructive" : "default"}
        >
          <LevelIcon level={a.level} />
          <AlertTitle className="flex flex-wrap justify-between gap-2">
            <span>{a.level.toUpperCase()}</span>
            <time className="font-normal text-muted-foreground">
              {utc(t0Of(snap), a.t)}
            </time>
          </AlertTitle>
          <AlertDescription>
            <p>{a.text}</p>
            {a.ack ? (
              <span>Acknowledged · condition may still be active</span>
            ) : (
              <Button
                variant="outline"
                size="sm"
                disabled={conn !== "live" || channel !== "shore"}
                onClick={() => {
                  if (send({ cmd: "ack", id: a.id })) setDigest(true);
                }}
              >
                Acknowledge
              </Button>
            )}
          </AlertDescription>
        </Alert>
      ))}
      {alerts.length > 8 && (
        <Button variant="ghost" size="sm" onClick={() => setAll(!all)}>
          {all ? "Show first 8" : `Show all ${alerts.length} alerts`}
        </Button>
      )}
    </section>
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
            Real simulation commands, not template scenarios. Every injected
            failure is labelled EXERCISE.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel>Boat</FieldLabel>
            <Select
              value={id === undefined ? undefined : String(id)}
              onValueChange={setBoat}
            >
              <SelectTrigger aria-label="Exercise boat">
                <SelectValue placeholder="Waiting for fleet" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  {ids.map((i) => (
                    <SelectItem key={i} value={String(i)}>
                      {usv(i)}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              disabled={disabled}
              onClick={() => {
                if (id !== undefined)
                  fire([{ cmd: "inject", kind: "battery_low", a: id }]);
              }}
            >
              Battery low
            </Button>
            <Button
              variant="outline"
              disabled={disabled}
              onClick={() => {
                if (id !== undefined)
                  fire([{ cmd: "inject", kind: "boat_off", a: id }]);
              }}
            >
              Switch off
            </Button>
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
          <Button
            variant="outline"
            disabled={disabled}
            title="Same boat and agent; no reset, teleport or battery recharge"
            onClick={() => {
              if (id !== undefined)
                fire([{ cmd: "inject", kind: "boat_restore", a: id }]);
            }}
          >
            Switch back on
          </Button>
          <p className="text-sm text-muted-foreground">
            Restores the same boat and agent, with battery as it was. A depleted
            boat stays depleted; shore reports resume only when delivered.
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
