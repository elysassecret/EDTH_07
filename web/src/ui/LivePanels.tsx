// Template presentation, operational data exclusively from the existing live store.
import { useState } from "react";
import { Activity, ArrowRight, Eye, PanelBottomClose, Radio, Ship } from "lucide-react";
import { LIMITS, maxSize } from "../panels";
import { Splitter, useLayout } from "./Panels";
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
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
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
  boatWhy,
  coverageRows,
  endpoint,
  eventCategory,
  linkText,
  reportAge,
  staleBoat,
  usv,
} from "../console-model";
import { segName } from "../coverage";
import { deg, dur, hhmm, hm, utc } from "../format";
import { roleText } from "../roles";
import { spreadText as spreadOf } from "../uncertainty";
import { useStore } from "../store";
import { t0Of } from "../types";
import { Fps } from "./Fps";
import { EscalateControl } from "./Escalate";

/** #88 item 6: one grey line with the reason the boats gave; the full text on hover. */
export function Why({ text }: { text: string }) {
  return <p className="truncate text-sm text-muted-foreground" title={text}>{text}</p>;
}

export function FleetOverview() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  const conn = useStore((s) => s.conn);
  const selected = useStore((s) => s.selected);
  const select = useStore((s) => s.select);
  if (!snap)
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>Waiting for fleet</EmptyTitle>
          <EmptyDescription>No observations have arrived.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  return (
    <div className="flex flex-col gap-2">
      {snap.boats.map((boat) => {
        const stale = staleBoat(boat, snap, scene, conn);
        const age = reportAge(boat, snap.t);
        const known = age !== null;
        return (
          <Card
            key={boat.id}
            data-testid={`fleet-${boat.id}`}
            data-stale={stale}
            className={`gap-2 py-3 ${selected === boat.id ? "ring-1 ring-ring" : ""} ${stale ? "bg-muted/40 text-muted-foreground" : ""}`}
          >
            <CardHeader className="gap-1 px-3">
              <div className="flex flex-wrap items-center justify-between gap-1">
                <CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="-ml-2"
                    aria-pressed={selected === boat.id}
                    onClick={() => select(boat.id)}
                  >
                    <Ship />
                    {usv(boat.id)}
                  </Button>
                </CardTitle>
                <Badge variant="outline">
                  {boat.mode === "SHADOWING"
                    ? "KEEP IN VIEW"
                    : boat.mode === "RETURNING"
                      ? "RTB"
                      : boat.mode === "UNAVAILABLE"
                        ? "OFF"
                        : boat.mode}
                </Badge>
              </div>
              <CardDescription className="break-words">
                {known
                  ? roleText(boat, scene)
                  : snap.launch
                    ? "Docked at Korsør · not switched on yet"
                    : "No report received"}
              </CardDescription>
              {snap.swaps?.[String(boat.id)] !== undefined && (
                <p className="text-sm font-medium">
                  Battery swap at Korsør · ready about {hhmm(t0Of(snap), snap.swaps[String(boat.id)])}
                </p>
              )}
              {known && boatWhy(boat, snap) && <Why text={boatWhy(boat, snap)} />}
            </CardHeader>
            <CardContent className="space-y-1 px-3 text-sm">
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground">Energy budget</span>
                <span>{known ? hm(boat.endurance_s) : "Not reported"}</span>
              </div>
              {known &&
                boat.must_return_by !== null &&
                boat.must_return_by !== undefined &&
                boat.mode !== "UNAVAILABLE" && (
                  <p className="text-muted-foreground">
                    Return by {hhmm(t0Of(snap), boat.must_return_by)}
                  </p>
                )}
            </CardContent>
            <CardFooter className="flex flex-wrap justify-between gap-1 px-3 text-sm">
              <span>{linkText(boat)}</span>
              <span className={stale ? "font-medium" : "text-muted-foreground"}>
                {conn !== "live"
                  ? "FROZEN"
                  : age === null
                    ? "NEVER HEARD"
                    : age <= 5
                      ? "LIVE"
                      : `${dur(age)} ago`}
              </span>
            </CardFooter>
          </Card>
        );
      })}
    </div>
  );
}

