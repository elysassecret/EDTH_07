// Owner: C. Feature 24: the headline number on screen, over the chart.
// "Oldest cable visit 1 h 32 min (seg:G:0)" and, past the target,
// "Cable zone gap open. No visit since 12:03Z". Never "coverage restored".
import { useState } from "react";
import { useStore } from "../store";
import { hhmm, hm } from "../format";
import { BAND_WORD, segAges, segName, worst, type Band } from "../coverage";
import { t0Of } from "../types";

const LEGEND: Band[] = ["recent", "due", "over", "none"];

export function CoverageBox() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  const [open, setOpen] = useState(false);
  if (!snap) return null;
  const ages = segAges(snap, scene);
  const w = worst(ages);
  if (!w) return null;
  const target = scene?.revisit_target_s;
  const t0 = t0Of(snap);
  const over = ages.filter((a) => a.band === "over" || a.band === "none");
  const gap = target !== undefined && over.length > 0;
  const source = snap.view === "truth" ? "truth (evaluator)" : "as reported to shore";
  return (
    <div className={`coverage ${gap ? "gap" : ""}`}>
      <div className="headline">
        {w.age === null ? (
          <>Oldest cable visit (shore-reported): <b>none since start</b> ({w.id})</>
        ) : (
          <>Oldest cable visit (shore-reported): <b>{hm(w.age)}</b> ({w.id})</>
        )}
      </div>
      {gap && (
        <div className="gap-line">
          Cable zone gap open.
          {w.age !== null && ` No visit since ${hhmm(t0, snap.t - w.age)}.`}
          {` ${over.length} of ${ages.length} segments over target or not visited.`}
        </div>
      )}
      <div className="sub">
        {target !== undefined ? `Revisit target ${hm(target)} (team setting, to be confirmed)` : "No revisit target set"}
        {" · "}{source}
      </div>
      <button className="more" onClick={() => setOpen((v) => !v)}>{open ? "Hide segments" : `All ${ages.length} segments`}</button>
      {open && (
        <table>
          <tbody>
            {ages.map((a) => (
              <tr key={a.id} title={segName(a.id)}>
                <td><span className={`band ${a.band}`} /></td>
                <td className="mono">{a.id}</td>
                <td className="num">{a.age === null ? "none" : hm(a.age)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {open && (
        <div className="legend">
          {LEGEND.map((b) => <span key={b}><span className={`band ${b}`} />{BAND_WORD[b]}</span>)}
        </div>
      )}
    </div>
  );
}
