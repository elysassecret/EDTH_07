// Retains the legacy StatusLine/CoverageBox logic using the live shadcn surfaces.
import { CircleAlert, Eye, Settings2, WifiOff } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { segAges, worst } from "../coverage";
import { hhmm, hm, utc } from "../format";
import { DigestSummary } from "./LiveTools";
import { isDocked } from "../roles";
import { useStore } from "../store";
import { t0Of } from "../types";

export function ChartNotices() {
  const snap = useStore((s) => s.snap);
  const conn = useStore((s) => s.conn);
  const channel = useStore((s) => s.channel);
  const evalOn = useStore((s) => s.evalOn);
  const placing = useStore((s) => s.placing);
  const setPlacing = useStore((s) => s.setPlacing);
  const exercise = snap?.events.filter((event) => event.exercise).at(-1);
  return <div className="absolute left-3 top-3 z-10 flex max-h-[45%] w-96 max-w-[calc(100%_-_1.5rem)] flex-col gap-2 overflow-y-auto overscroll-contain" data-testid="chart-notices">
    {conn !== "live" && <Alert variant={conn === "lost" ? "destructive" : "default"}><WifiOff /><AlertTitle>{conn === "lost" ? "FEED LOST" : "CONNECTING"} — {snap ? `display frozen at ${utc(t0Of(snap), snap.t)}` : "no data received"}</AlertTitle><AlertDescription>Last-known positions only. Commands disabled; queued unsent answers cancelled. Reconnecting automatically.</AlertDescription></Alert>}
    {(channel === "truth" || evalOn) && <Alert><Eye /><AlertTitle>{channel === "truth" ? "TRUTH VIEW — evaluator only" : "EVALUATOR COMPARISON ENABLED"}</AlertTitle><AlertDescription>{channel === "truth" ? "Not the shore picture. Operator decisions are disabled." : "Purple annotations use the separate /truth channel, not delivered shore observations."}</AlertDescription></Alert>}
    <CoverageHeadline />
    {exercise && <Alert><Settings2 /><AlertTitle>EXERCISE — injected or scripted simulation condition</AlertTitle><AlertDescription>{utc(t0Of(snap), exercise.t)} · {exercise.text.replace(/^EXERCISE: /, "")}</AlertDescription></Alert>}
    {placing && <Alert><CircleAlert /><AlertTitle>Click the chart to place a synthetic contact</AlertTitle><AlertDescription>Truth only until reported. <Button variant="outline" size="sm" onClick={() => setPlacing(null)}>Cancel placement</Button></AlertDescription></Alert>}
    <DigestSummary />
  </div>;
}

export function FleetStatus() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  if (!snap) return <span className="text-sm text-muted-foreground">Waiting for fleet picture</span>;
  const segments = scene ? Object.keys(scene.segments) : Object.keys(snap.seg_age);
  const watched = segments.filter((id) => snap.tasks[id]?.state === 1 && snap.tasks[id]?.owner).length;
  const atSea = snap.boats.filter((b) => !isDocked(b, scene) && b.mode !== "UNAVAILABLE").length;
  const count = (link: string) => snap.boats.filter((b) => b.link === link).length;
  return <div className="flex flex-wrap items-center gap-2 text-sm" aria-label="Fleet status">
    <Badge variant="outline">Cables watched {watched}/{segments.length}{watched < segments.length ? " · GAP" : ""}</Badge>
    <Badge variant="outline">At sea {atSea}/{snap.boats.length}</Badge>
    <Badge variant="outline">Links {count("direct")} direct · {count("peer")} peer · {count("none")} none</Badge>
    <span className="text-muted-foreground">{snap.source === "mock" ? "MOCK" : "Sim"} · {snap.view === "shore" ? "shore-reported" : "evaluator truth"}</span>
  </div>;
}

export function CoverageHeadline() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  if (!snap) return null;
  const ages = segAges(snap, scene);
  const oldest = worst(ages);
  if (!oldest) return null;
  const target = scene?.revisit_target_s;
  const gaps = ages.filter((age) => age.band === "over" || age.band === "none");
  const gap = target !== undefined && gaps.length > 0;
  return <Card className="gap-0 py-3 shadow-md" aria-label="Coverage headline"><CardContent className="space-y-1 px-3 text-sm">
    <p className="font-medium">Oldest cable visit ({snap.view === "shore" ? "shore-reported" : "evaluator truth"}): {oldest.age === null ? "no visit confirmed" : hm(oldest.age)} ({oldest.id})</p>
    {gap && <p>Cable zone gap open.{oldest.age === null ? " Visit history not confirmed." : ` No visit since ${hhmm(t0Of(snap), snap.t - oldest.age)}.`} {gaps.length} of {ages.length} segments over target or unconfirmed.</p>}
    <p className="text-muted-foreground">{target === undefined ? "No revisit target supplied" : `Revisit target ${hm(target)}`}. Assignments do not close gaps.</p>
  </CardContent></Card>;
}
