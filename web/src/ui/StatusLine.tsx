// Owner: C. U3 status line: five numbers that answer "is everything OK?" at a glance.
// All shore data. A chip that needs attention says so in words ("GAP", "WAITING"), not only colour.
import { useStore } from "../store";
import { hm } from "../format";
import { segAges, worst } from "../coverage";
import { isDocked } from "../roles";
import { openDecisions } from "./DecisionPanel";

function Chip({ label, value, bad, note }: { label: string; value: string; bad?: boolean; note?: string }) {
  return (
    <span className={`stat ${bad ? "bad" : "ok"}`} title={note}>
      <span className="stat-label">{label}</span> <b>{value}</b>{bad && <span className="stat-flag"> {note ?? "CHECK"}</span>}
    </span>
  );
}

export function StatusLine() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  if (!snap) return null;
  const segIds = scene ? Object.keys(scene.segments) : Object.keys(snap.seg_age);
  const watched = segIds.filter((k) => snap.tasks[k]?.state === 1 && snap.tasks[k]?.owner).length;
  const w = worst(segAges(snap, scene));
  const target = scene?.revisit_target_s;
  const oldBad = !!w && (w.age === null || (target !== undefined && w.age > target));
  const atSea = snap.boats.filter((b) => !isDocked(b, scene) && b.mode !== "UNAVAILABLE").length;
  const n = (l: string) => snap.boats.filter((b) => b.link === l).length;
  const open = openDecisions(snap).length;
  return (
    <div className="statusline" aria-label="Status">
      <Chip label="Cables watched" value={`${watched}/${segIds.length}`} bad={watched < segIds.length} note="GAP" />
      <Chip label="Oldest visit (shore)" value={w ? (w.age === null ? `none · ${w.id}` : `${hm(w.age)} · ${w.id}`) : "n/a"} bad={oldBad} note={w?.age === null ? "NO VISIT" : "OVER TARGET"} />
      <Chip label="At sea" value={`${atSea}/${snap.boats.length}`} />
      <Chip label="Links" value={`${n("direct")} direct · ${n("peer")} via peer · ${n("none")} none`} bad={n("none") > 0} note="NO PATH" />
      <Chip label="Decisions" value={String(open)} bad={open > 0} note="WAITING" />
    </div>
  );
}
