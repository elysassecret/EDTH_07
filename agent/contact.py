"""Contacts: tracks, dwell, the contact task, scout hold and the watcher. Owner: A.
See agent/PLAN.md section 7.8.

Every boat keeps the newest observation of each track (merged from its own camera and from
OBS messages) and OR-merged contact flags, so all boats converge. A slow track with no AIS
near a cable starts a dwell clock; after CONTACT_DWELL it becomes a contact task that the
auction gives to the nearest free boat (the watcher). Watching starts at once: it is the
delegated tier. Closing inside the stand-off ring waits for the watch officer's approval.
"""
from typing import TYPE_CHECKING

from agent.tour import dist_to_line
from contract.constants import CLAIMED, CONTACT_DWELL, CONTACT_STALE, RELEASED, SHADOW_CAP, VETOED
from contract.geo import dist
from contract.mission import Detection
from contract.tasks import Rec, kind

if TYPE_CHECKING:
    from agent.core import Agent

NEAR_CABLE_M = 1_000
FLAGS = ("dwell", "name", "anchor", "cannot_hold", "capped")


def task_of(track: str) -> str:
    return f"contact:{track}"


def ring_point(c: tuple[int, int], b: tuple[int, int], r: int) -> tuple[int, int]:
    """The point at distance r from contact c, on the side boat b is coming from."""
    d = dist(b, c)
    if d == 0:
        return c[0] + r, c[1]
    return c[0] + (b[0] - c[0]) * r // d, c[1] + (b[1] - c[1]) * r // d