export function ContactOverview() {
  const snap = useStore((s) => s.snap);
  const selected = useStore((s) => s.selectedContact);
  const select = useStore((s) => s.selectContact);
  const [all, setAll] = useState(false);
  if (!snap) return null;
  return (
    <Card className="gap-3 py-4">
      <CardHeader className="px-4">
        <CardTitle>Contacts · {snap.contacts.length}</CardTitle>
        <CardDescription>
          {snap.view === "shore"
            ? "Only reports delivered to shore"
            : "TRUTH · evaluator tracks"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 px-4">
        {snap.contacts.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No contacts in this picture. Absence of a report is not proof of
            clear water.
          </p>
        ) : (
          snap.contacts.slice(0, all ? undefined : 20).map((contact) => (
            <Button
              key={contact.id}
              variant={selected === contact.id ? "secondary" : "outline"}
              className="h-auto w-full justify-between gap-2 whitespace-normal py-3 text-left"
              onClick={() => select(contact.id)}
            >
              <span className="min-w-0 break-words">
                {contact.track ?? contact.id}
                <span className="block text-sm text-muted-foreground">
                  {contact.source ?? (contact.ais ? "AIS" : "camera")} · last
                  seen {dur(snap.t - contact.last_seen)} ago
                </span>
                {contact.why && <Why text={contact.why} />}
              </span>
              <Badge variant="outline">{contact.ais ? "AIS" : "NO AIS"}</Badge>
            </Button>
          ))
        )}
        {snap.contacts.length > 20 && (
          <Button variant="ghost" size="sm" onClick={() => setAll(!all)}>
            {all
              ? "Show first 20"
              : `Show all ${snap.contacts.length} contacts`}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

export function SelectedContext() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  const boatId = useStore((s) => s.selected);
  const contactId = useStore((s) => s.selectedContact);
  const segmentId = useStore((s) => s.selectedSegment);
  if (!snap)
    return (
      <p className="text-sm text-muted-foreground">Waiting for observations.</p>
    );
  const boat = snap.boats.find((b) => b.id === boatId);
  const contact = snap.contacts.find((c) => c.id === contactId);
  if (boat) {
    const age = reportAge(boat, snap.t);
    const links = snap.links.filter((l) => l.a === boat.id || l.b === boat.id);
    return (
      <Card className="gap-4 py-4">
        <CardHeader className="px-4">
          <CardTitle>{usv(boat.id)}</CardTitle>
          <CardDescription>{roleText(boat, scene)}</CardDescription>
          {boatWhy(boat, snap) && <Why text={boatWhy(boat, snap)} />}
        </CardHeader>
        <CardContent className="space-y-4 px-4">
          <Badge variant="outline">
            {snap.view === "shore" ? "SHORE-REPORTED STATE" : "EVALUATOR TRUTH"}
          </Badge>
          <dl className="grid grid-cols-[1fr_1fr] gap-3 text-sm">
            <dt className="text-muted-foreground">Last report</dt>
            <dd>
              {age === null
                ? "Never heard"
                : `${utc(t0Of(snap), boat.last_heard)} · ${dur(age)} ago`}
            </dd>
            {spreadOf(snap, scene, "boat", usv(boat.id)) && (
              <>
                <dt className="text-muted-foreground">Could be within</dt>
                <dd>{spreadOf(snap, scene, "boat", usv(boat.id))}</dd>
              </>
            )}
            <dt className="text-muted-foreground">Link</dt>
            <dd>{linkText(boat)}</dd>
            <dt className="text-muted-foreground">Energy budget</dt>
            <dd>{age === null ? "Not reported" : hm(boat.endurance_s)}</dd>
            <dt className="text-muted-foreground">Reported course</dt>
            <dd>
              {boat.hdg === undefined || age === null
                ? "Not reported"
                : deg(boat.hdg)}
            </dd>
            <dt className="text-muted-foreground">Reported speed</dt>
            <dd>
              {boat.sog === undefined || age === null
                ? "Not reported"
                : `${(boat.sog / 514.444).toFixed(1)} kn`}
            </dd>
          </dl>
          <p className="text-sm text-muted-foreground">
            Energy is a cruise-equivalent model estimate, not measured hull
            endurance.
          </p>
          <Separator />
          <p className="flex items-center gap-2 font-medium">
            <Radio className="size-4" />
            Reported links
          </p>
          {links.length ? (
            <ul className="space-y-2 text-sm">
              {links.map((l, i) => (
                <li key={`${l.a}-${l.b}-${i}`}>
                  {endpoint(l.a)} — {endpoint(l.b)}:{" "}
                  <Badge variant="outline">{l.state.toUpperCase()}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No link report supplied.
            </p>
          )}
          <p className="text-sm text-muted-foreground">
            A docked boat is not the shore node. A peer cut can coexist with a
            working direct shore link.
          </p>
          <p className="font-medium">Assigned tasks</p>
          <ul className="space-y-1 break-words font-mono text-sm">
            {boat.roles.map((task) => (
              <li key={task}>{task}{snap.tasks[task]?.why ? <span className="block font-sans text-muted-foreground">{snap.tasks[task].why}</span> : null}</li>
            ))}
          </ul>
        </CardContent>
      </Card>
    );
  }
  if (contact)
    return (
      <Card className="gap-4 py-4">
        <CardHeader className="px-4">
          <CardTitle>{contact.track ?? contact.id}</CardTitle>
          <CardDescription>
            {contact.source ?? (contact.ais ? "AIS" : "camera")} · delivered
            evidence
          </CardDescription>
          {contact.why && <Why text={contact.why} />}
        </CardHeader>
        <CardContent className="space-y-4 px-4">
          <Badge variant="outline">
            {contact.ais ? "AIS REPORT" : "CAMERA ONLY · NO AIS MATCH"}
          </Badge>
          <p className="text-sm">
            Last observed {utc(t0Of(snap), contact.last_seen)} ·{" "}
            {dur(snap.t - contact.last_seen)} ago.
            {spreadOf(snap, scene, "contact", contact.track) &&
              ` Could be within ${spreadOf(snap, scene, "contact", contact.track)} of that place.`}
          </p>
          <p className="text-sm">
            Seen by{" "}
            {contact.seen_by.length
              ? contact.seen_by.map(usv).join(", ")
              : "no recent observer"}
            .{" "}
            {contact.watcher
              ? `Watcher: ${usv(contact.watcher)}.`
              : "No watcher reported."}
          </p>
          <p className="text-sm text-muted-foreground">
            {contact.name_status ?? "Name not supplied"} ·{" "}
            {contact.anchor_status ?? "Anchor evidence not supplied"}. Missing
            AIS does not establish intent. Look flags indicate a simulated
            observation, not verified identity.
          </p>
          {snap.view === "shore" && <EscalateControl contact={contact} snap={snap} />}
          <Empty>
            <EmptyHeader>
              <EmptyMedia variant="icon">
                <Eye />
              </EmptyMedia>
              <EmptyTitle>Image evidence not supplied</EmptyTitle>
              <EmptyDescription>
                No camera frames are provided by this simulator.
              </EmptyDescription>
            </EmptyHeader>
          </Empty>
        </CardContent>
      </Card>
    );
  if (segmentId) {
    const row = coverageRows(snap, scene).find((r) => r.id === segmentId);
    const task = snap.tasks[segmentId];
    return (
      <Card className="gap-4 py-4">
        <CardHeader className="px-4">
          <CardTitle>{segmentId}</CardTitle>
          <CardDescription>{segName(segmentId)}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 px-4">
          <Badge variant="outline">
            {row?.age === null || !row
              ? "UNKNOWN / UNVISITED"
              : "OBSERVATION AVAILABLE"}
          </Badge>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <dt className="text-muted-foreground">Worst sample age</dt>
            <dd>{row?.age === null || !row ? "Unknown" : dur(row.age)}</dd>
            <dt className="text-muted-foreground">Target</dt>
            <dd>
              {scene?.revisit_target_s === undefined
                ? "Not supplied"
                : hm(scene.revisit_target_s)}
            </dd>
            <dt className="text-muted-foreground">Assigned owner</dt>
            <dd>{task?.owner ? usv(task.owner) : "None reported"}</dd>
          </dl>
          <p className="text-sm text-muted-foreground">
            Ownership does not credit a visit. Unknown coverage is not zero age.
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Ship />
        </EmptyMedia>
        <EmptyTitle>
          {boatId !== null || contactId || segmentId
            ? "Selection not in this picture"
            : "Select an entity"}
        </EmptyTitle>
        <EmptyDescription>
          Choose a vessel, contact or coverage segment. No truth data is
          substituted for missing reports.
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}

export function EventTimeline({ height, room }: { height: number; room: number }) {
  const snap = useStore((s) => s.snap);
  const setPanel = useLayout((s) => s.set);
  const showPanel = useLayout((s) => s.show);
  const expanded = height > LIMITS.timeline.min;
  const [filter, setFilter] = useState("All events");
  const [story, setStory] = useState(false);
  const rows = story
    ? (snap?.narration ?? []).map((e) => ({
        ...e,
        kind: "narration",
        exercise: false,
      }))
    : (snap?.events ?? []);
  const matching = [...rows]
    .reverse()
    .filter((e) => filter === "All events" || eventCategory(e) === filter);
  return (
    <section className="relative shrink-0 border-t" aria-label="Event timeline">
      <Splitter id="timeline" edge="top" size={height} room={room} />
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2">
        <span className="flex items-center gap-2 text-sm font-medium">
          <Activity className="size-4" />
          Event timeline<Badge variant="secondary">{rows.length}</Badge>
        </span>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" size="sm" onClick={() => setStory(!story)}>
            {story ? "Show event log" : "What changed"}
          </Button>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger
              size="sm"
              aria-label="Filter event timeline"
              className="w-36"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {[
                  "All events",
                  "Coordination",
                  "Command",
                  "Observation",
                  "Coverage",
                  "Exercise",
                ].map((name) => (
                  <SelectItem key={name} value={name}>
                    {name}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setPanel("timeline", {
                size: expanded ? LIMITS.timeline.min : Math.min(240, maxSize("timeline", room)),
                open: true,
              })
            }
            aria-expanded={expanded}
          >
            {expanded ? "Collapse" : "Expand"}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-8"
            aria-label="Collapse event timeline"
            title="Collapse to a thin bar"
            onClick={() => showPanel("timeline", false)}
          >
            <PanelBottomClose />
          </Button>
        </div>
      </div>
      <div
        className="overflow-y-auto overscroll-contain border-t px-4"
        style={{ height }}
      >
        {matching.length ? (
          matching.slice(0, 60).map((e, i) => (
            <div
              className="flex gap-3 border-b py-2 text-sm last:border-0"
              key={`${e.t}-${e.kind}-${i}`}
            >
              <time className="shrink-0">{utc(t0Of(snap), e.t)}</time>
              <span className="hidden w-24 shrink-0 text-muted-foreground md:block">
                {eventCategory(e)}
              </span>
              <span className="min-w-0 break-words text-muted-foreground">
                {e.text}
              </span>
            </div>
          ))
        ) : (
          <p className="py-2 text-sm text-muted-foreground">
            {story ? "No reported changes." : "No matching events."}
          </p>
        )}
      </div>
    </section>
  );
}

export function EvaluatorWorkspace() {
  const on = useStore((s) => s.evalOn);
  const ev = useStore((s) => s.evalData);
  const card = useStore((s) => s.scorecard);
  if (!on) return null;
  return (
    <Card className="gap-3 border-dashed py-4">
      <CardHeader className="px-4">
        <CardTitle>Evaluator · truth only</CardTitle>
        <CardDescription>
          Not available to the operator. Purple map annotations are evaluator
          truth.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 overflow-x-auto px-4 text-sm">
        <Fps />
        {!ev ? (
          <p>Waiting for /truth…</p>
        ) : (
          <>
            {ev.cable_overdue ? (
              <p>
                <strong>
                  {ev.cable_overdue.overdue_km.toFixed(1)} km overdue
                </strong>{" "}
                + {ev.cable_overdue.never_visited_km.toFixed(1)} km never
                visited, of {ev.cable_overdue.total_km.toFixed(1)} km. Target{" "}
                {hm(ev.cable_overdue.target_s)}. Truth estimate; final scored
                figures come from eval/.
              </p>
            ) : (
              <p>Physical coverage metric not supplied.</p>
            )}
            <table className="w-full text-left">
              <caption className="mb-2 text-left font-medium">
                True versus shore-reported fleet
              </caption>
              <thead>
                <tr className="border-b text-muted-foreground">
                  <th>Boat</th>
                  <th>Report age</th>
                  <th>Offset</th>
                </tr>
              </thead>
              <tbody>
                {ev.boats.map((b) => (
                  <tr key={b.id} className="border-b">
                    <td className="py-2">{usv(b.id)}</td>
                    <td>
                      {b.shore_age_s === null
                        ? "Never heard"
                        : dur(b.shore_age_s)}
                    </td>
                    <td>
                      {b.offset_m === null ? "Unknown" : `${b.offset_m} m`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p>
              Contacts unknown to shore:{" "}
              {ev.contacts
                .filter((c) => !c.on_shore)
                .map((c) => c.track ?? c.id)
                .join(", ") || "None"}
              .
            </p>
            <ul className="space-y-1">
              {ev.links.map((l) => (
                <li key={`${l.a}-${l.b}`}>
                  {endpoint(l.a)} — {endpoint(l.b)}: true {l.true}, shore{" "}
                  {l.shore}
                </li>
              ))}
            </ul>
            <table className="w-full text-left">
              <caption className="mb-2 text-left font-medium">
                Cable age · shore / truth
              </caption>
              <tbody>
                {Object.entries(ev.seg_age).map(([id, age]) => (
                  <tr key={id} className="border-b">
                    <td className="py-2">{id}</td>
                    <td>{age.shore === null ? "Unknown" : dur(age.shore)}</td>
                    <td>{age.true === null ? "Unvisited" : dur(age.true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
        <Separator />
        <p className="font-medium">Three-mode scorecard</p>
        {card ? (
          <>
            <p>
              {card.source} · seeds {card.seeds.join(", ")}
            </p>
            {card.preliminary && (
              <Alert>
                <AlertTitle>PRELIMINARY</AlertTitle>
                <AlertDescription>
                  The evaluator marks these results as preliminary, not final
                  accepted figures.
                </AlertDescription>
              </Alert>
            )}
            <table className="w-full text-left">
              <thead>
                <tr>
                  <th>Mode / metric</th>
                  <th>Median</th>
                  <th>Range</th>
                </tr>
              </thead>
              <tbody>
                {card.rows.map((r) => (
                  <tr key={`${r.mode}-${r.metric}`} className="border-b">
                    <td className="py-2">
                      {r.mode} / {r.metric}
                    </td>
                    <td>
                      {r.median} {r.unit}
                    </td>
                    <td>
                      {r.min}–{r.max}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <p className="text-muted-foreground">
            Waiting for eval/ scorecard. No results are invented.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function ContextLink({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <Button
      variant="outline"
      className="w-full justify-between"
      onClick={onClick}
    >
      {label}
      <ArrowRight />
    </Button>
  );
}
