import { useEffect, useRef, useState } from "react";
import { Activity, ArrowRight, CircleAlert, Eye, Undo2 } from "lucide-react";
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
import { Separator } from "@/components/ui/separator";
import {
  actionsFor,
  canOperate,
  decisionRevision,
  pendingDecisions,
  usv,
  type DecisionAction,
} from "../console-model";
import { dur } from "../format";
import { useStore } from "../store";
import type { Decision } from "../types";

const WORD: Record<DecisionAction, string> = {
  approve: "Approve",
  decline: "Decline",
  confirm: "Confirm",
  stop: "Stop",
};
const KEY: Record<DecisionAction, string> = {
  approve: "A",
  decline: "D",
  confirm: "C",
  stop: "S",
};
type Attempt = {
  action: DecisionAction;
  phase:
    "queued" | "sent" | "accepted" | "unconfirmed" | "rejected" | "cancelled";
  message?: string;
};
type Review = { id: string; action: DecisionAction; revision: string };
const blocks = (a: Attempt | undefined) =>
  !!a && ["queued", "sent", "accepted", "unconfirmed"].includes(a.phase);

export function useDecisionFlow() {
  const snap = useStore((s) => s.snap);
  const conn = useStore((s) => s.conn);
  const channel = useStore((s) => s.channel);
  const ack = useStore((s) => s.lastAck);
  const held = useStore((s) => s.held);
  const answering = useStore((s) => s.answering);
  const transportError = useStore((s) => s.commandError);
  const [review, setReview] = useState<Review | null>(null);
  const [attempts, setAttempts] = useState<Record<string, Attempt>>({});
  const [preview, setPreview] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());
  const last = useRef<{ seed?: number; t: number } | null>(null);

  useEffect(() => {
    if (!snap) return;
    if (
      last.current &&
      (snap.t < last.current.t || snap.seed !== last.current.seed)
    ) {
      setAttempts({});
      setReview(null);
      setPreview(null);
    }
    last.current = { seed: snap.seed, t: snap.t };
  }, [snap]);
  useEffect(() => {
    useStore.getState().setHoverDecision(review?.id ?? preview);
  }, [preview, review]);
  useEffect(() => {
    if (!held) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 200);
    return () => window.clearInterval(timer);
  }, [held]);
  useEffect(() => {
    if (!answering) return;
    setAttempts((old) =>
      old[answering]
        ? { ...old, [answering]: { ...old[answering], phase: "sent" } }
        : old,
    );
    const timer = window.setTimeout(() => {
      setAttempts((old) =>
        old[answering]?.phase === "sent"
          ? { ...old, [answering]: { ...old[answering], phase: "unconfirmed" } }
          : old,
      );
      // Keep this attempt blocked against duplicate retries, but release other tasks.
      if (useStore.getState().answering === answering)
        useStore.setState({ answering: null });
    }, 10000);
    return () => window.clearTimeout(timer);
  }, [answering]);
  useEffect(() => {
    if (!ack?.id) return;
    const id = ack.id;
    setAttempts((old) =>
      old[id] && old[id].action === ack.cmd
        ? {
            ...old,
            [id]: {
              ...old[id],
              phase: ack.ok ? "accepted" : "rejected",
              message: ack.error,
            },
          }
        : old,
    );
  }, [ack]);
  useEffect(() => {
    if (conn === "live") return;
    setAttempts((old) =>
      Object.fromEntries(
        Object.entries(old).map(([id, a]) => [
          id,
          a.phase === "queued"
            ? { ...a, phase: "cancelled" as const }
            : ["sent", "accepted"].includes(a.phase)
              ? { ...a, phase: "unconfirmed" as const }
              : a,
        ]),
      ),
    );
  }, [conn]);
  useEffect(() => {
    if (
      !held &&
      !answering &&
      transportError?.startsWith("Queued answer cancelled")
    ) {
      setAttempts((old) =>
        Object.fromEntries(
          Object.entries(old).map(([id, a]) => [
            id,
            a.phase === "queued" ? { ...a, phase: "cancelled" as const } : a,
          ]),
        ),
      );
    }
  }, [held, answering, transportError]);
  useEffect(
    () => () => {
      useStore.getState().undoAnswer();
    },
    [],
  );

  function begin(d: Decision, action: DecisionAction) {
    const state = useStore.getState();
    if (
      !state.snap ||
      !canOperate(state.conn, state.channel) ||
      state.held ||
      blocks(attempts[d.id])
    )
      return;
    setReview({ id: d.id, action, revision: decisionRevision(d, state.snap) });
  }
  function authorize() {
    const state = useStore.getState();
    const d = state.snap?.decisions.find((item) => item.id === review?.id);
    if (
      !review ||
      !d ||
      !state.snap ||
      d.state !== "pending" ||
      !canOperate(state.conn, state.channel) ||
      blocks(attempts[d.id]) ||
      decisionRevision(d, state.snap) !== review.revision
    )
      return;
    const command = { cmd: review.action, id: d.id } as const;
    const ok =
      review.action === "confirm"
        ? state.send(command)
        : state.holdAnswer(command, `${WORD[review.action]}: ${d.text}`);
    if (ok && review.action === "confirm")
      useStore.setState({ answering: d.id });
    setAttempts((old) => ({
      ...old,
      [d.id]: {
        action: review.action,
        phase: ok
          ? review.action === "confirm"
            ? "sent"
            : "queued"
          : "cancelled",
      },
    }));
    if (ok) setReview(null);
  }
  function undo() {
    const id = held && "id" in held.cmd ? held.cmd.id : null;
    if (useStore.getState().undoAnswer() && id)
      setAttempts((old) =>
        old[id] ? { ...old, [id]: { ...old[id], phase: "cancelled" } } : old,
      );
  }
  return {
    snap,
    conn,
    channel,
    review,
    setReview,
    attempts,
    begin,
    authorize,
    undo,
    held,
    preview,
    setPreview,
    remaining: held ? Math.max(0, Math.ceil((held.until - now) / 1000)) : 0,
  };
}
export type DecisionFlow = ReturnType<typeof useDecisionFlow>;

