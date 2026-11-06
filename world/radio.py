"""Range-limited broadcast radio with a delivery heap and a channel tape.

A send goes to every node inside range at send time, after the tape's drop
and delay. Delivery checks range again. Directed links can be cut (link_off)
and a failed boat neither sends nor receives. Messages are bytes only.
"""
from __future__ import annotations

import heapq
import math

from contract.constants import SHORE_ID

from .channel import ChannelTape


class Radio:
    def __init__(self, cfg: dict, tape: ChannelTape):
        r = cfg["radio"]
        self.boat_m = float(r["boat_m"])
        self.shore_m = float(r["shore_m"])
        self.max_bytes = int(r["max_bytes"])
        self.tape = tape
        self.heap: list[tuple[int, int, int, bytes]] = []
        self.seq = 0
        self.cut: set[tuple[int, int]] = set()
        self.positions: dict[int, tuple[float, float]] = {}
        self.silent: set[int] = set()
        self.inbox: dict[int, list[bytes]] = {n: [] for n in tape.nodes}
        self.stats = {"sent": 0, "dropped": 0, "delivered": 0, "out_of_range": 0, "oversize": 0}

    def range_m(self, a: int, b: int) -> float:
        return self.shore_m if SHORE_ID in (a, b) else self.boat_m

    def in_range(self, a: int, b: int) -> bool:
        pa, pb = self.positions.get(a), self.positions.get(b)
        if pa is None or pb is None:
            return False
        return math.hypot(pa[0] - pb[0], pa[1] - pb[1]) <= self.range_m(a, b)

    def link_ok(self, a: int, b: int) -> bool:
        return (a, b) not in self.cut and a not in self.silent and b not in self.silent and self.in_range(a, b)

    def send(self, t: int, src: int, data: bytes) -> None:
        if len(data) > self.max_bytes:
            self.stats["oversize"] += 1
            raise ValueError(f"message from {src} is {len(data)} bytes, cap {self.max_bytes}")
        if src in self.silent:
            return
        self.stats["sent"] += 1
        for dst in self.tape.nodes:
            if dst == src:
                continue
            if not self.link_ok(src, dst):
                self.stats["out_of_range"] += 1
                continue
            drop, delay = self.tape.lookup(src, dst, t)
            if drop:
                self.stats["dropped"] += 1
                continue
            self.seq += 1
            heapq.heappush(self.heap, (t + delay, self.seq, dst, data))

    def deliver(self, t: int) -> None:
        while self.heap and self.heap[0][0] <= t:
            _, _, dst, data = heapq.heappop(self.heap)
            if dst in self.silent:
                continue
            self.inbox[dst].append(data)
            self.stats["delivered"] += 1

    def take_inbox(self, node: int) -> list[bytes]:
        box = self.inbox[node]
        self.inbox[node] = []
        return box

    def graph(self) -> list[tuple[int, int]]:
        """Undirected usable links right now (both directions ok)."""
        out = []
        ns = self.tape.nodes
        for i, a in enumerate(ns):
            for b in ns[i + 1:]:
                if self.link_ok(a, b) and self.link_ok(b, a):
                    out.append((a, b))
        return out

    def shore_reach(self) -> dict[int, int]:
        """Hop count from shore for each node over usable links, or -1."""
        adj: dict[int, list[int]] = {n: [] for n in self.tape.nodes}
        for a, b in self.graph():
            adj[a].append(b)
            adj[b].append(a)
        hops = {n: -1 for n in self.tape.nodes}
        hops[SHORE_ID] = 0
        frontier = [SHORE_ID]
        while frontier:
            nxt = []
            for a in frontier:
                for b in sorted(adj[a]):
                    if hops[b] < 0:
                        hops[b] = hops[a] + 1
                        nxt.append(b)
            frontier = nxt
        return hops
