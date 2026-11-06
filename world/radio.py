"""Physical byte-broadcast channel only; agents own routing and protocol expiry."""

import hashlib
import heapq
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from contract.geo import dist
from contract.mission import Point


@dataclass(frozen=True, slots=True)
class RadioConfig:
    boat_m: int = 8000
    shore_m: int = 14000
    delay_min_ms: int = 250
    delay_max_ms: int = 1000
    loss_permille: int = 50

    def __post_init__(self):
        if not (0 <= self.loss_permille <= 1000):
            raise ValueError("loss must be between 0 and 1000 permille")
        if not (0 < self.delay_min_ms <= self.delay_max_ms):
            raise ValueError("radio delay must be positive and ordered")
        if min(self.boat_m, self.shore_m) <= 0:
            raise ValueError("radio ranges must be positive")


class Radio:
    def __init__(self, config: RadioConfig, seed: int):
        self.config = config
        self.seed = seed
        self.blocked: set[tuple[int, int]] = set()
        self.queue: list[tuple[int, int, int, int, bytes]] = []
        self.seq = 0
        self._send_counts: dict[tuple[int, int], int] = {}
        self._count_time: int | None = None

    def link(self, src: int, dst: int, on: bool) -> None:
        if on:
            self.blocked.discard((src, dst))
        else:
            self.blocked.add((src, dst))

    def reachable(self, src: int, dst: int, positions: Mapping[int, Point]) -> bool:
        radius = self.config.shore_m if 0 in (src, dst) else self.config.boat_m
        return (
            (src, dst) not in self.blocked
            and src in positions
            and dst in positions
            and dist(positions[src], positions[dst]) <= radius
        )

    def broadcast(self, t: int, src: int, raw: bytes, positions: Mapping[int, Point]) -> None:
        if not isinstance(raw, bytes):
            raise TypeError("radio accepts bytes only")
        if src not in positions:
            return
        if self._count_time != t:
            self._send_counts.clear()
            self._count_time = t
        for dst in sorted(positions):
            if dst == src:
                continue
            key = (src, dst)
            ordinal = self._send_counts.get(key, 0)
            self._send_counts[key] = ordinal + 1
            # Counter-keyed environmental randomness: unrelated transmissions never
            # consume this link's draws. Same tick/link/ordinal gets the same outcome.
            digest = hashlib.sha256(f"{self.seed}:{t}:{src}:{dst}:{ordinal}".encode()).digest()
            drop = int.from_bytes(digest[:8], "big") % 1000
            delay = self.config.delay_min_ms + int.from_bytes(digest[8:16], "big") % (
                self.config.delay_max_ms - self.config.delay_min_ms + 1
            )
            if drop < self.config.loss_permille or not self.reachable(src, dst, positions):
                continue
            self.seq += 1
            heapq.heappush(self.queue, (t + delay, self.seq, src, dst, raw))

    def deliver(self, t: int, positions: Mapping[int, Point]) -> dict[int, list[bytes]]:
        inbox: dict[int, list[bytes]] = defaultdict(list)
        while self.queue and self.queue[0][0] <= t:
            _, _, src, dst, raw = heapq.heappop(self.queue)
            if self.reachable(src, dst, positions):
                inbox[dst].append(raw)
        return dict(inbox)
