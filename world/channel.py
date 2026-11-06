"""Pre-drawn channel tape: drop and delay per directed link per second.

Drawn once per seed with Generator.spawn, so adaptive and baseline modes
face identical radio weather even though they send different messages
(common random numbers, the fairness trick behind F1).
"""
from __future__ import annotations

import hashlib

import numpy as np


class ChannelTape:
    def __init__(self, nodes: list[int], n_seconds: int, t0_s: int, loss: float,
                 delay_s: tuple[float, float], rng: np.random.Generator):
        self.nodes = sorted(nodes)
        self.t0_s = t0_s
        self.n = n_seconds
        self.links: dict[tuple[int, int], int] = {}
        i = 0
        for a in self.nodes:
            for b in self.nodes:
                if a != b:
                    self.links[(a, b)] = i
                    i += 1
        child = rng.spawn(2)
        self.drop = child[0].random((i, n_seconds)) < loss
        lo, hi = delay_s
        self.delay_ms = (child[1].random((i, n_seconds)) * (hi - lo) + lo) * 1000.0
        self.delay_ms = self.delay_ms.astype(np.int32)

    def lookup(self, a: int, b: int, t_ms: int) -> tuple[bool, int]:
        col = (t_ms // 1000 - self.t0_s) % self.n
        row = self.links[(a, b)]
        return bool(self.drop[row, col]), int(self.delay_ms[row, col])

    def hash(self) -> str:
        h = hashlib.sha256()
        h.update(self.drop.tobytes())
        h.update(self.delay_ms.tobytes())
        return h.hexdigest()[:16]
