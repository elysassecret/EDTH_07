"""Alerts for the real sim, built from the shore picture only. Owner: C. Feature 23.

The real ShoreNode sends no alerts, so the bridge makes them here from what the shore
station knows (the /shore picture) plus what the console itself did (its exercise events).
Truth is never used.

Three levels, the bridge alert words (docs/research/operations_incidents_law.md):
- alarm:   a held decision unanswered for ALARM_AFTER_S ("Unanswered: repeats in 05:00,
           then alarm")
- warning: a held decision waiting for the watch officer; a boat not heard for stale_after_s;
           a contact on the shore picture with no AIS match ("cue for a look"); a contact the
           boats cannot hold
- caution: no link to shore, a boat returning to Korsør, a lane picket uncovered
           ("since HH:MMZ": when the console first saw it open), a cable segment past the
           revisit target ("no visit since HH:MMZ", from the shore's own segment age),
           an exercise failure (battery_low, boat_off, link_off)

Rules:
- One alert per id (dedup). Its time is when it was first raised at its current level.
- A condition alert stays while the condition holds. Acknowledge means "I have seen it":
  it stays listed, marked acknowledged. If it escalates to a higher level, it needs a new
  acknowledgement.
- An exercise-event alert has no condition to watch, so it goes away when acknowledged
  (a link cut also goes away when the link is restored).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from contract.views import Alert, Snapshot

ALARM_AFTER_S = 300  # research note: unanswered held decision repeats at 05:00, then alarm
RANK = {"alarm": 0, "warning": 1, "caution": 2}
FAILURE_KINDS = ("battery_low", "boat_off", "link_off")


def _usv(i: int) -> str:
    return f"USV {i:02d}"


class AlertBook:
    def __init__(self, stale_after_s: int, t0_utc: str = "", revisit_target_s: int | None = None):
        self.stale_after_s = stale_after_s
        self.revisit_target_s = revisit_target_s  # config/run.toml; None = no overdue alerts
        self.t0 = datetime.fromisoformat(t0_utc) if t0_utc else None
        self.active: dict[str, dict] = {}  # id -> {level, text, t, ack}
        self.acked_events: set[str] = set()  # exercise-event alerts the officer cleared

    def _hhmm(self, t: int) -> str:
        if self.t0 is None:
            return f"t+{t} s"
        return (self.t0 + timedelta(seconds=t)).strftime("%H:%MZ")

    # ---- inputs
    def update(self, pic: Snapshot, exercise: list[dict], cuts: set[tuple[int, int]]) -> None:
        """Recompute from the shore picture. Calling it twice at the same time is harmless."""
        t = pic.t
        want: dict[str, tuple[str, str]] = {}  # id -> (level, text)

        for b in pic.boats:
            if t - b.last_heard > self.stale_after_s:
                want[f"stale:{b.id}"] = (
                    "warning", f"{_usv(b.id)} not heard since {self._hhmm(b.last_heard)}")
            if b.link == "none":
                want[f"nolink:{b.id}"] = ("caution", f"{_usv(b.id)} no link to shore")
            if b.mode == "RETURNING":
                want[f"rtb:{b.id}"] = ("caution", f"{_usv(b.id)} returning to Korsør")

        for k, task in sorted(pic.tasks.items()):
            # state 0 released / 2 vetoed; v > 0 means it was claimed before (not start-up)
            if k.startswith("pick:") and task.state != 1 and task.v > 0:
                aid = f"picket:{k}"
                since = self.active[aid]["t"] if aid in self.active else t
                want[aid] = ("caution", f"Lane picket {k[5:]} uncovered since {self._hhmm(since)}")

        target = self.revisit_target_s
        for k, age in sorted(pic.seg_age.items()):
            if target is None or (age is not None and age <= target):
                continue
            if age is None or age >= t:  # the shore has no visit report for it in this run
                text = f"Cable {k}: no visit reported since start (shore-reported)"
            else:
                text = f"Cable {k} overdue: no visit since {self._hhmm(t - age)} (shore-reported)"
            want[f"overdue:{k}"] = ("caution", text)

        for c in pic.contacts:
            if c.flags.cannot_hold:
                want[f"contact:{c.track}"] = (
                    "warning", f"Cannot hold {c.track}: leaving faster than our boats")
            elif not c.ais:
                want[f"contact:{c.track}"] = (
                    "warning", f"{c.track}: camera contact, no AIS match. Cue for a look.")

        for d in pic.decisions:
            if d.state != "pending" or d.tier != "held":
                continue
            open_s = t - d.t
            if open_s >= ALARM_AFTER_S:
                mm, ss = divmod(open_s, 60)
                want[f"decision:{d.id}"] = ("alarm", f"Unanswered {mm:02d}:{ss:02d}: {d.text}")
            else:
                want[f"decision:{d.id}"] = ("warning", f"Waiting for watch officer: {d.text}")

        for n, e in enumerate(exercise):
            aid = f"exercise:{n}"
            if e["kind"] not in FAILURE_KINDS or aid in self.acked_events:
                continue
            if e["kind"] == "link_off" and e["pair"] not in cuts:
                continue  # restored since
            if not e.get("active", True):
                continue  # boat switched back on since
            want[aid] = ("caution", e["text"])

        for aid in sorted(set(self.active) - set(want)):
            del self.active[aid]
        for aid, (level, text) in sorted(want.items()):
            a = self.active.get(aid)
            if a is None or RANK[level] < RANK[a["level"]]:
                self.active[aid] = {"level": level, "text": text, "t": t, "ack": False}
            else:  # same or lower level: keep its time and acknowledgement, refresh words
                a.update(level=level, text=text)

    def ack(self, aid: str) -> bool:
        a = self.active.get(aid)
        if a is None:
            return False
        if aid.startswith("exercise:"):
            self.acked_events.add(aid)
            del self.active[aid]
        else:
            a["ack"] = True
        return True

    # ---- output
    def alerts(self) -> list[Alert]:
        order = sorted(self.active.items(),
                       key=lambda kv: (kv[1]["ack"], RANK[kv[1]["level"]], -kv[1]["t"], kv[0]))
        return [Alert(id=aid, level=a["level"], t=a["t"], text=a["text"], ack=a["ack"])
                for aid, a in order]
