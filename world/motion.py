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
    drain_remainder: int = 0  # fractional cruise-equivalent ms spent, in thousandths

    @classmethod
    def at(cls, boat_id: int, point: Point, endurance_ms: int) -> "Boat":
        return cls(boat_id, point[0] * 1000, point[1] * 1000, endurance_ms, endurance_ms)

    @property
    def point(self) -> Point:
        return round(self.x_mm / 1000), round(self.y_mm / 1000)

    def own(self, current: Point = (0, 0)) -> Own:
        return Own(*self.point, self.charge_ms * 1000 // self.endurance_ms, *current)

    def advance(
        self,
        action: Action,
        dt_ms: int,
        current: Point = (0, 0),
        hotel_load_permille: int = 1000,
        propulsion_permille: int = 1000,
        cruise_mm_s: int | None = None,
    ) -> None:
        if dt_ms < 0 or action.speed_mm_s < 0:
            raise ValueError("time step and speed must be nonnegative")
        if not 1 <= hotel_load_permille <= 1000:
            raise ValueError("hotel load must be between 1 and 1000 permille of cruise load")
        if not 0 <= propulsion_permille <= 1000:
            raise ValueError("propulsion effectiveness must be between 0 and 1000 permille")
        if not self.enabled or self.charge_ms == 0 or action.mode == UNAVAILABLE:
            return
        dx, dy = 0, 0
        if action.target is not None:
            dx = action.target[0] * 1000 - self.x_mm
            dy = action.target[1] * 1000 - self.y_mm
        distance = isqrt(dx * dx + dy * dy)
        motors_on = distance > 0 and action.speed_mm_s > 0
        # Total cruise load already includes hotel load; do not add it twice.
        rate = 1000 if motors_on else hotel_load_permille
        if motors_on and cruise_mm_s and action.speed_mm_s < cruise_mm_s:
            # below cruise, propulsion power falls with the cube of speed (displacement-hull rule
            # of thumb, config/energy.toml power_exponent; not hull data); the hotel load stays
            rate = power_rate(action.speed_mm_s, cruise_mm_s, hotel_load_permille)
        available = self.charge_ms * 1000 - self.drain_remainder
        requested_ms = dt_ms
        dt_ms = min(dt_ms, available // rate)
        spent, self.drain_remainder = divmod(dt_ms * rate + self.drain_remainder, 1000)
        self.charge_ms -= spent
        if dt_ms < requested_ms:
            # Exhausted within the tick: discard less than one ms of operating energy.
            self.charge_ms, self.drain_remainder = 0, 0
        if action.target is not None and action.speed_mm_s > 0:
            eff_speed = action.speed_mm_s * propulsion_permille // 1000
            travel = eff_speed * dt_ms // 1000
            if distance <= travel:
                self.x_mm, self.y_mm = action.target[0] * 1000, action.target[1] * 1000
                return
            if distance:
                self.x_mm += dx * travel // distance
                self.y_mm += dy * travel // distance
        self.x_mm += current[0] * dt_ms // 1000
        self.y_mm += current[1] * dt_ms // 1000


def power_rate(speed_mm_s: int, cruise_mm_s: int, hotel_load_permille: int) -> int:
    """Battery drain at a speed, permille of the cruise drain: hotel + propulsion * (v/v_c)^3.
    At cruise it is 1000, as before; at rest, the hotel load."""
    v = min(max(speed_mm_s, 0), cruise_mm_s)
    return hotel_load_permille + (1000 - hotel_load_permille) * v**3 // cruise_mm_s**3