export function QueuedAnswer({ flow }: { flow: DecisionFlow }) {
  if (!flow.held) return null;
  return <div className="fixed bottom-14 left-1/2 z-[60] w-96 max-w-[calc(100%_-_1.5rem)] -translate-x-1/2 shadow-xl">
    <Alert role="status"><Undo2 /><AlertTitle>Not sent · {flow.remaining}s undo window</AlertTitle><AlertDescription><p>{flow.held.label}</p><Button size="sm" variant="outline" onClick={flow.undo}>Undo queued answer</Button></AlertDescription></Alert>
  </div>;
}

export function DecisionWorkspace({ flow }: { flow: DecisionFlow }) {
  const { snap, attempts, held } = flow;
  const localError = useStore((s) => s.commandError);
  const open = pendingDecisions(snap);
  const history =
    snap?.decisions
      .filter((d) => d.state !== "pending")
      .slice(-8)
      .reverse() ?? [];
  const locked = !canOperate(flow.conn, flow.channel);
  return (
    <section className="space-y-3" aria-label="Decisions for the watch officer">
      {localError && (
        <Alert>
          <CircleAlert />
          <AlertTitle>Command transport</AlertTitle>
          <AlertDescription>{localError}</AlertDescription>
        </Alert>
      )}
      {open.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No decisions waiting. No proposal is manufactured from template data.
        </p>
      )}
      {open.map((d) => {
        const contact = snap?.contacts.find(
          (c) => c.id === d.task || `contact:${c.track}` === d.task,
        );
        const attempt = attempts[d.id];
        return (
          <Card
            key={d.id}
            tabIndex={0}
            role="article"
            aria-label={`Decision ${d.id}. Focus this card for decision shortcuts.`}
            className="max-h-[max(18rem,min(36rem,calc(100dvh_-_25rem)))] gap-3 overflow-hidden py-3"
            onKeyDown={(event) => {
              if (
                event.target !== event.currentTarget ||
                event.altKey ||
                event.ctrlKey ||
                event.metaKey ||
                locked
              )
                return;
              const action = actionsFor(d).find(
                (a) => KEY[a] === event.key.toUpperCase(),
              );
              if (action) {
                event.preventDefault();
                flow.begin(d, action);
              }
            }}
          >
            <CardHeader className="gap-2 px-4">
              <div className="flex flex-wrap justify-between gap-2">
                <Badge variant="secondary">
                  {d.tier === "delegated" ? "DELEGATED" : "HELD"}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Waiting {dur((snap?.t ?? d.t) - d.t)}
                </span>
              </div>
              <CardTitle className="leading-relaxed">{d.text}</CardTitle>
              <CardDescription>
                {d.id}
                {d.boat ? ` · ${usv(d.boat)}` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent className="min-h-0 space-y-3 overflow-y-auto px-4 text-sm">
              <p>
                {d.tier === "delegated"
                  ? "Already running under a standing order; you may confirm or request a stop."
                  : "The boat waits for authorization. No answer means no additional action."}
              </p>
              {contact && (
                <p className="text-muted-foreground">
                  {contact.track}:{" "}
                  {contact.ais ? "AIS report" : "camera only, no AIS match"} ·
                  last seen{" "}
                  {dur((snap?.t ?? contact.last_seen) - contact.last_seen)} ago
                  ·{" "}
                  {contact.seen_by.map(usv).join(", ") || "no recent observer"}.
                  A cue for a look, not an intent claim.
                </p>
              )}
              <Separator />
              <p className="text-muted-foreground">
                Authorization is not execution. Only a delivered observation
                changes coverage.
              </p>
              {d.route && (
                <Button
                  variant="outline"
                  size="sm"
                  aria-pressed={flow.preview === d.id}
                  onClick={() =>
                    flow.setPreview(flow.preview === d.id ? null : d.id)
                  }
                >
                  <Eye />
                  {flow.preview === d.id
                    ? "Hide proposed route"
                    : "Preview proposed route"}
                  <ArrowRight />
                </Button>
              )}
              {locked && (
                <Alert>
                  <CircleAlert />
                  <AlertTitle>Controls unavailable</AlertTitle>
                  <AlertDescription>
                    {flow.channel === "truth"
                      ? "Evaluator view is read-only for operator decisions."
                      : "Fresh feed unavailable. Inspect last-known state only."}
                  </AlertDescription>
                </Alert>
              )}
              {attempt && (
                <Alert role="status">
                  <Activity />
                  <AlertTitle>
                    {attempt.phase === "queued"
                      ? "Queued locally · not sent"
                      : attempt.phase === "sent"
                        ? "Sent · waiting for server"
                        : attempt.phase === "accepted"
                          ? "Accepted by server · await boat report"
                          : attempt.phase === "unconfirmed"
                            ? "DELIVERY UNCONFIRMED"
                            : attempt.phase === "rejected"
                              ? "Rejected by server"
                              : "Cancelled before transmission"}
                  </AlertTitle>
                  <AlertDescription>
                    {attempt.message ??
                      (attempt.phase === "unconfirmed"
                        ? "Do not assume execution or retry automatically. Inspect the latest delivered decision state."
                        : "Server acceptance and boat acknowledgment are different. Neither means an observation is complete.")}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
            <CardFooter className="flex flex-wrap gap-2 px-4">
              {actionsFor(d).map((action) => (
                <Button
                  key={action}
                  variant={
                    action === "stop" || action === "decline"
                      ? "outline"
                      : "default"
                  }
                  disabled={locked || !!held || blocks(attempt)}
                  onClick={() => flow.begin(d, action)}
                >
                  {action === "approve" ? "Review & approve" : WORD[action]}
                  <kbd className="ml-1 text-xs opacity-70">{KEY[action]}</kbd>
                </Button>
              ))}
            </CardFooter>
          </Card>
        );
      })}
      {history.length > 0 && (
        <Card className="gap-3 py-4">
          <CardHeader className="px-4">
            <CardTitle>Reported decision history</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 px-4 text-sm">
            {history.map((d) => (
              <div key={d.id} className="border-b pb-2 last:border-0">
                <p>{d.text}</p>
                <p className="text-muted-foreground">
                  {d.state === "delivered"
                    ? "Boat acknowledgment delivered; execution is not implied"
                    : d.state === "approved"
                      ? "Approved by operator; boat delivery not yet confirmed"
                      : d.state === "stopped"
                        ? "Stop requested; boat delivery not yet confirmed"
                        : d.state === "confirmed"
                          ? "Confirmed by operator"
                          : d.state}{" "}
                  · {d.id}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </section>
  );
}

export function DecisionReview({ flow }: { flow: DecisionFlow }) {
  const authorizeButton = useRef<HTMLButtonElement>(null);
  const d = flow.snap?.decisions.find((item) => item.id === flow.review?.id);
  const valid =
    !!d &&
    !!flow.snap &&
    !!flow.review &&
    d.state === "pending" &&
    decisionRevision(d, flow.snap) === flow.review.revision;
  const locked = !canOperate(flow.conn, flow.channel);
  return (
    <Dialog
      open={flow.review !== null}
      onOpenChange={(open) => {
        if (!open) flow.setReview(null);
      }}
    >
      <DialogContent className="max-h-[85dvh] overflow-y-auto" onOpenAutoFocus={(event) => {
        if (authorizeButton.current && !authorizeButton.current.disabled) {
          event.preventDefault();
          authorizeButton.current.focus();
        }
      }}>
        <DialogHeader>
          <DialogTitle>
            {flow.review
              ? `${WORD[flow.review.action]} proposed action`
              : "Review decision"}
          </DialogTitle>
          <DialogDescription>
            {flow.review?.id} · live delivered decision, not template data
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 text-sm">
          <Badge variant="outline">
            {d?.tier === "delegated"
              ? "DELEGATED TASK"
              : "HELD FOR AUTHORIZATION"}
          </Badge>
          <p className="font-medium">
            {d?.text ?? "This decision is no longer in the picture."}
          </p>
          <p>
            Acting boat: {d?.boat ? usv(d.boat) : "Not reported"}. Task:{" "}
            {d?.task ?? "Not reported"}.
          </p>
          <Alert>
            <CircleAlert />
            <AlertTitle>Authorization is not completion</AlertTitle>
            <AlertDescription>
              Confirm goes to the server immediately. Approve, Decline and Stop
              wait in a five-second local undo window before transmission.
              Delivery is known only from the reported acknowledgment.
            </AlertDescription>
          </Alert>
          {!valid && (
            <Alert variant="destructive">
              <AlertTitle>Decision changed or expired</AlertTitle>
              <AlertDescription>
                Return to the latest picture and review again. Nothing has been
                sent.
              </AlertDescription>
            </Alert>
          )}
          {locked && (
            <p role="status">
              Fresh shore feed required. Nothing can be authorized here.
            </p>
          )}
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Back to review</Button>
          </DialogClose>
          <Button
            ref={authorizeButton}
            disabled={!valid || locked || !!flow.held}
            onClick={flow.authorize}
          >
            Authorize & send
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
