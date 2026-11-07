"""Evaluator metrics on the team world. Owner: D.

Everything here is **truth**: it reads World state the boats and the shore never see, and
nothing flows back. A scorecard speaks mission seconds (0 = end of warm-up), the clock the
scenario tape is written in. The runner shifts the tape, so `world.script` and `world.t`
are both world time and mission time is world time minus `t0_ms`.

A sample that was never visited has age None, not a large number. It is reported as
`never_visited_km`, beside `cable_km_overdue` and never inside it, so the headline cannot
quietly mix "late" with "unknown". `overdue_or_never_km` is the two added together.

Energy and recovery (#109, from world/PRODUCT_BRIEF.md: judge energy work on reserve
violations, unserved work and recovery outcome, never on energy saved):

- **Reserve violation:** an enabled boat more than `HOME_M` from the Korsør station with less
  than `reserve_s` of charge left. Counted in boat-seconds over the whole mission. A boat at 0
  away from the station is also listed as `stranded_boats`. A switched-off boat is not counted:
  that is an injected failure, not an energy decision.
- **Unserved work:** task-seconds from T to evaluation in which a fixed mission task (cable
  segment, lane picket, relay) has no live owner, split by kind. Contact tasks are not in it;
  the contact rows cover them.
- **Recovery outcome** at evaluation: `all tasks` (every fixed task has a live owner),
  `cables only` (every segment does, some picket or the relay does not), `not recovered`
  (some segment has no live owner). `unowned_at_end` names the tasks.
"""

import hashlib
import json
from math import hypot

from contract.constants import CLAIMED, RETURNING, UNAVAILABLE
from contract.mission import FAILURES
from contract.tasks import kind

HOME_M = 50  # at the shore station; same radius as agent/core.py HOME_M

EVERY_MS = 60_000  # one metric row per minute; ages only change at visits


def task_lengths_m(tasks) -> dict[str, float]:
    return {
        t.id: sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(t.pts, t.pts[1:], strict=False))
        for t in tasks
        if kind(t.id) == "seg"
    }


def interval_lengths_m(samples, seg_len: dict[str, float]) -> list[float]:
    """Metres of cable each sample stands for: up to the next sample of its segment, or the
    segment end. Samples stop short of the endpoint, so the last interval is usually under
    100 m. A flat 100 m per sample would give 24.1 km on a 23.6 km route."""
    out = []
    for i, s in enumerate(samples):
        nxt = samples[i + 1] if i + 1 < len(samples) else None
        end = nxt.offset_m if nxt is not None and nxt.task == s.task else seg_len[s.task]
        out.append(max(end - s.offset_m, 0.0))
    return out


def km_overdue(visits, km, now_ms: int, target_ms: int) -> float:
    return sum(
        k for v, k in zip(visits, km, strict=True) if v is not None and now_ms - v > target_ms
    )


def never_visited_km(visits, km) -> float:
    return sum(k for v, k in zip(visits, km, strict=True) if v is None)


def worst_age_ms(visits, now_ms: int) -> int | None:
    ages = [now_ms - v for v in visits if v is not None]
    return max(ages) if ages else None


