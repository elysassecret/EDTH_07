"""Chosen uniform current, reversing once at the configured tide time.

Direction is navigation degrees flowing TOWARD that bearing, not a weather 'from'
bearing. Quantize once at load; runtime movement and sensor values use mm/s integers.
This is a simulation input, not a Great Belt forecast or hydrodynamic model.
"""

from dataclasses import dataclass

from contract.mission import Point
from world.sensors import velocity


@dataclass(frozen=True, slots=True)
class Current:
    vector: Point
    flip_ms: int

    @classmethod
    def from_config(cls, config: dict) -> "Current":
        speed = config["current_mps"]
        direction = config["current_dir_deg"]
        flip_s = config["tide_flip_s"]
        if speed < 0 or not 0 <= direction < 360 or flip_s < 0:
            raise ValueError("current speed/time must be nonnegative; bearing must be in [0, 360)")
        return cls(velocity(round(speed * 1000), direction), round(flip_s * 1000))

    def at(self, t_ms: int) -> Point:
        if t_ms < 0:
            raise ValueError("simulation time must be nonnegative")
        return self.vector if t_ms < self.flip_ms else (-self.vector[0], -self.vector[1])

    def intervals(self, start_ms: int, end_ms: int) -> tuple[tuple[int, Point], ...]:
        """Split a motion interval exactly at reversal, including a non-aligned flip."""
        if not 0 <= start_ms <= end_ms:
            raise ValueError("current interval must be nonnegative and ordered")
        if start_ms < self.flip_ms < end_ms:
            return (
                (self.flip_ms - start_ms, self.at(start_ms)),
                (end_ms - self.flip_ms, self.at(self.flip_ms)),
            )
        return ((end_ms - start_ms, self.at(start_ms)),)
