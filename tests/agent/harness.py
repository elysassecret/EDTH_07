"""Tiny deterministic fake world for agent tests. Test-only; world/ (B) is the real simulator.

Tick order follows agent/PLAN.md D-6: events (caller), move, deliver, step boats in ID order
then the shore, broadcast. Positions are kept in mm so 2.3 m/s moves exactly.
"""
import hashlib
import heapq
import json
import random
from math import cos, isqrt, radians, sin

from agent.core import Agent
from agent.shore import ShoreNode
from contract.constants import SHORE
from contract.mission import Action, Detection, Mission, Own, Params


class Sim:
    def __init__(self, mission: Mission, params: Params, start: dict[int, tuple[int, int]],
                 delay_ms: int = 1_000, loss: float = 0.0, seed: int = 0,
                 boat_range_m: int = 8_000, shore_range_m: int = 14_000, detect_m: int = 2_000):
        self.mission, self.params = mission, params
        self.agents = {b: Agent(b, mission, params) for b in mission.boats}
        self.shore = ShoreNode(mission, params)
        self.pos = {b: (start[b][0] * 1000, start[b][1] * 1000) for b in mission.boats}
        self.pos[SHORE] = (mission.shore[0] * 1000, mission.shore[1] * 1000)
        self.batt = {b: 1000 for b in mission.boats}
        self.alive = {b: True for b in mission.boats}
        self.off: set[tuple[int, int]] = set()  # directed links switched off; membership only
        self.slow: dict[int, int] = {}  # boat -> propulsion permille (test faults only)
        self.actions = {b: Action("PATROL", None, 0) for b in mission.boats}
        self.delay_ms, self.loss, self.rng = delay_ms, loss, random.Random(seed)
        self.boat_range_m, self.shore_range_m = boat_range_m, shore_range_m
        self.queue: list[tuple[int, int, int, bytes]] = []  # (deliver_t, seq, dst, bytes)
        self.seq = 0
        self.t = 0
        self.detect_m = detect_m
        self.tracks: dict[str, dict] = {}  # synthetic contacts, positions in mm

    # controls -----------------------------------------------------------------------------
    def kill(self, b: int) -> None:
        self.alive[b] = False

    def set_batt(self, b: int, permille: int) -> None:
        self.batt[b] = permille

    def link(self, a: int, b: int, on: bool) -> None:
        for pair in ((a, b), (b, a)):
            if on:
                self.off.discard(pair)
            else:
                self.off.add(pair)

    def add_track(self, tid: str, xy: tuple[int, int], sog: int = 0, cog: int = 0,
                  ais: bool = False) -> None:
        self.tracks[tid] = {"x": xy[0] * 1000, "y": xy[1] * 1000, "ais": ais}
        self.set_track(tid, sog, cog)

    def set_track(self, tid: str, sog: int, cog: int) -> None:
        """sog in mm/s, cog in degrees clockwise from north (test-only trig)."""
        tr = self.tracks[tid]
        tr.update(sog=sog, cog=cog, vx=round(sog * sin(radians(cog))),
                  vy=round(sog * cos(radians(cog))))

    def detections(self, b: int) -> tuple[Detection, ...]:
        x, y = self.xy(b)
        out = []
        for tid, tr in sorted(self.tracks.items()):
            tx, ty = tr["x"] // 1000, tr["y"] // 1000
            if isqrt((tx - x) ** 2 + (ty - y) ** 2) <= self.detect_m:
                out.append(Detection(tid, tx, ty, tr["sog"], tr["cog"], tr["ais"]))
        return tuple(out)

    def isolate(self, b: int, on: bool = False) -> None:
        for other in (SHORE, *self.mission.boats):
            if other != b:
                self.link(b, other, on)

    # loop ---------------------------------------------------------------------------------
    def xy(self, n: int) -> tuple[int, int]:
        return self.pos[n][0] // 1000, self.pos[n][1] // 1000

    def in_range(self, a: int, b: int) -> bool:
        (ax, ay), (bx, by) = self.xy(a), self.xy(b)
        rng = self.shore_range_m if SHORE in (a, b) else self.boat_range_m
        return isqrt((ax - bx) ** 2 + (ay - by) ** 2) <= rng

    def move(self, b: int) -> None:
        a = self.actions[b]
        if a.target is None:
            return
        (x, y), (tx, ty) = self.pos[b], (a.target[0] * 1000, a.target[1] * 1000)
        # 1 s tick; slow[b] < 1000 models weak propulsion (#106), unknown to the boat
        d, step = isqrt((tx - x) ** 2 + (ty - y) ** 2), a.speed_mm_s * self.slow.get(b, 1000) // 1000
        self.pos[b] = (tx, ty) if d <= step else (x + (tx - x) * step // d,
                                                  y + (ty - y) * step // d)

    def broadcast(self, src: int, out: list[bytes]) -> None:
        for raw in out:
            for dst in (*self.mission.boats, SHORE):
                if dst == src or (dst != SHORE and not self.alive[dst]):
                    continue
                if (src, dst) in self.off or not self.in_range(src, dst):
                    continue
                if self.loss and self.rng.random() < self.loss:
                    continue
                self.seq += 1
                heapq.heappush(self.queue, (self.t + self.delay_ms, self.seq, dst, raw))

    def tick(self) -> None:
        for b in self.mission.boats:
            if self.alive[b]:
                self.move(b)
        for tr in self.tracks.values():
            tr["x"] += tr["vx"]
            tr["y"] += tr["vy"]
        inbox: dict[int, list[bytes]] = {n: [] for n in (*self.mission.boats, SHORE)}
        while self.queue and self.queue[0][0] <= self.t:
            _, _, dst, raw = heapq.heappop(self.queue)
            inbox[dst].append(raw)
        for b in self.mission.boats:
            if not self.alive[b]:
                continue
            x, y = self.xy(b)
            action, out = self.agents[b].step(self.t, Own(x, y, self.batt[b]), self.detections(b),
                                              inbox[b])
            self.actions[b] = action
            self.broadcast(b, out)
        self.broadcast(SHORE, self.shore.step(self.t, inbox[SHORE]))
        self.t += 1_000

    def run_until(self, t_ms: int) -> None:
        while self.t <= t_ms:
            self.tick()

    def digest(self) -> str:
        views = [self.agents[b].view() for b in self.mission.boats]
        blob = json.dumps({"views": views, "pos": sorted(self.pos.items())}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()
