"""Boat and vessel kinematics. 1 s tick, straight-line motion, no physics."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from contract.constants import KN_TO_MPS


@dataclass(slots=True)
class Boat:
    id: int
    x: float
    y: float
    speed_mps: float
    batt_s: int
    endurance_s: int
    mode: str = "PATROL"
    target: tuple[float, float] | None = None
    failed: bool = False          # chaos: dead hull, radio silent
    docked: bool = False          # reached shore after a return
    forced_return: bool = False   # hull battery monitor
    moved_m: float = 0.0
    tour: list = field(default_factory=list)

    @property
    def batt_permille(self) -> int:
        return max(0, min(1000, (1000 * self.batt_s) // max(1, self.endurance_s)))

    def step(self, dt_s: float, drain: bool) -> None:
        if self.failed or self.docked:
            return
        if self.target is not None:
            dx, dy = self.target[0] - self.x, self.target[1] - self.y
            d = math.hypot(dx, dy)
            step = self.speed_mps * dt_s
            if d <= step:
                self.x, self.y = self.target
                self.moved_m += d
            elif d > 0:
                self.x += dx / d * step
                self.y += dy / d * step
                self.moved_m += step
        if drain:
            self.batt_s = max(0, self.batt_s - int(dt_s))


@dataclass(slots=True)
class Vessel:
    """A synthetic surface contact. Never a real vessel."""
    id: str
    x: float
    y: float
    sog_kn: float
    course_deg: float
    ais: bool
    cls: str = "dusk"
    t_start: int = 0
    departed: bool = False

    @property
    def sog_mps(self) -> float:
        return self.sog_kn * KN_TO_MPS

    def step(self, dt_s: float) -> None:
        r = math.radians(self.course_deg)
        self.x += math.sin(r) * self.sog_mps * dt_s
        self.y += math.cos(r) * self.sog_mps * dt_s
