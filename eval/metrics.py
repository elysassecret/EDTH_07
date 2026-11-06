"""Ground-truth metrics: sample ages, km overdue, worst age, contact timeline, lane crossings in view.

Visit credit uses r_verify only, and only boats that are live (not returning,
not docked, not failed): assignment alone never closes a gap (S5).
"""
from __future__ import annotations

import hashlib
import math

import numpy as np

from contract.constants import CLAIMED, RETURNING, UNAVAILABLE
from world import geo


class Metrics:
    def __init__(self, sim):
        self.sim = sim
        cfg = sim.cfg
        self.samples = np.array(sim.scene.samples, dtype=np.float64)
        self.n = len(self.samples)
        self.step_m = float(cfg["scene"]["sample_step_m"])
        self.r_verify = float(cfg["boat"]["r_verify_m"])
        self.keep_in_view = float(cfg["boat"]["keep_in_view_m"])
        self.target_ms = int(cfg["run"]["revisit_target_s"]) * 1000
        self.last_visit = np.full(self.n, sim.t, dtype=np.int64)
        self.seg_slices = {s.task: slice(s.sample_offset, s.sample_offset + len(s.samples)) for s in sim.scene.segments}
        self.first_event_t = min((e["t"] for e in sim.events if e["kind"] not in ("reset", "evaluate")), default=0) * 1000
        self.eval_t = next((e["t"] for e in sim.events if e["kind"] == "evaluate"), cfg["run"]["evaluate_s"]) * 1000
        self.all_owned_t: int | None = None
        self.detect_t: dict[str, int] = {}
        self.in_view_t: dict[str, int] = {}
        self.dwell_start: dict[str, int] = {}
        self.crossings: list[dict] = []
        self.ais_last: dict[str, tuple[float, float, int]] = {}
        self.worst_post = 0
        self.ages_at_T_minus_1: bytes | None = None
        self.evaluated: dict | None = None
        self.operator_actions = 0
        self.cables = [piece for name in cfg["scene"]["scenario_lines"] for piece in sim.scene.cables[name]]

    def live_boats(self):
        for b, boat in sorted(self.sim.boats.items()):
            if boat.failed or boat.docked or boat.mode in (RETURNING, UNAVAILABLE):
                continue
            yield b, boat

    def update(self, t: int) -> None:
        for _, boat in self.live_boats():
            d2 = (self.samples[:, 0] - boat.x) ** 2 + (self.samples[:, 1] - boat.y) ** 2
            self.last_visit[d2 <= self.r_verify ** 2] = t
        if t == self.first_event_t - 1000:
            self.ages_at_T_minus_1 = (t - self.last_visit).tobytes()
        if t >= self.first_event_t and self.all_owned_t is None and self._all_segs_owned():
            self.all_owned_t = t
        if t > self.first_event_t:
            self.worst_post = max(self.worst_post, int((t - self.last_visit).max()))
        for vid, v in sorted(self.sim.vessels.items()):
            cid = f"contact:{vid}"
            if cid not in self.dwell_start:
                self.dwell_start[cid] = v.t_start
        for b, ag in sorted(self.sim.agents.items()):
            for cid, obs in ag.contact_obs.items():
                if cid not in self.detect_t:
                    self.detect_t[cid] = obs["t"]
                if obs.get("in_view") and obs["by"] != ag.me and cid not in self.in_view_t:
                    pass
            if ag.shadow_cid and ag.shadow_cid not in self.in_view_t:
                obs = ag.contact_obs.get(ag.shadow_cid)
                if obs and obs["by"] == ag.me and obs.get("in_view"):
                    self.in_view_t[ag.shadow_cid] = t
        if t == self.eval_t:
            self.evaluated = self.scorecard(t)

    def _all_segs_owned(self) -> bool:
        live = {b for b, _ in self.live_boats()}
        for s in self.sim.scene.segments:
            owner = None
            for b in sorted(live):
                ag = self.sim.agents[b]
                r = ag.table.get(s.task)
                if r is not None and r.state == CLAIMED and r.owner == b and any(e[0] == s.task for e in ag.tour):
                    owner = b
            if owner is None:
                return False
        return True

    def on_ais(self, pings, t: int) -> None:
        """Record real-vessel crossings of scenario cables and whether a live boat had them in view."""
        for p in pings:
            prev = self.ais_last.get(p.track)
            self.ais_last[p.track] = (p.x, p.y, t)
            if prev is None or t - prev[2] > 1_800_000:
                continue
            for cable in self.cables:
                for a, b in zip(cable[:-1], cable[1:]):
                    hit = geo.seg_intersect((prev[0], prev[1]), (p.x, p.y), a, b)
                    if hit:
                        in_view = any(math.hypot(boat.x - hit[0], boat.y - hit[1]) <= self.keep_in_view
                                      for _, boat in self.live_boats())
                        self.crossings.append({"t": t, "track": p.track, "x": round(hit[0]), "y": round(hit[1]),
                                               "in_view": in_view})
                        break
                else:
                    continue
                break

    def ages(self, t: int) -> np.ndarray:
        return t - self.last_visit

    def seg_age(self, t: int) -> dict[str, int]:
        a = self.ages(t)
        return {task: int(a[sl].max() // 1000) for task, sl in self.seg_slices.items()}

    def km_overdue(self, t: int) -> float:
        return float((self.ages(t) > self.target_ms).sum() * self.step_m / 1000.0)

    def worst_age(self, t: int) -> int:
        return int(self.ages(t).max() // 1000)

    def ages_hash(self, t: int) -> str:
        return hashlib.sha256(self.ages(t).tobytes()).hexdigest()[:16]

    def scorecard(self, t: int) -> dict:
        T = self.first_event_t
        post = [c for c in self.crossings if c["t"] >= T]
        boats_km = {b: round(boat.moved_m / 1000, 1) for b, boat in sorted(self.sim.boats.items())}
        sc = {
            "t_s": t // 1000,
            "mode": self.sim.mode,
            "seed": self.sim.seed,
            "cable_km_overdue": round(self.km_overdue(t), 1),
            "cable_km_total": round(self.n * self.step_m / 1000.0, 1),
            "worst_age_s": self.worst_age(t),
            "worst_age_post_event_s": self.worst_post // 1000,
            "seg_age_s": self.seg_age(t),
            "time_to_all_segs_owned_s": None if self.all_owned_t is None else (self.all_owned_t - T) // 1000,
            "lane_crossings_post_event": len(post),
            "lane_crossings_in_view": sum(1 for c in post if c["in_view"]),
            "detect_s": {cid: (tt - self.dwell_start.get(cid, tt)) // 1000 for cid, tt in sorted(self.detect_t.items())},
            "contacts_scripted": sorted(self.dwell_start),
            "in_view_s": {cid: (tt - self.dwell_start.get(cid, tt)) // 1000 for cid, tt in sorted(self.in_view_t.items())},
            "operator_actions": len(self.sim.shore.actions),
            "hours_post_event": round((t - T) / 3_600_000, 2),
            "boat_km": boats_km,
            "radio": dict(self.sim.radio.stats),
            "claims": sum(a.stats["claims"] for a in self.sim.agents.values()),
            "releases": sum(a.stats["releases"] for a in self.sim.agents.values()),
            "repair_claims_after_T": sum(sum(a.repair_claims_after.values()) for a in self.sim.agents.values()),
            "reports_queued": sum(1 for a in self.sim.agents.values() for r in a.reports if r.get("queued")),
        }
        sc["operator_actions_per_hour"] = round(sc["operator_actions"] / max(sc["hours_post_event"], 0.01), 2)
        return sc
