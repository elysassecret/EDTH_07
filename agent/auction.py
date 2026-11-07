"""Slotted auction on shared time, no coordinator. Owner: A. See agent/PLAN.md section 7.4.

At each slot boundary a boat closes the previous round with the bids it heard, claims a task
if it was cheapest, then bids on the first open task (bid order) it is eligible for.
Losers do nothing; if two boats both think they won, merge keeps the lower bid.
"""
from typing import TYPE_CHECKING

from agent.contact import NEAR_CABLE_M
from agent.tour import dist_to_line
from contract.constants import (
    CLAIMED,
    CYCLE_MAX,
    PEER_STALE,
    REBALANCE,
    RETURNING,
    SHADOWING,
    SHORE_SILENCE,
    SLOT,
    UNAVAILABLE,
)
from contract.geo import dist
from contract.tasks import BID_ORDER, kind

if TYPE_CHECKING:
    from agent.core import Agent


WHY_MAX = 120  # characters of a reason the shore shows
# PLAN F6: winning a task of this kind frees the boat's tasks of these kinds
DROPS = {"seg": ("pick",), "relay": ("seg", "pick"), "contact": ("seg", "pick")}


def hm(ms_: int) -> str:
    """A duration (ms) as hours and minutes."""
    m = ms_ // 60_000
    return f"{m // 60} h {m % 60:02d} m" if m >= 60 else f"{m} m"


def ms(metres: int, speed_mm_s: int) -> int:
    return metres * 1_000_000 // speed_mm_s


