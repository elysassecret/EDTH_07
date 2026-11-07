"""Agent <-> world interface: mission, parameters, sensor inputs, actions. Owner: A.

B builds `Mission` in world/routes.py. The agent never reads files or the clock: it gets
`Mission` and `Params` at construction, and `Own`, `Detection`s and inbox bytes every tick.
Units: int metres (contract/geo.py frame), int ms, battery permille, speed mm/s.
"""
import tomllib
from dataclasses import dataclass
from pathlib import Path

Point = tuple[int, int]
FAILURES = ("battery_low", "link_off", "boat_off")


@dataclass(frozen=True, slots=True)
class TaskSpec:
    id: str  # "seg:H:0", "pick:N", "relay"
    pts: tuple[Point, ...]  # seg: polyline (>= 2 points); pick, relay: one point


@dataclass(frozen=True, slots=True)
class Mission:
    boats: tuple[int, ...]  # (1, 2, 3, 4, 5)
    tasks: tuple[TaskSpec, ...]  # fixed order
    initial: tuple[tuple[str, int], ...]  # (task_id, owner) at t = 0
    shore: Point
    lane: tuple[Point, ...]  # measured centreline
    lane_half_m: int  # band half-width for the keep-out


@dataclass(frozen=True, slots=True)
class Params:
    speed_mm_s: int
    endurance_ms: int
    reserve_ms: int
    r_verify_m: int
    keep_in_view_m: int
    standoff_m: int
    standoff_floor_m: int
    sentinel_radius_m: int
    return_safety_permille: int
    seg_lease_ms: int
    role_penalty_ms: int
    rebalance_ratio_permille: int
    loiter_sog_mm_s: int
    policy: str  # elysa | off | static
    repair_off_after_ms: int  # first failure event in the scenario; same in every mode
    r_detect_m: int = 5000  # camera detect radius for ship-class target under scene light (m)
    health_window_ms: int = 120_000  # health check (#106), see config/agent.toml
    health_min_permille: int = 500
    health_recover_permille: int = 800
    health_fails: int = 2
    health_attempts: int = 3


@dataclass(frozen=True, slots=True)
class Own:
    """This boat's own sensors."""
    x: int
    y: int
    batt: int  # permille of full charge
    cur_x: int = 0  # measured current, mm/s (feature 15)
    cur_y: int = 0


@dataclass(frozen=True, slots=True)
class Detection:
    """A camera detection the world says this boat can see."""
    track: str  # sim track ID stands in for cross-boat correlation (disclosed)
    x: int
    y: int
    sog: int  # mm/s
    cog: int  # degrees
    ais: bool


@dataclass(frozen=True, slots=True)
class Action:
    mode: str
    target: Point | None  # None = motors off, drift
    speed_mm_s: int


def load_params(root: str | Path = ".", scenario: str = "scenarios/fixed.toml") -> Params:
    root = Path(root)

    def toml(name):
        with open(root / name, "rb") as f:
            return tomllib.load(f)

    boat, energy = toml("config/boat.toml"), toml("config/energy.toml")
    agent, tape = toml("config/agent.toml"), toml(scenario)
    failures = [e["t"] for e in tape.get("event", []) if e["kind"] in FAILURES]
    return Params(
        speed_mm_s=round(boat["speed_mps"] * 1000),
        endurance_ms=boat["endurance_s"] * 1000,
        reserve_ms=boat["reserve_s"] * 1000,
        r_verify_m=boat["r_verify_m"],
        keep_in_view_m=boat["keep_in_view_m"],
        standoff_m=boat["standoff_m"],
        standoff_floor_m=boat["standoff_floor_m"],
        sentinel_radius_m=energy["sentinel_radius_m"],
        return_safety_permille=round(energy["return_safety"] * 1000),
        seg_lease_ms=agent["seg_lease_s"] * 1000,
        role_penalty_ms=agent["role_penalty_s"] * 1000,
        rebalance_ratio_permille=round(agent["rebalance_ratio"] * 1000),
        loiter_sog_mm_s=agent["loiter_sog_mm_s"],
        policy=agent["policy"],
        repair_off_after_ms=min(failures) * 1000 if failures else 0,
        r_detect_m=boat["r_detect_m"]["ship_day"],
        health_window_ms=agent["health_window_s"] * 1000,
        health_min_permille=round(agent["health_min_progress"] * 1000),
        health_recover_permille=round(agent["health_recover"] * 1000),
        health_fails=agent["health_fails"],
        health_attempts=agent["health_attempts"],
    )