class Contacts:
    def __init__(self, agent: "Agent"):
        self.a = agent
        self.tracks: dict[str, dict] = {}  # track -> newest observation (OBS payload)
        self.by: dict[str, dict[int, dict]] = {}  # track -> boat -> that boat's newest observation
        self.own_obs: list[dict] = []
        self.first: dict[str, int] = {}  # track -> earliest time anyone saw it
        self.flags: dict[str, dict] = {}  # contact task -> {flag: bool, "course": int | None}
        self.cables = [s.pts for s in agent.mission.tasks if kind(s.id) == "seg"]
        self.holding: str | None = None  # track this boat holds as scout
        self.watch_start: dict[str, int] = {}  # contact task -> when I claimed it
        self.close: dict[str, str] = {}  # contact task -> "approved" | "done"

    # merging ----------------------------------------------------------------------------------
    def on_obs(self, p: dict) -> None:
        cur = self.tracks.get(p["track"])
        if cur is None or (p["to"], -p["by"]) > (cur["to"], -cur["by"]):
            self.tracks[p["track"]] = p
        mine = self.by.setdefault(p["track"], {})
        if p["by"] not in mine or p["to"] > mine[p["by"]]["to"]:
            mine[p["by"]] = p
        self.first[p["track"]] = min(self.first.get(p["track"], p["to"]), p["to"])

    def on_contact(self, p: dict) -> bool:
        """Merge flags; True if anything changed."""
        cur = self.flags.setdefault(p["id"], {f: False for f in FLAGS} | {"course": None})
        before = dict(cur)
        for f in FLAGS:
            cur[f] = cur[f] or bool(p["flags"].get(f))
        if p.get("course") is not None:
            cur["course"] = p["course"]
        track = p["id"].split(":", 1)[1]
        self.first[track] = min(self.first.get(track, p["first"]), p["first"])
        return cur != before

    def set_flag(self, task: str, **kw) -> None:
        p = {"id": task, "first": self.first.get(task.split(":", 1)[1], self.a.t),
             "flags": {k: v for k, v in kw.items() if k in FLAGS}, "course": kw.get("course")}
        if self.on_contact(p):
            self.a.log("contact", self.message(task))
            self.a.net.send(self.a.t, "CONTACT", self.message(task))

    def message(self, task: str) -> dict:
        f = self.flags[task]
        return {"id": task, "first": self.first[task.split(":", 1)[1]],
                "flags": {k: f[k] for k in FLAGS}, "course": f["course"]}

    # queries ----------------------------------------------------------------------------------
    def candidate(self, d: Detection) -> bool:
        """Slow, no AIS, near a cable: worth a look."""
        return (not d.ais and d.sog <= self.a.params.loiter_sog_mm_s
                and any(dist_to_line((d.x, d.y), pts) <= NEAR_CABLE_M for pts in self.cables))

    def stale(self, track: str, t: int) -> bool:
        return track not in self.tracks or t - self.tracks[track]["to"] > CONTACT_STALE

    def done(self, task: str) -> bool:
        """No boat should take it any more."""
        f = self.flags.get(task, {})
        r = self.a.table.recs.get(task)
        return (f.get("cannot_hold") or f.get("capped") or (r is not None and r.state == VETOED)
                or self.stale(task.split(":", 1)[1], self.a.t))

    def position(self, task: str) -> tuple[int, int]:
        o = self.tracks[task.split(":", 1)[1]]
        return o["x"], o["y"]

    def radius(self, task: str) -> int:
        p = self.a.params
        if self.close.get(task) == "approved":
            return max(p.standoff_floor_m, p.r_verify_m - 10)  # never inside the hard floor
        return (p.standoff_m + p.keep_in_view_m) // 2  # outside 1 nm, inside camera range

    def ring(self, task: str) -> tuple[int, int]:
        return ring_point(self.position(task), self.a.pos, self.radius(task))

    def watching(self) -> str | None:
        """The contact task this boat owns as watcher, if any."""
        for task in self.a.table.held_by(self.a.me):
            if kind(task) == "contact":
                return task
        return None

    def relieved(self, track: str) -> bool:
        """The watcher reports it in view, so a scout can go back to its sweep."""
        r = self.a.table.recs.get(task_of(track))
        if r is None or r.state != CLAIMED or r.owner == self.a.me:
            return False
        o = self.by.get(track, {}).get(r.owner)
        return (o is not None and self.a.t - o["to"] <= CONTACT_STALE
                and o["dist"] <= self.a.params.keep_in_view_m)

    # per tick ---------------------------------------------------------------------------------
    def tick(self, t: int, seen: tuple[Detection, ...]) -> None:
        a, p = self.a, self.a.params
        self.own_obs = [{"track": d.track, "x": d.x, "y": d.y, "sog": d.sog, "cog": d.cog,
                         "ais": d.ais, "to": t, "by": a.me, "dist": dist(a.pos, (d.x, d.y))}
                        for d in seen]
        for o in self.own_obs:
            self.on_obs(o)
        mine = self.watching()
        for d in seen:
            task = task_of(d.track)
            if d.sog > p.speed_mm_s and (mine == task or self.holding == d.track):
                self.set_flag(task, cannot_hold=True, course=d.cog)  # faster than us: report
            if not self.candidate(d) or self.done(task):
                continue
            if task not in a.table.recs and t - self.first[d.track] >= CONTACT_DWELL:
                a.publish(Rec(task, 1, RELEASED, 0, 0, 0))  # every boat makes the same record
                self.set_flag(task, dwell=True)
            if (mine != task and not self.relieved(d.track) and not a.returning
                    and p.policy != "static"):  # static never leaves its station (#19)
                self.holding = d.track  # scout holds until the watcher has it in view
        if self.holding and (self.relieved(self.holding) or self.done(task_of(self.holding))):
            self.holding = None
        if self.holding and t - self.first[self.holding] >= SHADOW_CAP:
            self.set_flag(task_of(self.holding), capped=True)
        if mine and self.done(mine):
            a.release(mine)  # stopped, stale, capped or cannot hold
        elif mine:
            self.watch_start.setdefault(mine, t)
            near = dist(a.pos, self.position(mine)) <= p.r_verify_m + 10
            if self.close.get(mine) == "approved" and near:
                self.close[mine] = "done"  # a look within 500 m: the sim draws nothing
                self.set_flag(mine, name=True, anchor=True)
            if t - self.watch_start[mine] >= SHADOW_CAP:
                self.set_flag(mine, capped=True)

    def on_cmd(self, p: dict) -> None:
        r = self.a.table.recs.get(p["task"])
        if r is None or r.owner != self.a.me or r.state != CLAIMED:
            return
        if p["dec"] == "close" and p["ans"] == "approve" and self.close.get(p["task"]) != "done":
            self.close[p["task"]] = "approved"

    def observations(self) -> list[dict]:
        """OBS payloads for what this boat sees right now."""
        return self.own_obs
