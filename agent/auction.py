"""Slotted auction on shared time, no coordinator. Owner: A. See agent/PLAN.md section 7.4.

At each slot boundary a boat closes the previous round with the bids it heard, claims a task
if it was cheapest, then bids on the first open task (bid order) it is eligible for.
Losers do nothing; if two boats both think they won, merge keeps the lower bid.
"""
from typing import TYPE_CHECKING

from contract.constants import CLAIMED, CYCLE_MAX, SHORE_SILENCE, SLOT
from contract.geo import dist
from contract.tasks import BID_ORDER, kind

if TYPE_CHECKING:
    from agent.core import Agent


def ms(metres: int, speed_mm_s: int) -> int:
    return metres * 1_000_000 // speed_mm_s


class Auction:
    def __init__(self, agent: "Agent"):
        self.a = agent
        self.bids: dict[int, dict[str, list[tuple[int, int]]]] = {}  # e -> task -> [(cost, boat)]

    def on_bid(self, p: dict) -> None:
        self.bids.setdefault(p["e"], {}).setdefault(p["task"], []).append((p["cost"], p["boat"]))

    def on_slot(self, t: int) -> None:
        e = t // SLOT
        self.close_round(e - 1, t)
        for old in [k for k in self.bids if k < e - 1]:
            del self.bids[old]
        if not self.a.may_bid(t):
            return
        table = self.a.table
        for task in sorted(table.recs, key=lambda k: (BID_ORDER.get(kind(k), 99), k)):
            if table.is_open(task, t) and self.can_bid(task, t):
                cost = self.cost(task)
                self.on_bid({"task": task, "e": e, "cost": cost, "boat": self.a.me})
                self.a.net.send(t, "BID", {"task": task, "e": e, "cost": cost, "boat": self.a.me})
                return  # one bid per slot

    def close_round(self, e: int, t: int) -> None:
        for task, bs in sorted(self.bids.pop(e, {}).items()):
            if task not in self.a.table.recs or not self.a.table.is_open(task, t):
                continue  # a live claim arrived during the round: cancel
            bs = sorted(bs, key=lambda b: (b[0], -b[1]))
            if bs[0][1] != self.a.me:
                continue
            dep = bs[1][1] if len(bs) > 1 and kind(task) in ("relay", "contact") else 0
            self.a.claim(task, bs[0][0], dep)

    # cost and eligibility ------------------------------------------------------------------
    def cycle_after(self, task: str) -> int:
        a = self.a
        return ms(a.tours.cycle_m(a.tours.insert(a.legs(), task)), a.params.speed_mm_s)

    def reach_ms(self, task: str) -> int:
        a = self.a
        if kind(task) == "seg":
            return ms(a.tours.reach_m(a.pos, task), a.params.speed_mm_s)
        return ms(dist(a.pos, a.station(task)), a.params.speed_mm_s)

    def cost(self, task: str) -> int:
        a = self.a
        c = self.reach_ms(task) + 1_800_000 * (1000 - a.batt) // 1000
        if kind(task) == "seg":
            c += self.cycle_after(task)
            if a.holds("pick"):
                c += a.params.role_penalty_ms  # PLAN F3: cables before lane, but not for free
        return c

    def energy_ok(self, task: str) -> bool:
        a = self.a
        p = a.params
        far = a.tours.pts[task][-1] if kind(task) == "seg" else a.station(task)
        one_pass = ms(a.tours.len[task], p.speed_mm_s) if kind(task) == "seg" else 0
        need = self.reach_ms(task) + one_pass + a.return_ms(far)
        return a.remaining_ms() - p.reserve_ms >= p.return_safety_permille * need // 1000

    def can_bid(self, task: str, t: int) -> bool:
        a = self.a
        k = kind(task)
        if k == "seg":
            if a.table.recs[task].state == CLAIMED and not a.majority:
                return False  # taking over an expired claim needs a live majority (P4)
            return (not a.holds("relay") and self.cycle_after(task) <= CYCLE_MAX
                    and self.energy_ok(task))
        if k == "pick":
            return not any(a.holds(x) for x in ("seg", "pick", "relay", "contact"))
        if k == "relay":
            # A relay reconnects a group: a lone boat out of range keeps its work instead.
            return (t - a.shore_t > SHORE_SILENCE and a.live_peers(t) >= 1
                    and self.energy_ok(task))
        return False  # contact and cue come in later phases