class Auction:
    def __init__(self, agent: "Agent"):
        self.a = agent
        self.bids: dict[int, dict[str, list[tuple[int, int]]]] = {}  # e -> task -> [(cost, boat)]
        self.gave: dict[str, int] = {}  # task -> until when I won't bid on what I just gave away
        self.options: list[tuple[int, str]] = []  # this round's best options (score ms, task)
        self.compared: dict[str, list[tuple[int, str]]] = {}  # bid task -> options it beat

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
        order = sorted(table.recs, key=lambda k: (BID_ORDER.get(kind(k), 99), k))
        open_now = [k for k in order if table.is_open(k, t) and self.can_bid(k, t)]
        # every option this round, scored the same way (#123); the bid goes, as before, to the
        # first one in priority order, and the others are kept to show what it was compared with
        self.options = sorted((self.score(k, t)[0], k) for k in open_now)[:3]
        if open_now:  # one bid per slot
            task = open_now[0]
            cost = self.score(task, t)[0]
            self.compared[task] = self.options
            self.on_bid({"task": task, "e": e, "cost": cost, "boat": self.a.me})
            self.a.net.send(t, "BID", {"task": task, "e": e, "cost": cost, "boat": self.a.me})

    def close_round(self, e: int, t: int) -> None:
        for task, bs in sorted(self.bids.pop(e, {}).items()):
            if (not self.a.may_bid(t) or task not in self.a.table.recs
                    or not self.a.table.is_open(task, t) or not self.can_bid(task, t)):
                continue  # eligibility can change after bidding: return, role, quorum or policy
            bs = sorted(bs, key=lambda b: (b[0], -b[1]))
            if bs[0][1] != self.a.me:
                continue
            dep = bs[1][1] if len(bs) > 1 and kind(task) in ("relay", "contact") else 0
            self.a.claim(task, bs[0][0], dep, self.reason(task, t, bs),
                         self.compared.pop(task, []))

    def take_over(self, t: int) -> None:
        """Deputy (PLAN 7.10): when the owner of a relay or contact I am deputy for goes past
        its lease, take it at once without an auction if I still can, else release it so the
        auction runs straight away instead of after the deputy grace."""
        a = self.a
        for task, r in sorted(a.table.recs.items()):
            if (r.state != CLAIMED or r.deputy != a.me or r.owner == a.me
                    or a.table.lease_ok(r.owner, task, t)):
                continue
            if self.can_bid(task, t):
                silent = (t - a.table.last_hb.get(r.owner, 0)) // 1000
                a.claim(task, self.cost(task), 0, f"USV {a.me:02d}: named backup, USV {r.owner:02d} "
                        f"silent {silent} s [deputy takeover]")
            else:
                a.release(task)

    # why (#86): a reason the shore can show, from facts this boat has when it claims --------
    def reason(self, task: str, t: int, bids: list[tuple[int, int]]) -> str:
        """Travel time, energy left after the task (model estimate) and the role it drops (#103)."""
        a = self.a
        lead = (f"USV {a.me:02d}: cheapest of {len(bids)} bids" if len(bids) > 1
                else f"USV {a.me:02d}: only bid")
        nxt = f" (USV {bids[1][1]:02d} +{hm(bids[1][0] - bids[0][0])})" if len(bids) > 1 else ""
        drops = [x for x in a.table.held_by(a.me) if kind(x) in DROPS.get(kind(task), ())]
        left = max(a.remaining_ms() - self.need_ms(task), 0)
        facts = (f"; {self.reach_ms(task) // 60_000} min away, battery ~{hm(left)} after, "
                 f"drops {', '.join(drops) or 'nothing'}")
        tag = f" [{self.why_open(task, t)}]"
        text = lead + nxt + facts + tag
        return text if len(text) <= WHY_MAX else lead + facts + tag

    def why_open(self, task: str, t: int) -> str:
        """Which rule made the task open, as this boat sees it before claiming."""
        a, r, k = self.a, self.a.table.recs[task], kind(task)
        if k == "contact":
            return "contact: nearest free boat"
        if k == "relay":
            silent = f" {(t - a.shore_t) // 1000} s" if a.shore_t >= 0 else ""
            return f"relay: no shore path{silent}"
        if r.state == CLAIMED:
            return "lease expired"
        p = a.peers.get(r.owner, (0, {}))[1]
        if r.owner and p.get("mode") in (RETURNING, UNAVAILABLE):
            return "battery return"
        if r.owner and any(kind(x) in ("relay", "contact") for x in p.get("roles", [])):
            return "handed over"
        if r.owner and r.owner != a.me and dict(a.mission.initial).get(task) == a.me:
            return "handed back"  # my original task, released to me by the boat that covered it
        if r.owner == a.me:
            return "back to my own task"
        if r.owner:
            return "rebalance"
        return "open task"

    # cost and eligibility ------------------------------------------------------------------
    def cycle_after(self, task: str) -> int:
        a = self.a
        return ms(a.tours.cycle_m(a.tours.insert(a.legs(), task)), a.v_plan())

    def reach_ms(self, task: str) -> int:
        a = self.a
        if kind(task) == "seg":
            return ms(a.tours.reach_m(a.pos, task), a.v_plan())
        if kind(task) == "contact":
            return ms(dist(a.pos, a.contacts.ring(task)), a.v_plan())
        return ms(dist(a.pos, a.station(task)), a.v_plan())

    def score(self, task: str, t: int) -> tuple[int, dict[str, int]]:
        """One score per option, in ms of bid (lower is better), with its named terms. The time
        term is the bid as measured; the cable-risk term is off unless config switches it on."""
        a, p = self.a, self.a.params
        terms = {"time": self.cost(task)}
        if kind(task) == "seg" and p.score_risk_permille:
            age = t - max(a.visits.oldest(task), 0)
            ships = sum(1 for k, o in sorted(a.contacts.tracks.items())
                        if not o["ais"] and not a.contacts.stale(k, t)
                        and o["sog"] <= p.loiter_sog_mm_s
                        and dist_to_line((o["x"], o["y"]), a.tours.pts[task]) <= NEAR_CABLE_M)
            risk = age * (1000 + ships * p.score_ships_permille) // 1000
            if task.split(":")[1] in p.data_cables:
                risk = risk * p.score_data_permille // 1000
            terms["cable risk"] = -risk * p.score_risk_permille // 1000
        return sum(terms.values()), terms

    def cost(self, task: str) -> int:
        a = self.a
        c = self.reach_ms(task) + 1_800_000 * (1000 - a.batt) // 1000
        if kind(task) == "seg":
            c += self.cycle_after(task)
            if a.holds("pick"):
                c += a.params.role_penalty_ms  # PLAN F3: cables before lane, but not for free
        if kind(task) == "contact" and a.holds("seg"):
            c += a.params.role_penalty_ms  # take a watcher from the lane before the cables
        return c

    def need_parts(self, task: str) -> tuple[int, int]:
        """Model estimate (ms at cruise) of the trip out (reach the task, do it once) and of the
        trip home by water from its far end, with the current this boat measures."""
        a = self.a
        k = kind(task)
        far = (a.tours.pts[task][-1] if k == "seg" else a.contacts.position(task)
               if k == "contact" else a.station(task))
        one_pass = ms(a.tours.len[task], a.v_plan()) if k == "seg" else 0
        return self.reach_ms(task) + one_pass, a.return_ms(far)

    def need_ms(self, task: str) -> int:
        out, back = self.need_parts(task)
        return out + back

    def energy_ok(self, task: str) -> bool:
        """Rule 12: the trip out, then the trip home with the same margin as the return rule 11
        (return_safety on the way home, plus the reserve). The margin is on the way home, the
        uncertain part (current, a slower boat); the way out is driven, and checked every tick by
        rule 11. Before, the margin also multiplied the way out, and no fresh boat could take the
        far end of the HVDC cable (seg:H:0) from Korsør."""
        p = self.a.params
        out, back = self.need_parts(task)
        return (self.a.remaining_ms() - p.reserve_ms
                >= out + p.return_safety_permille * back // 1000)

    def can_bid(self, task: str, t: int) -> bool:
        a = self.a
        k = kind(task)
        if t < self.gave.get(task, -1):
            return False
        if k == "seg":
            if a.table.recs[task].state == CLAIMED and not a.majority:
                return False  # taking over an expired claim needs a live majority (P4)
            return (not a.holds("relay") and a.mode != SHADOWING
                    and a.contacts.watching() is None and self.cycle_after(task) <= CYCLE_MAX
                    and self.energy_ok(task))
        if k == "pick":
            return not any(a.holds(x) for x in ("seg", "pick", "relay", "contact"))
        if k == "relay":
            # A relay reconnects a group: a lone boat out of range keeps its work instead.
            return (t - a.shore_t > SHORE_SILENCE and a.live_peers(t) >= 1
                    and self.energy_ok(task))
        if k == "contact":
            track = task.split(":", 1)[1]
            return (not a.holds("relay") and not self.last_sweeper(t)
                    and a.contacts.watching() is None and not a.contacts.done(task)
                    and a.contacts.tracks[track]["sog"] <= a.v_plan()
                    and self.energy_ok(task))
        return False  # cue tasks come with B's AIS replay (P1)

    def peer_fits(self, p: dict, task: str) -> bool:
        """Model estimate, from the peer's own heartbeat (position, battery), that it could do one
        pass of this segment and still get home with the same margin as energy_ok. No current."""
        a, prm = self.a, self.a.params
        pts = a.tours.pts[task]
        here = (p["x"], p["y"])
        v = prm.speed_mm_s
        out = ms(min(dist(here, pts[0]), dist(here, pts[-1])) + a.tours.len[task], v)
        back = ms(dist(pts[-1], a.mission.shore), v)
        left = p["batt"] * prm.endurance_ms // 1000 - prm.reserve_ms
        return left >= out + prm.return_safety_permille * back // 1000

    def last_sweeper(self, t: int) -> bool:
        """Never take the last boat sweeping cables off them (PLAN F7)."""
        a = self.a
        if not a.holds("seg"):
            return False
        return not any(t - tc <= PEER_STALE and any(kind(r) == "seg" for r in p["roles"])
                       for b, (tc, p) in a.peers.items() if b != a.me)


    # rebalance (PLAN 7.7 and F5) -------------------------------------------------------------
    def rebalance(self, t: int) -> None:
        """Hand one segment to a less loaded peer, at most once per period. Only boats that
        hold nothing but segments count as available: pickets and the relay are not idle."""
        a = self.a
        legs = a.legs()
        if len(legs) < 2 or any(a.table.is_open(k, t) and self.can_bid(k, t)
                                for k in a.table.recs):
            return
        avail = []
        for b, (tc, p) in sorted(a.peers.items()):
            if (t - tc <= PEER_STALE and p["mode"] not in (RETURNING, UNAVAILABLE, SHADOWING)
                    and all(kind(r) == "seg" for r in p["roles"])):
                avail.append((p["cyc"], b, p["tour"]))
        if not avail:
            return
        lo_cyc, lo, lo_tour = min(avail)
        mine = ms(a.tours.cycle_m(legs), a.v_plan())
        if mine * 1000 <= a.params.rebalance_ratio_permille * lo_cyc:
            return
        _, give = min((a.tours.cycle_m([leg for leg in legs if leg[0] != k]), k)
                      for k, _ in legs)
        if not self.peer_fits(a.peers[lo][1], give):
            return  # it could not take it: giving it away would only leave the cable open
        lo_legs = []
        for k in sorted(lo_tour + [give]):
            lo_legs = a.tours.insert(lo_legs, k)
        if ms(a.tours.cycle_m(lo_legs), a.v_plan()) < mine:
            a.release(give)
            self.gave[give] = t + REBALANCE  # don't win it straight back
