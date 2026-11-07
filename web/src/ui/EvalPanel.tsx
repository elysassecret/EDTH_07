// Owner: C. Evaluator panel: the shore's belief next to the truth, for judges and the team.
// Off by default, never shown in operator mode (?operator). Data comes from /truth "eval"
// (server/evaluator.py); the operator's own picture stays /shore only.
import { useStore } from "../store";
import { dur, hm } from "../format";
import { Fps } from "./Fps";

const usv = (i: number) => `USV ${String(i).padStart(2, "0")}`;
const end = (n: number) => (n === 0 ? "shore" : usv(n));

export function EvalBanner() {
  const on = useStore((s) => s.evalOn);
  if (!on) return null;
  return (
    <div className="banner evaluator">
      EVALUATOR VIEW — not available to the operator · purple = truth
    </div>
  );
}

export function EvalPanel() {
  const on = useStore((s) => s.evalOn);
  const ev = useStore((s) => s.evalData);
  const card = useStore((s) => s.scorecard);
  if (!on) return null;
  if (!ev) return <section className="evalpanel"><h2>Evaluator view</h2><p className="muted">Waiting for /truth…</p></section>;
  const hidden = ev.contacts.filter((c) => !c.on_shore);
  return (
    <section className="evalpanel">
      <h2>Evaluator view · not available to the operator</h2>
      <Fps />
      {ev.cable_overdue ? (
        <div className="eval-headline">
          Cable overdue (truth): <b>{ev.cable_overdue.overdue_km.toFixed(1)} km</b> past the {hm(ev.cable_overdue.target_s)} target
          {" "}+ <b>{ev.cable_overdue.never_visited_km.toFixed(1)} km</b> never visited, of {ev.cable_overdue.total_km.toFixed(1)} km.
          <div className="muted">Console estimate from true sample visits; the scored number comes from eval/.</div>
        </div>
      ) : <p className="muted">Cable km overdue: real sim only.</p>}
      <table>
        <thead><tr><th>USV</th><th>shore data age</th><th>position off by</th><th>link true / shore</th></tr></thead>
        <tbody>
          {ev.boats.map((b) => (
            <tr key={b.id} className={b.true_link !== b.shore_link ? "diff" : ""}>
              <td>{usv(b.id)}</td>
              <td className="num">{b.shore_age_s === null ? "never heard" : dur(b.shore_age_s)}</td>
              <td className="num">{b.offset_m === null ? "n/a" : `${b.offset_m} m`}</td>
              <td>{b.true_link ?? "?"} / {b.shore_link ?? "none"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Contacts the shore does not have</h3>
      {hidden.length === 0 ? <p className="muted">None.</p> : (
        <ul>{hidden.map((c) => <li key={c.id}>{c.track ?? c.id} · {c.ais ? "AIS" : "no AIS"}</li>)}</ul>
      )}
      <h3>Links: truth differs from shore belief</h3>
      {ev.links.length === 0 ? <p className="muted">None.</p> : (
        <ul>{ev.links.map((l) => <li key={`${l.a}-${l.b}`}>{end(l.a)} – {end(l.b)}: true {l.true}, shore {l.shore}</li>)}</ul>
      )}
      <h3>Three-mode scorecard</h3>
      {card ? (
        <table>
          <thead><tr><th>mode</th><th>metric</th><th>median</th><th>range</th></tr></thead>
          <tbody>{card.rows.map((r) => (
            <tr key={`${r.mode}-${r.metric}`}><td>{r.mode}</td><td>{r.metric}</td>
              <td className="num">{r.median} {r.unit}</td><td className="num">{r.min}–{r.max}</td></tr>
          ))}</tbody>
        </table>
      ) : <p className="muted">Waits for eval/ (Franco): nothing shown until it sends real numbers.</p>}
      <h3>Cable revisit age: shore estimate / true</h3>
      <table>
        <tbody>
          {Object.entries(ev.seg_age).map(([k, v]) => (
            <tr key={k}>
              <td className="mono">{k}</td>
              <td className="num">{v.shore === null ? "none" : hm(v.shore)}</td>
              <td className="num">{v.true === null ? "never visited" : hm(v.true)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
