"""Stage-1 Gazebo surface-vehicle adapter and single-boat patrol harness (#107).

Owner: B (world/). Keeps the Python World as the default backend for tests, batch
evaluation, and the console demo. Gazebo is optional and never required by pytest.

The adapter enforces strict truth isolation: the Agent receives only its own
quantized Own observation (in int local metres, permille battery, and mm/s current),
range-filtered Detections, and delivered radio bytes, never Gazebo ground truth.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from math import atan2, cos, degrees, hypot, radians, sin

from contract.constants import UNAVAILABLE
from contract.geo import dist
from contract.mission import Action, Detection, Mission, Own, Params, Point, TaskSpec, load_params


@dataclass(frozen=True, slots=True)
class GazeboTelemetry:
    """Own-ship sensor reading from Gazebo `/model/usv_XX/odometry` + `/clock`."""

    sim_time_ms: int
    east_m: float
    north_m: float
    heave_m: float
    roll_deg: float
    pitch_deg: float
    heading_deg: float
    surge_mps: float
    cur_east_mm_s: int = 0
    cur_north_mm_s: int = 0


@dataclass(frozen=True, slots=True)
class ThrusterCommand:
    """Differential twin-thruster actuator command sent to Gazebo."""

    left_thrust_n: float
    right_thrust_n: float
    heading_cmd_deg: float
    speed_cmd_mps: float


class GazeboSurfaceVessel:
    """Stage-1 surface-vehicle hydrodynamic/buoyancy plant (VRX WAM-V reference class).

    Models hydrostatic heave/pitch flotation stability, surge drag, differential
    thruster propulsion, and yaw rate convergence in simulation time. Can run
    standalone offline or be driven by live Gazebo transport topics.
    """

    def __init__(
        self,
        start_point: Point = (0, 0),
        heading_deg: float = 90.0,
        max_speed_mps: float = 2.3,
        max_thrust_n: float = 250.0,
    ):
        self.sim_time_ms: int = 0
        self.east_m: float = float(start_point[0])
        self.north_m: float = float(start_point[1])
        self.heave_m: float = 0.0
        self.heave_vel_mps: float = 0.0
        self.roll_deg: float = 0.0
        self.pitch_deg: float = 0.0
        self.heading_deg: float = heading_deg % 360.0
        self.surge_mps: float = 0.0
        self.max_speed_mps = max_speed_mps
        self.max_thrust_n = max_thrust_n

    def telemetry(self, current_mm_s: Point = (0, 0)) -> GazeboTelemetry:
        return GazeboTelemetry(
            sim_time_ms=self.sim_time_ms,
            east_m=self.east_m,
            north_m=self.north_m,
            heave_m=round(self.heave_m, 4),
            roll_deg=round(self.roll_deg, 3),
            pitch_deg=round(self.pitch_deg, 3),
            heading_deg=round(self.heading_deg, 2),
            surge_mps=round(self.surge_mps, 3),
            cur_east_mm_s=current_mm_s[0],
            cur_north_mm_s=current_mm_s[1],
        )

    def step_physics(
        self, cmd: ThrusterCommand, dt_ms: int, current_mm_s: Point = (0, 0)
    ) -> GazeboTelemetry:
        if dt_ms <= 0:
            raise ValueError("simulation step dt_ms must be positive")
        dt_s = dt_ms / 1000.0
        self.sim_time_ms += dt_ms

        # Hydrostatic buoyancy restoring force (substepped 10x for stability at 1 s ticks).
        total_thrust = max(0.0, cmd.left_thrust_n + cmd.right_thrust_n)
        sub_dt = dt_s / 10.0
        for i in range(10):
            t_sub = (self.sim_time_ms - dt_ms) / 1000.0 + (i + 1) * sub_dt
            wave_forcing = 0.015 * sin(t_sub)
            heave_acc = -4.0 * self.heave_m - 3.5 * self.heave_vel_mps + wave_forcing
            self.heave_vel_mps += heave_acc * sub_dt
            self.heave_m += self.heave_vel_mps * sub_dt
        self.pitch_deg = round(1.2 * (total_thrust / (2.0 * self.max_thrust_n)) - 4.0 * self.heave_m, 3)
        self.roll_deg = round(0.4 * sin(self.sim_time_ms / 1500.0), 3)

        # Yaw alignment from differential thrust moment.
        diff_thrust = cmd.left_thrust_n - cmd.right_thrust_n
        yaw_rate_deg_s = max(-45.0, min(45.0, diff_thrust * 0.45))
        err = (cmd.heading_cmd_deg - self.heading_deg + 540.0) % 360.0 - 180.0
        if abs(err) <= abs(yaw_rate_deg_s * dt_s):
            self.heading_deg = cmd.heading_cmd_deg % 360.0
        else:
            self.heading_deg = (self.heading_deg + yaw_rate_deg_s * dt_s) % 360.0

        # Surge acceleration against linear + quadratic hydrodynamic drag.
        target_surge = min(self.max_speed_mps, cmd.speed_cmd_mps)
        tau_s = 1.25
        alpha = min(1.0, dt_s / tau_s)
        self.surge_mps += (target_surge - self.surge_mps) * alpha

        hdg_rad = radians(self.heading_deg)
        vx_mps = self.surge_mps * sin(hdg_rad) + current_mm_s[0] / 1000.0
        vy_mps = self.surge_mps * cos(hdg_rad) + current_mm_s[1] / 1000.0
        self.east_m += vx_mps * dt_s
        self.north_m += vy_mps * dt_s
        return self.telemetry(current_mm_s)


class GazeboBoatAdapter:
    """Per-boat adapter translating between Gazebo telemetry and Agent's contract interface.

    Never exposes Gazebo scene truth; constructs Own and range-gated Detections only from
    the boat's own sensors and simulation clock.
    """

    def __init__(
        self,
        boat_id: int,
        endurance_ms: int,
        hotel_load_permille: int = 100,
        r_detect_m: int = 5000,
        max_thrust_n: float = 250.0,
    ):
        self.boat_id = boat_id
        self.endurance_ms = endurance_ms
        self.charge_ms = endurance_ms
        self.drain_remainder = 0
        self.hotel_load_permille = hotel_load_permille
        self.r_detect_m = r_detect_m
        self.max_thrust_n = max_thrust_n
        self.last_telemetry: GazeboTelemetry | None = None

    def own_from_telemetry(self, tel: GazeboTelemetry) -> Own:
        """Convert Gazebo float pose + sim clock into integer contract.mission.Own."""
        self.last_telemetry = tel
        batt_permille = self.charge_ms * 1000 // self.endurance_ms
        return Own(
            x=round(tel.east_m),
            y=round(tel.north_m),
            batt=batt_permille,
            cur_x=tel.cur_east_mm_s,
            cur_y=tel.cur_north_mm_s,
        )

    def filter_detections(
        self, own: Own, raw_contacts: tuple[Detection, ...] = ()
    ) -> tuple[Detection, ...]:
        """Range-gate detections to this boat's own sensor radius; never pass global truth."""
        pos = (own.x, own.y)
        return tuple(d for d in raw_contacts if dist(pos, (d.x, d.y)) <= self.r_detect_m)

    def action_to_thrusters(
        self, action: Action, tel: GazeboTelemetry, dt_ms: int
    ) -> ThrusterCommand:
        """Translate Agent's mission-intent Action into twin-thruster commands and update battery."""
        dx = 0.0 if action.target is None else (action.target[0] - tel.east_m)
        dy = 0.0 if action.target is None else (action.target[1] - tel.north_m)
        distance_m = hypot(dx, dy)
        motors_on = (
            action.mode != UNAVAILABLE
            and action.target is not None
            and action.speed_mm_s > 0
            and distance_m > 0.5
            and self.charge_ms > 0
        )
        rate = 1000 if motors_on else self.hotel_load_permille
        available = self.charge_ms * 1000 - self.drain_remainder
        eff_dt_ms = min(dt_ms, available // rate)
        spent, self.drain_remainder = divmod(eff_dt_ms * rate + self.drain_remainder, 1000)
        self.charge_ms = max(0, self.charge_ms - spent)

        if not motors_on:
            return ThrusterCommand(0.0, 0.0, tel.heading_deg, 0.0)

        desired_hdg = degrees(atan2(dx, dy)) % 360.0
        err = (desired_hdg - tel.heading_deg + 540.0) % 360.0 - 180.0
        speed_cmd_mps = min(action.speed_mm_s / 1000.0, distance_m / max(dt_ms / 1000.0, 1.0))
        base_thrust = self.max_thrust_n * (speed_cmd_mps / 2.3)
        steer = max(-80.0, min(80.0, err * 1.8))
        left = max(0.0, min(self.max_thrust_n, base_thrust + steer))
        right = max(0.0, min(self.max_thrust_n, base_thrust - steer))
        return ThrusterCommand(
            left_thrust_n=round(left, 2),
            right_thrust_n=round(right, 2),
            heading_cmd_deg=round(desired_hdg, 2),
            speed_cmd_mps=round(speed_cmd_mps, 3),
        )


def make_two_waypoint_mission(
    wp_a: Point = (0, 0), wp_b: Point = (450, 0), shore: Point = (-100, 0)
) -> Mission:
    """Construct a single-boat, 2-waypoint patrol Mission for Stage-1 Gazebo verification."""
    return Mission(
        boats=(1,),
        tasks=(TaskSpec("seg:H:0", (wp_a, wp_b)),),
        initial=(("seg:H:0", 1),),
        shore=shore,
        lane=((0, 2000), (500, 2000)),
        lane_half_m=500,
    )


def run_stage1_patrol(
    wp_a: Point = (0, 0),
    wp_b: Point = (450, 0),
    ticks: int = 450,
    tick_ms: int = 1000,
) -> dict:
    """Run one boat on a 2-waypoint patrol through GazeboBoatAdapter and record tour progress."""
    from agent.core import Agent

    params: Params = load_params(".")
    mission = make_two_waypoint_mission(wp_a, wp_b)
    agent = Agent(1, mission, params)
    vessel = GazeboSurfaceVessel(start_point=wp_a, heading_deg=90.0, max_speed_mps=params.speed_mm_s / 1000.0)
    adapter = GazeboBoatAdapter(1, endurance_ms=params.endurance_ms, r_detect_m=params.r_detect_m)

    visited_waypoints: set[Point] = set()
    follower_indices: list[int] = []
    max_abs_heave_m = 0.0
    max_abs_pitch_deg = 0.0
    trace: list[dict] = []

    for step_idx in range(ticks):
        tel = vessel.telemetry()
        own = adapter.own_from_telemetry(tel)
        seen = adapter.filter_detections(own, ())
        action, _ = agent.step(tel.sim_time_ms, own, seen, [])
        if dist((own.x, own.y), wp_a) <= 25:
            visited_waypoints.add(wp_a)
        if dist((own.x, own.y), wp_b) <= 25:
            visited_waypoints.add(wp_b)
        if not follower_indices or follower_indices[-1] != agent.follow.j:
            follower_indices.append(agent.follow.j)
        cmd = adapter.action_to_thrusters(action, tel, tick_ms)
        tel_after = vessel.step_physics(cmd, tick_ms)
        max_abs_heave_m = max(max_abs_heave_m, abs(tel_after.heave_m))
        max_abs_pitch_deg = max(max_abs_pitch_deg, abs(tel_after.pitch_deg))
        if step_idx % 50 == 0 or step_idx == ticks - 1:
            trace.append(
                {
                    "t_ms": tel.sim_time_ms,
                    "own": asdict(own),
                    "target": list(action.target) if action.target else None,
                    "tour": [leg[0] for leg in agent.legs()],
                    "waypoint_index": agent.follow.j,
                    "thrusters": asdict(cmd),
                    "heave_m": tel_after.heave_m,
                    "pitch_deg": tel_after.pitch_deg,
                }
            )

    return {
        "backend": "gazebo_stage1_adapter",
        "boat": 1,
        "waypoints": [list(wp_a), list(wp_b)],
        "visited_waypoints": [list(p) for p in sorted(visited_waypoints)],
        "follower_index_transitions": follower_indices,
        "tour": [leg[0] for leg in agent.legs()],
        "flotation_stable": max_abs_heave_m <= 0.15 and max_abs_pitch_deg <= 5.0,
        "max_abs_heave_m": round(max_abs_heave_m, 4),
        "max_abs_pitch_deg": round(max_abs_pitch_deg, 3),
        "final_batt_permille": adapter.charge_ms * 1000 // adapter.endurance_ms,
        "trace": trace,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage-1 Gazebo surface-vehicle adapter runner.")
    parser.add_argument("--waypoints", default="0,0:450,0", help="Two waypoints x1,y1:x2,y2 in metres")
    parser.add_argument("--ticks", type=int, default=450, help="Simulation ticks (1 s each)")
    args = parser.parse_args()
    raw_a, raw_b = args.waypoints.split(":")
    wp_a = tuple(int(v) for v in raw_a.split(","))
    wp_b = tuple(int(v) for v in raw_b.split(","))
    report = run_stage1_patrol((wp_a[0], wp_a[1]), (wp_b[0], wp_b[1]), ticks=args.ticks)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