def seg_ages_s(samples, visits, now_ms: int) -> dict[str, int | None]:
    """Worst sample age per segment; None if any sample of it was never visited."""
    out: dict[str, int | None] = {}
    for s, v in zip(samples, visits, strict=True):
        if v is None or (s.task in out and out[s.task] is None):
            out[s.task] = None
        else:
            out[s.task] = max(out.get(s.task, 0), (now_ms - v) // 1000)
    return dict(sorted(out.items()))


def visits_hash(visits) -> str:
    return hashlib.sha256(json.dumps(visits).encode()).hexdigest()[:16]


class Metrics:
    """Call `on_tick()` once after every `world.step()` of the mission."""

    def __init__(self, world, target_s: int, t0_ms: int = 0, ais=None, log=None, gap=None):
        self.w = world
        self.t0 = t0_ms
        self.target_ms = target_s * 1000
        self.ais = ais
        self.log = log  # called with one dict per metric row
        self.gap = gap  # GapAudit: what the console shows against this truth
        self.samples = world.scene.samples
        self.seg_len = task_lengths_m(world.mission.tasks)
        self.km = [m / 1000 for m in interval_lengths_m(self.samples, self.seg_len)]
        self.segs = sorted(self.seg_len)
        script = world.script
        self.T = min(e["t"] for e in script if e["kind"] in FAILURES) * 1000
        self.eval_t = max(e["t"] for e in script if e["kind"] == "evaluate") * 1000
        self.contact_start = {
            e["id"]: e["t"] * 1000 for e in script if e["kind"] == "contact_start"
        }
        self.detected: dict[str, int] = {}
        self.watcher_in_view: dict[str, int] = {}
        self.watchers: dict[str, set[int]] = {c: set() for c in self.contact_start}
        self.flags: dict[str, set[str]] = {c: set() for c in self.contact_start}
        self.in_view_ms: dict[str, int] = dict.fromkeys(self.contact_start, 0)
        self.boat_mm = dict.fromkeys(world.mission.boats, 0)
        self.ages_hash_T1: str | None = None
        self.state_hash_T1: str | None = None
        self.broken_t: int | None = None
        self.owned_t: int | None = None
        self.seen_claims: set[tuple[str, int, int]] = set()
        self.claims_after: dict[str, int] = {}
        self.worst_post_ms = 0
        self.post_rows: list[float] = []
        self.evaluated: dict | None = None
        self.tasks = [t.id for t in world.mission.tasks]
        self.reserve_ms = world.params.reserve_ms
        self.reserve_viol_ms: dict[int, int] = {}
        self.stranded: set[int] = set()
        self.unserved_ms: dict[str, int] = {}

    # helpers ----------------------------------------------------------------------------------
    def live(self) -> list[int]:
        """Boats that can do work: on, charged, not heading home or docked."""
        return [
            b
            for b, s in sorted(self.w.boats.items())
            if s.enabled
            and s.charge_ms > 0
            and self.w.actions[b].mode not in (RETURNING, UNAVAILABLE)
        ]

    def owned(self, task: str, live: list[int]) -> bool:
        for b in live:
            r = self.w.nodes[b].table.recs.get(task)
            if r is not None and r.state == CLAIMED and r.owner == b:
                return True
        return False

    # per tick ---------------------------------------------------------------------------------
    def on_tick(self) -> None:
        w, t = self.w, self.w.t
        for b in self.boat_mm:
            self.boat_mm[b] += w.telemetry[b]["sog"] * w.tick_ms // 1000
        live = self.live()
        self._claims(t)
        self._ownership(t, live)
        self._contacts(t, live)
        self._reserve()
        if self.T <= t <= self.eval_t:
            self._unserved(live)
        if self.ais is not None:
            self.ais.on_tick(t - self.t0, [w.boats[b].point for b in live])
        if t == self.T - w.tick_ms:
            self.ages_hash_T1 = visits_hash(w.sample_visit_ms)
            self.state_hash_T1 = w.state_hash()
        if (t - self.t0) % EVERY_MS == 0 or t == self.eval_t:
            self._row(t)
        if t == self.eval_t:
            self.evaluated = self.scorecard()

    def _claims(self, t: int) -> None:
        """A claim is a CLAIMED (task, version, owner) new to every table. Counted from T on."""
        for node in self.w.nodes.values():
            for task, r in node.table.recs.items():
                if r.state != CLAIMED or r.ver == 0:
                    continue
                key = (task, r.ver, r.owner)
                if key not in self.seen_claims:
                    self.seen_claims.add(key)
                    if t >= self.T:
                        k = kind(task)
                        self.claims_after[k] = self.claims_after.get(k, 0) + 1

    def _ownership(self, t: int, live: list[int]) -> None:
        """Time from T until every segment has a live owner again, after the failure broke it."""
        if t < self.T or self.owned_t is not None:
            return
        owned = all(self.owned(task, live) for task in self.segs)
        if not owned and self.broken_t is None:
            self.broken_t = t
        elif owned and self.broken_t is not None:
            self.owned_t = t

    def _reserve(self) -> None:
        w = self.w
        shore = w.mission.shore
        for b, s in sorted(w.boats.items()):
            if not s.enabled:
                continue
            x, y = s.point
            if hypot(x - shore[0], y - shore[1]) <= HOME_M:
                continue
            if s.charge_ms < self.reserve_ms:
                self.reserve_viol_ms[b] = self.reserve_viol_ms.get(b, 0) + w.tick_ms
            if s.charge_ms <= 0:
                self.stranded.add(b)

    def _unserved(self, live: list[int]) -> None:
        for task in self.tasks:
            if not self.owned(task, live):
                k = kind(task)
                self.unserved_ms[k] = self.unserved_ms.get(k, 0) + self.w.tick_ms

    def recovery(self, live: list[int]) -> tuple[str, list[str]]:
        unowned = [task for task in self.tasks if not self.owned(task, live)]
        if any(kind(task) == "seg" for task in unowned):
            return "not recovered", unowned
        return ("cables only" if unowned else "all tasks"), unowned

    def _contacts(self, t: int, live: list[int]) -> None:
        w = self.w
        keep = w.params.keep_in_view_m
        for cid in self.contact_start:
            truth = w.contacts.get(cid)
            if truth is None:
                continue
            task = f"contact:{cid}"
            if cid not in self.detected:
                seen = [n.contacts.first[cid] for n in w.nodes.values() if cid in n.contacts.first]
                if seen:
                    self.detected[cid] = min(seen)
            for b, node in sorted(w.nodes.items()):
                r = node.table.recs.get(task)
                if r is None:
                    continue
                if r.state == CLAIMED and r.owner:
                    self.watchers[cid].add(r.owner)
                self.flags[cid].update(
                    f for f, v in node.contacts.flags.get(task, {}).items() if v is True
                )
                if cid not in self.watcher_in_view and r.state == CLAIMED and r.owner == b:
                    obs = node.contacts.by.get(cid, {}).get(b)
                    if obs is not None and obs["to"] == t and obs["dist"] <= keep:
                        self.watcher_in_view[cid] = t
            x, y = truth.point
            for b in live:
                px, py = w.boats[b].point
                if hypot(px - x, py - y) <= keep:
                    self.in_view_ms[cid] += w.tick_ms
                    break

    def _row(self, t: int) -> None:
        visits = self.w.sample_visit_ms
        overdue = km_overdue(visits, self.km, t, self.target_ms)
        worst = worst_age_ms(visits, t)
        if self.gap is not None:
            truth = seg_ages_s(self.samples, visits, t)
            self.gap.add(self.w.shore.picture(t).seg_age, truth, t // 1000)
        if self.T <= t <= self.eval_t:
            self.post_rows.append(overdue)
            if worst is not None:
                self.worst_post_ms = max(self.worst_post_ms, worst)
        if self.log is not None:
            self.log(
                {
                    "t": (t - self.t0) // 1000,
                    "km_overdue": round(overdue, 3),
                    "never_km": round(never_visited_km(visits, self.km), 3),
                    "worst_age_s": None if worst is None else worst // 1000,
                    "modes": {b: self.w.actions[b].mode for b in sorted(self.w.actions)},
                }
            )

    # scorecard --------------------------------------------------------------------------------
    def scorecard(self) -> dict:
        w, t = self.w, self.w.t
        visits = w.sample_visit_ms
        overdue = km_overdue(visits, self.km, t, self.target_ms)
        never = never_visited_km(visits, self.km)
        worst = worst_age_ms(visits, t)
        live = self.live()
        since = self.contact_start
        outcome, unowned = self.recovery(live)
        out = {
            "t_s": (t - self.t0) // 1000,
            "seed": w.seed,
            "mode": w.params.policy,
            "speed_mm_s": w.params.speed_mm_s,
            "radio_boat_m": w.radio_config.boat_m,
            "target_s": self.target_ms // 1000,
            "cable_km_total": round(sum(self.km), 2),
            "cable_km_overdue": round(overdue, 2),
            "never_visited_km": round(never, 2),
            "overdue_or_never_km": round(overdue + never, 2),
            "mean_km_overdue_post_T": (
                round(sum(self.post_rows) / len(self.post_rows), 2) if self.post_rows else None
            ),
            "worst_age_s": None if worst is None else worst // 1000,
            "worst_age_post_T_s": self.worst_post_ms // 1000,
            "seg_age_s": seg_ages_s(self.samples, visits, t),
            "time_to_all_segs_owned_s": (
                None if self.owned_t is None else (self.owned_t - self.T) // 1000
            ),
            "ownership_broken": self.broken_t is not None,
            "segs_unowned_at_end": sum(1 for task in self.segs if not self.owned(task, live)),
            "repair_claims_after_T": sum(self.claims_after.values()),
            "claims_after_T": dict(sorted(self.claims_after.items())),
            "reserve_violation_s": sum(self.reserve_viol_ms.values()) // 1000,
            "reserve_violation_boats": sorted(self.reserve_viol_ms),
            "stranded_boats": sorted(self.stranded),
            "unserved_task_s_post_T": sum(self.unserved_ms.values()) // 1000,
            "unserved_s_by_kind": {k: v // 1000 for k, v in sorted(self.unserved_ms.items())},
            "recovery_outcome": outcome,
            "unowned_at_end": unowned,
            "operator_actions": len(getattr(w.shore, "decisions", {})),
            "boat_km": {b: round(mm / 1_000_000, 1) for b, mm in sorted(self.boat_mm.items())},
            "boats_end": {
                b: {"mode": w.actions[b].mode, "batt": s.own().batt}
                for b, s in sorted(w.boats.items())
            },
            "ages_hash_T1": self.ages_hash_T1,
            "state_hash_T1": self.state_hash_T1,
            "contacts": sorted(self.contact_start),
            "detect_s": {c: (v - since[c]) // 1000 for c, v in self.detected.items()},
            "watcher_in_view_s": {
                c: (v - since[c]) // 1000 for c, v in self.watcher_in_view.items()
            },
            "contact_in_view_total_s": {c: v // 1000 for c, v in self.in_view_ms.items()},
            "watchers": {c: sorted(v) for c, v in self.watchers.items()},
            "contact_flags": {c: sorted(v) for c, v in self.flags.items()},
        }
        if self.ais is not None:
            out.update(self.ais.summary())
        if self.gap is not None:
            out["gap"] = self.gap.row()
        return out
