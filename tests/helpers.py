"""Shared helpers: fast sims (no AIS) and a cache so story tests reuse one run."""
from __future__ import annotations

import functools

from contract.config import MODES, load, load_scenario
from eval.metrics import Metrics
from world.sim import Sim


def make_sim(mode: str = "elysa", seed: int = 1, use_ais: bool = False, overrides: dict | None = None,
             scenario: list | None = None, evidence: bool = False) -> tuple[Sim, Metrics]:
    ov = dict(MODES[mode])
    ov.update(overrides or {})
    cfg = load(overrides=ov)
    sim = Sim(cfg, mode=mode, seed=seed, scenario=scenario, use_ais=use_ais, evidence=evidence)
    m = Metrics(sim)
    sim.observers.append(m)
    return sim, m


@functools.lru_cache(maxsize=8)
def run_cached(mode: str, seed: int, until_s: int, use_ais: bool = False):
    sim, m = make_sim(mode, seed, use_ais=use_ais)
    sim.run_warm()
    sim.run_until(until_s)
    return sim, m


def events(sim, kinds=None, after_s: int = -10**9):
    out = []
    for b, a in sorted(sim.agents.items()):
        for t, k, body in a.events:
            if t >= after_s * 1000 and (kinds is None or k in kinds):
                out.append((t // 1000, b, k, body))
    return sorted(out, key=lambda r: (r[0], r[1]))
