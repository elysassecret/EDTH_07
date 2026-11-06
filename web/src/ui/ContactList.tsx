// Owner: C. Feature 19: contact tracks as a list. How the swarm knows each contact
// (AIS / camera only "NO AIS" / both), who sees it, and how old the data is.
// Wording rule: "cue for a look", never "suspicious" or "hostile".
import { useStore } from "../store";
import { deg, dur } from "../format";
import type { Contact, Snapshot } from "../types";

const LIVE_S = 5;
const KN_PER_MM_S = 1 / 514.444;

function typeBadge(k: Contact): { word: string; cls: string } {
  if (!k.ais) return { word: "NO AIS", cls: "dark" };
  if (k.source === "fused") return { word: "AIS+CAM", cls: "fused" };
  return { word: "AIS", cls: "ais" };
}

const usv = (id: number) => `USV ${String(id).padStart(2, "0")}`;

function ContactRow({ k, snap, staleAfter }: { k: Contact; snap: Snapshot; staleAfter: number }) {
  const selected = useStore((s) => s.selectedContact);
  const selectContact = useStore((s) => s.selectContact);
  const frozen = useStore((s) => s.conn) !== "live";
  const age = snap.t - k.last_seen;
  const stale = frozen || age > staleAfter;
  const badge = typeBadge(k);
  const kn = k.sog_kn ?? k.sog * KN_PER_MM_S;
  return (
    <button
      className={`card contact ${stale ? "stale" : ""} ${selected === k.id ? "selected" : ""}`}
      onClick={() => selectContact(selected === k.id ? null : k.id)}
      aria-pressed={selected === k.id}
    >
      <div className="card-head">
        <span className="id">{k.ais ? (k.name ?? k.track) : k.track}</span>
        <span className={`chip type-${badge.cls}`}>{badge.word}</span>
        <span className={`age ${stale ? "old" : ""}`}>
          {frozen ? "FROZEN" : age <= LIVE_S ? "LIVE" : `LAST SEEN ${dur(age)} AGO`}
        </span>
      </div>
      <dl>
        <dt>Course</dt>
        <dd>{kn < 0.5 ? `Stopped · ${kn.toFixed(1)} kn` : `${deg(k.cog)} · ${kn.toFixed(1)} kn`}</dd>
        <dt>Seen by</dt>
        <dd>{k.seen_by.length ? k.seen_by.map(usv).join(", ") : "nobody now"}</dd>
        {!k.ais && (
          <>
            <dt>Watching</dt>
            <dd>{k.watcher ? usv(k.watcher) : "no boat assigned"}</dd>
            <dt>Name</dt>
            <dd>{k.name_status ?? (k.flags.name ? "IMAGE TAKEN" : "NOT READ")}</dd>
            <dt>Anchor</dt>
            <dd>{k.anchor_status ?? (k.flags.anchor ? "IMAGE TAKEN" : "NOT SEEN")}</dd>
          </>
        )}
      </dl>
      {!k.ais && (
        <div className="note">
          {k.flags.cannot_hold
            ? `Cannot hold: faster than USV. Report queued.${k.course !== null && k.course !== undefined ? ` Last course ${deg(k.course)}.` : ""}`
            : "Camera contact with no AIS match. Cue for a look."}
          <br />Not assessed: identity, intent, distress.
        </div>
      )}
    </button>
  );
}

export function ContactList() {
  const snap = useStore((s) => s.snap);
  const scene = useStore((s) => s.scene);
  if (!snap) return null;
  const staleAfter = scene?.stale_after_s ?? 60;
  // camera-only first, then most recently seen
  const list = [...snap.contacts].sort((a, b) => Number(a.ais) - Number(b.ais) || b.last_seen - a.last_seen);
  const nDark = list.filter((k) => !k.ais).length;
  return (
    <section>
      <h2>Contacts · {list.length}{nDark ? ` · ${nDark} NO AIS` : ""}</h2>
      {list.map((k) => <ContactRow key={k.id} k={k} snap={snap} staleAfter={staleAfter} />)}
    </section>
  );
}
