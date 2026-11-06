"""Basic point-boat physics; no land, collision or autopilot model."""

from dataclasses import dataclass
from math import isqrt

from contract.constants import UNAVAILABLE
from contract.mission import Action, Own, Point


@dataclass(slots=True)
class Boat:
    id: int
    x_mm: int
    y_mm: int
    charge_ms: int
    endurance_ms: int
    enabled: bool = True

    @classmethod
    def at(cls, boat_id: int, point: Point, endurance_ms: int) -> "Boat":
        return cls(boat_id, point[0] * 1000, point[1] * 1000, endurance_ms, endurance_ms)

    @property
    def point(self) -> Point:
        return round(self.x_mm / 1000), round(self.y_mm / 1000)

    def own(self, current: Point = (0, 0)) -> Own:
        return Own(*self.point, self.charge_ms * 1000 // self.endurance_ms, *current)

    def advance(self, action: Action, dt_ms: int, current: Point = (0, 0)) -> None:
        if dt_ms < 0 or action.speed_mm_s < 0:
            raise ValueError("time step and speed must be nonnegative")
        if not self.enabled or self.charge_ms == 0 or action.mode == UNAVAILABLE:
            return
        # Basic model: cruise-equivalent endurance drains uniformly while operating.
        dt_ms = min(dt_ms, self.charge_ms)
        self.charge_ms -= dt_ms
        if action.target is not None:
            dx = action.target[0] * 1000 - self.x_mm
            dy = action.target[1] * 1000 - self.y_mm
            distance = isqrt(dx * dx + dy * dy)
            travel = action.speed_mm_s * dt_ms // 1000
            if distance <= travel:
                self.x_mm, self.y_mm = action.target[0] * 1000, action.target[1] * 1000
            elif distance:
                self.x_mm += dx * travel // distance
                self.y_mm += dy * travel // distance
        self.x_mm += current[0] * dt_ms // 1000
        self.y_mm += current[1] * dt_ms // 1000
