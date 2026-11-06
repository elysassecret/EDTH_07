"""One projection for agent, world and server. Owner: A.

Equirectangular about 55.40 N 11.00 E, as in data/scene-coordinates.json.
x east, y north, integer metres. lon/lat floats are for the map only.
"""
from math import isqrt

LAT0, LON0 = 55.40, 11.00
KX, KY = 63_212.0, 111_190.0  # metres per degree of longitude and latitude at LAT0


def to_xy(lat: float, lon: float) -> tuple[int, int]:
    return round((lon - LON0) * KX), round((lat - LAT0) * KY)


def to_lonlat(x: int, y: int) -> tuple[float, float]:
    return round(LON0 + x / KX, 6), round(LAT0 + y / KY, 6)


def dist(a: tuple[int, int], b: tuple[int, int]) -> int:
    dx, dy = a[0] - b[0], a[1] - b[1]
    return isqrt(dx * dx + dy * dy)
