"""Synthetic camera contacts; track IDs stand in for correlation by agreement."""

from dataclasses import dataclass
from math import cos, radians, sin

from contract.geo import dist
from contract.mission import Detection, Point


def velocity(speed_mm_s: int, course_deg: int) -> Point:
    """Navigation course: clockwise from north; quantize once to integer mm/s."""
    return round(speed_mm_s * sin(radians(course_deg))), round(
        speed_mm_s * cos(radians(course_deg))
    )


@dataclass(slots=True)
class Contact:
    id: str
    x_mm: int
    y_mm: int
    speed_mm_s: int
    course: int
    ais: bool
    category: str
    vx: int = 0
    vy: int = 0
    updated_ms: int = 0

    def set_velocity(self, speed_mm_s: int, course: int):
        self.speed_mm_s, self.course = speed_mm_s, course
        self.vx, self.vy = velocity(speed_mm_s, course)

    def advance(self, t: int):
        dt = t - self.updated_ms
        self.x_mm += self.vx * dt // 1000
        self.y_mm += self.vy * dt // 1000
        self.updated_ms = t

    @property
    def point(self) -> Point:
        return round(self.x_mm / 1000), round(self.y_mm / 1000)

    def detection(self) -> Detection:
        return Detection(self.id, *self.point, self.speed_mm_s, self.course, self.ais)


def observe(
    point: Point, contacts: dict[str, Contact], radii: dict[str, int]
) -> tuple[Detection, ...]:
    return tuple(
        contact.detection()
        for _, contact in sorted(contacts.items())
        if dist(point, contact.point) <= radii[contact.category]
    )
