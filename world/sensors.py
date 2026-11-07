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
    ship_type: str | None = None
    length_band_m: int | None = None

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

    def snapshot(self, standoff_m: int = 1852) -> dict:
        return {
            "track": self.id,
            "x": self.point[0],
            "y": self.point[1],
            "sog": self.speed_mm_s,
            "cog": self.course,
            "ais": self.ais,
            "standoff_m": standoff_m,
            "ship_type": self.ship_type,
            "length_band_m": self.length_band_m,
        }


def observe(
    point: Point,
    contacts: dict[str, Contact],
    radii: dict[str, int],
    ais_detections: tuple[Detection, ...] = (),
) -> tuple[Detection, ...]:
    camera_detections = tuple(
        contact.detection()
        for _, contact in sorted(contacts.items())
        if dist(point, contact.point) <= radii[contact.category]
    )
    if not ais_detections:
        return camera_detections
    seen_tracks = {det.track for det in camera_detections}
    return camera_detections + tuple(det for det in ais_detections if det.track not in seen_tracks)
