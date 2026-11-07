// Retains the legacy StatusLine/CoverageBox logic using the live shadcn surfaces.
import { useState } from "react";
import { CircleAlert, Eye, Radio, WifiOff } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { BAND_WORD, coverageWords, segAges, segName, worst } from "../coverage";
import { dur, hm, utc } from "../format";
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
  const scene = useStore((s) => s.scene);
  const replayT = useStore((s) => s.replayT);
  const showReplay = useStore((s) => s.showReplay);
  const setPlacing = useStore((s) => s.setPlacing);
  return <div className="absolute left-3 top-3 z-10 flex max-h-[45%] w-96 max-w-[calc(100%_-_1.5rem)] flex-col gap-2 overflow-y-auto overscroll-contain" data-testid="chart-notices">
    {replayT !== null && snap && <Alert className="border-red-500/60"><Radio className="text-red-500" /><AlertTitle>REPLAY {utc(t0Of(snap), snap.t)}: what the shore knew then</AlertTitle><AlertDescription>The simulation keeps running. Commands are off while you watch. <Button variant="outline" size="sm" onClick={() => showReplay(null)}>Go live</Button></AlertDescription></Alert>}
    {conn !== "live" && <Alert variant={conn === "lost" ? "destructive" : "default"}><WifiOff /><AlertTitle>{conn === "lost" ? "FEED LOST" : "CONNECTING"} — {snap ? `display frozen at ${utc(t0Of(snap), snap.t)}` : "no data received"}</AlertTitle><AlertDescription>Last-known positions only. Commands disabled; queued unsent answers cancelled. Reconnecting automatically.</AlertDescription></Alert>}
    {(channel === "truth" || evalOn) && <Alert><Eye /><AlertTitle>{channel === "truth" ? "TRUTH VIEW — evaluator only" : "EVALUATOR COMPARISON ENABLED"}</AlertTitle><AlertDescription>{channel === "truth" ? "Not the shore picture. Operator decisions are disabled." : "Purple annotations use the separate /truth channel, not delivered shore observations."}</AlertDescription></Alert>}
    <SegmentList />
    {scene?.ais === false && <Alert><CircleAlert /><AlertTitle>No AIS ships: no AIS data on this laptop</AlertTitle><AlertDescription>Put the AIS clip at data/ais-clip-box.csv (not in git) and restart the server.</AlertDescription></Alert>}
    {placing && <Alert><CircleAlert /><AlertTitle>Click the chart to place a synthetic contact</AlertTitle><AlertDescription>Truth only until reported. <Button variant="outline" size="sm" onClick={() => setPlacing(null)}>Cancel placement</Button></AlertDescription></Alert>}
    <DigestSummary />
  </div>;
}

/** #88: details behind a toggle. Shore data only; the headline is the one thing always shown. */
export function StatusDetails() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  if (!snap) return null;
  const segments = scene ? Object.keys(scene.segments) : Object.keys(snap.seg_age);
  const watched = segments.filter((id) => snap.tasks[id]?.state === 1 && snap.tasks[id]?.owner).length;
  const atSea = snap.boats.filter((b) => !isDocked(b, scene) && b.mode !== "UNAVAILABLE").length;
  const count = (link: string) => snap.boats.filter((b) => b.link === link).length;
  const open = snap.decisions.filter((d) => d.state === "pending").length;
  const w = worst(segAges(snap, scene));
  return <div className="flex flex-wrap items-center gap-2 text-sm" aria-label="Status details">
    <Badge variant="outline">Cables watched {watched}/{segments.length}{watched < segments.length ? " · GAP" : ""}</Badge>
    <Badge variant="outline">Oldest visit {w ? (w.age === null ? `none · ${w.id}` : `${hm(w.age)} · ${w.id}`) : "n/a"}</Badge>
    <Badge variant="outline">At sea {atSea}/{snap.boats.length}</Badge>
    <Badge variant="outline">Links {count("direct")} direct · {count("peer")} via peer · {count("none")} none{count("none") ? " · NO PATH" : ""}</Badge>
    <Badge variant="outline">Decisions {open}{open ? " · WAITING" : ""}</Badge>
    <span className="text-muted-foreground">T+{dur(snap.t)} · {snap.source === "mock" ? "MOCK" : "Sim"} · {snap.view === "shore" ? "shore-reported" : "evaluator truth"}</span>
  </div>;
}

/** #88: the coverage headline in words, with a level shape so it reads without colour. */
export function CoverageLine() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  if (!snap) return <span className="text-sm text-muted-foreground">Waiting for the shore picture</span>;
  const ages = segAges(snap, scene);
  const target = scene?.revisit_target_s;
  const words = coverageWords(ages, target, snap.t, t0Of(snap));
  const ok = target !== undefined && ages.length > 0 && ages.every((a) => a.age !== null && a.age <= target);
  return <p className="flex min-w-0 items-center gap-2 font-medium" aria-label="Coverage headline">
    <span aria-hidden="true" className={`inline-block size-3 shrink-0 ${ok ? "rounded-full bg-emerald-400" : "rotate-45 bg-amber-400"}`} />
    <span className="min-w-0">{words}</span>
    <span className="shrink-0 text-sm font-normal text-muted-foreground">{snap.view === "shore" ? "shore-reported" : "evaluator truth"}</span>
  </p>;
}

/** Chart box top-left: the segment list behind one button (the sentence lives in the status row). */
export function SegmentList() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  const select = useStore((s) => s.selectSegment);
  const [open, setOpen] = useState(false);
  if (!snap) return null;
  const ages = segAges(snap, scene);
  if (!ages.length) return null;
  return <Card className="gap-0 py-2 shadow-md"><CardContent className="space-y-2 px-3 text-sm">
    <Button variant="ghost" size="sm" className="-ml-2" aria-expanded={open} onClick={() => setOpen(!open)}>
      {open ? "Hide segments" : `All ${ages.length} segments`}
    </Button>
    {open && <table className="w-full"><tbody>{ages.map((a) => (
      <tr key={a.id} className="cursor-pointer" title={segName(a.id)} onClick={() => select(a.id)}>
        <td className="pr-2 font-mono">{a.id}</td>
        <td className="text-right">{a.age === null ? "no visit confirmed" : hm(a.age)}</td>
        <td className="pl-2 text-muted-foreground">{BAND_WORD[a.band]}</td>
      </tr>))}</tbody></table>}
  </CardContent></Card>;
}
