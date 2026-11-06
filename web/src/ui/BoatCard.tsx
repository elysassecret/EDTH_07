// Owner: C. Feature 18: one card per USV. Role, mode chip, battery as time left and
// must-return-by, link, data age. Stale boats are greyed and say when they were last heard.
import { useStore } from "../store";
import { ContactList } from "./ContactList";
import { deg, dur, hm, hhmm } from "../format";
import { t0Of, type Boat, type Snapshot } from "../types";

const LIVE_S = 5; // reports younger than this read "LIVE"

const MODE_WORD: Record<string, string> = {
  PATROL: "PATROL", ECO: "ECO", SENTINEL: "SENTINEL", DORMANT: "DORMANT",
  SHADOWING: "KEEP IN VIEW", RETURNING: "RTB", UNAVAILABLE: "OFF",
};

function linkText(b: Boat): string {
  if (b.link === "direct") return "Direct to shore";
  if (b.link === "peer") return b.via ? `Via USV ${String(b.via).padStart(2, "0")}` : "Via peer";
  return "NO LINK";
}

export function BoatCard({ b, snap, staleAfter }: { b: Boat; snap: Snapshot; staleAfter: number }) {
  const selected = useStore((s) => s.selected);
  const select = useStore((s) => s.select);
  const frozen = useStore((s) => s.conn) !== "live";
  const t0 = t0Of(snap);
  const age = snap.t - b.last_heard;
  const neverHeard = b.heard === false;
  const stale = frozen || neverHeard || age > staleAfter;
  const mustReturn = b.must_return_by;
  const returnDue = mustReturn !== null && mustReturn !== undefined && mustReturn <= snap.t && b.mode !== "RETURNING" && b.mode !== "UNAVAILABLE";

  return (
    <button
      className={`card ${stale ? "stale" : ""} ${selected === b.id ? "selected" : ""}`}
      onClick={() => select(selected === b.id ? null : b.id)}
      aria-pressed={selected === b.id}
    >
      <div className="card-head">
        <span className="id">USV {String(b.id).padStart(2, "0")}</span>
        <span className={`chip mode-${b.mode}`}>{MODE_WORD[b.mode] ?? b.mode}</span>
        <span className={`age ${stale ? "old" : ""}`}>
          {frozen ? "FROZEN" : neverHeard ? "NEVER HEARD" : age <= LIVE_S ? "LIVE" : `LAST SEEN ${dur(age)} AGO`}
        </span>
      </div>
      <div className="role">{b.role_text ?? (b.roles.join(", ") || "No task")}</div>
      <dl>
        <dt>Battery</dt>
        <dd>
          {hm(b.endurance_s)}
          {mustReturn !== null && mustReturn !== undefined && b.mode !== "UNAVAILABLE" && (
            <span className={returnDue ? "warn" : ""}> · return by {hhmm(t0, mustReturn)}</span>
          )}
        </dd>
        <dt>Link</dt>
        <dd className={b.link === "none" ? "warn" : ""}>{linkText(b)}</dd>
        <dt>Course</dt>
        <dd>{b.hdg !== undefined ? `${deg(b.hdg)} · ${(b.sog !== undefined ? b.sog / 514.444 : (b.sog_kn ?? 0)).toFixed(1)} kn` : "n/a"}</dd>
        <dt>Tasks</dt>
        <dd className="tasks">{b.tour.length ? b.tour.join(" ") : "none"}</dd>
      </dl>
    </button>
  );
}

export function FleetPanel() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  if (!snap) return <aside className="panel"><h2>Fleet</h2><p className="muted">Waiting for feed</p></aside>;
  const staleAfter = scene?.stale_after_s ?? 60;
  return (
    <aside className="panel">
      <h2>Fleet · {snap.boats.length} USVs</h2>
      {snap.boats.map((b) => <BoatCard key={b.id} b={b} snap={snap} staleAfter={staleAfter} />)}
      <ContactList />
    </aside>
  );
}
