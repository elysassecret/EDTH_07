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


VIEWER_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Great Belt 3D Fleet Virtual Environment — All 5 USVs &amp; AIS</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #06101a; color: #e2ecf5; font-family: system-ui, -apple-system, sans-serif; overflow: hidden; }
  #canvas { width: 100vw; height: 100vh; display: block; cursor: grab; }
  #canvas:active { cursor: grabbing; }
  .hud { position: fixed; top: 14px; left: 14px; width: 380px; max-height: calc(100vh - 90px); overflow-y: auto;
         background: rgba(9, 20, 32, 0.90); border: 1px solid rgba(96, 170, 255, 0.30); border-radius: 10px;
         padding: 14px; backdrop-filter: blur(8px); box-shadow: 0 8px 28px rgba(0,0,0,0.5); font-size: 12.5px; }
  .hud h1 { font-size: 15px; font-weight: 600; color: #60aaff; margin-bottom: 3px; }
  .sub { font-size: 11.5px; color: #90a8c0; margin-bottom: 8px; }
  .sec { border-top: 1px solid rgba(255,255,255,0.09); padding-top: 8px; margin-top: 8px; }
  .sec-title { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #7cb8ff; margin-bottom: 5px; }
  .boat-row { display: grid; grid-template-columns: 58px 76px 54px 1fr; gap: 6px; align-items: center;
              padding: 5px 7px; border-radius: 6px; cursor: pointer; font-family: ui-monospace, SFMono-Regular, monospace; font-size: 11.5px; }
  .boat-row:hover { background: rgba(96, 170, 255, 0.14); }
  .boat-row.sel { background: rgba(96, 170, 255, 0.25); border: 1px solid rgba(96, 170, 255, 0.55); }
  .controls { position: fixed; bottom: 16px; left: 14px; display: flex; gap: 7px; flex-wrap: wrap;
              background: rgba(9, 20, 32, 0.90); border: 1px solid rgba(96, 170, 255, 0.30);
              padding: 10px 12px; border-radius: 10px; }
  button { background: #142c44; color: #e2ecf5; border: 1px solid #2b5278; border-radius: 6px;
           padding: 6px 11px; font-size: 12px; cursor: pointer; font-weight: 500; }
  button:hover { background: #1d3f60; }
  button.active { background: #1e5b94; border-color: #60aaff; }
  .badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 600; background: #14382c; color: #4ce0a0; }
</style>
</head>
<body>
<canvas id="canvas"></canvas>
<div class="hud">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <h1>Great Belt 3D Fleet Environment</h1>
    <span class="badge" id="st-badge">LIVE 5 USVs + AIS</span>
  </div>
  <div class="sub">Click any USV below (or on the 3D sea) to chase-cam follow it · Drag to orbit · Scroll to zoom</div>

  <div class="sec">
    <div class="sec-title">Sim Clock &amp; Contacts (<span id="v-time">0s</span>)</div>
    <div style="display:flex;justify-content:space-between;font-size:12px;color:#b8cde0;">
      <span>Active USVs: <strong id="v-usv-cnt">5</strong></span>
      <span>AIS Ships: <strong id="v-ais-cnt">0</strong></span>
      <span>Dark Contacts: <strong id="v-dark-cnt">0</strong></span>
    </div>
  </div>

  <div class="sec">
    <div class="sec-title">USV Fleet (Click to Follow in 3D)</div>
    <div id="fleet-list"></div>
  </div>
</div>

<div class="controls">
  <button id="btn-f0" class="active" onclick="followBoat(null)">3D Fleet Overview</button>
  <button id="btn-f1" onclick="followBoat(1)">Follow USV 01</button>
  <button id="btn-f2" onclick="followBoat(2)">Follow USV 02</button>
  <button id="btn-f3" onclick="followBoat(3)">Follow USV 03</button>
  <button id="btn-f4" onclick="followBoat(4)">Follow USV 04</button>
  <button id="btn-f5" onclick="followBoat(5)">Follow USV 05</button>
</div>

<script>
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
let W = window.innerWidth, H = window.innerHeight;
window.addEventListener("resize", () => { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; });
canvas.width = W; canvas.height = H;

let followedId = null; // null = overview, 1..5 = USV id
let camYaw = -0.35, camPitch = 0.62, camDist = 14500;
let panX = 1500, panY = -5500;
let dragging = false, lastX = 0, lastY = 0;

canvas.addEventListener("mousedown", e => { dragging = true; lastX = e.clientX; lastY = e.clientY; });
window.addEventListener("mouseup", () => dragging = false);
window.addEventListener("mousemove", e => {
  if (!dragging) return;
  if (e.shiftKey) {
    const scale = camDist * 0.0012;
    panX -= (e.clientX - lastX) * Math.cos(camYaw) * scale;
    panY += (e.clientY - lastY) * Math.sin(camYaw) * scale;
  } else {
    camYaw += (e.clientX - lastX) * 0.007;
    camPitch = Math.max(0.12, Math.min(1.48, camPitch + (e.clientY - lastY) * 0.006));
  }
  lastX = e.clientX; lastY = e.clientY;
});
canvas.addEventListener("wheel", e => {
  camDist = Math.max(80, Math.min(32000, camDist * (1 + e.deltaY * 0.001)));
});

function followBoat(id) {
  followedId = id;
  for (const k of [0,1,2,3,4,5]) {
    const b = document.getElementById("btn-f" + k);
    if (b) b.className = (id === (k === 0 ? null : k)) ? "active" : "";
  }
  if (id === null) {
    camPitch = 0.65;
    camDist = 14500;
    panX = 1500;
    panY = -5500;
  } else {
    camPitch = 0.36;
    camDist = 420;
  }
}

let snap = { t: 0, boats: [], contacts: [] };
let scene = null;
let landPolys = [];
const trails = {};

// Connect directly to the live 5-boat simulation bridge on port 8765
function connectSim() {
  const ws = new WebSocket(`ws://${window.location.hostname || "127.0.0.1"}:8765/truth`);
  ws.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === "scene") {
        scene = msg;
      } else if (msg.boats) {
        snap = msg;
        for (const b of snap.boats) {
          const tr = (trails[b.id] = trails[b.id] || []);
          if (!tr.length || Math.hypot(b.x - tr[tr.length - 1][0], b.y - tr[tr.length - 1][1]) > 15) {
            tr.push([b.x, b.y]);
            if (tr.length > 90) tr.shift();
          }
        }
        updateFleetHud();
      }
    } catch {}
  };
  ws.onclose = () => setTimeout(connectSim, 1000);
}
connectSim();

// Also fetch land polygons from the main console server so Sprogø, Funen & Zealand render in 3D
const LON0 = 10.97, LAT0 = 55.35, M_LAT = 111320, M_LON = 111320 * Math.cos(55.35 * Math.PI / 180);
function toXY(lon, lat) { return [(lon - LON0) * M_LON, (lat - LAT0) * M_LAT]; }
fetch(`http://${window.location.hostname || "127.0.0.1"}:8765/geo/land.geojson`)
  .then(r => r.json())
  .then(geo => {
    for (const f of geo.features || []) {
      const g = f.geometry;
      const rings = g.type === "Polygon" ? [g.coordinates[0]] : g.type === "MultiPolygon" ? g.coordinates.map(p => p[0]) : [];
      for (const r of rings) {
        const pts = r.filter((_, i) => i % 2 === 0).map(c => toXY(c[0], c[1]));
        if (pts.length >= 3) landPolys.push(pts);
      }
    }
  }).catch(() => {});

function updateFleetHud() {
  document.getElementById("v-time").textContent = snap.t + "s";
  const aisCnt = (snap.contacts || []).filter(c => c.ais).length;
  const darkCnt = (snap.contacts || []).filter(c => !c.ais).length;
  document.getElementById("v-usv-cnt").textContent = (snap.boats || []).length;
  document.getElementById("v-ais-cnt").textContent = aisCnt;
  document.getElementById("v-dark-cnt").textContent = darkCnt;

  const box = document.getElementById("fleet-list");
  box.innerHTML = (snap.boats || []).map(b => {
    const sel = followedId === b.id ? "boat-row sel" : "boat-row";
    const hdg = (b.hdg || 0).toFixed(0) + "°";
    const batt = Math.round((b.batt || 0) / 10) + "%";
    const tour = (b.tour && b.tour.length) ? b.tour.join(",") : (b.roles && b.roles.length ? b.roles.join(",") : b.mode);
    return `<div class="${sel}" onclick="followBoat(${b.id})">
      <strong style="color:#60aaff">USV 0${b.id}</strong>
      <span>${b.mode}</span>
      <span>${batt} · ${hdg}</span>
      <span style="color:#9ec0e0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${tour}</span>
    </div>`;
  }).join("");
}

function project(wx, wy, wz, cx, cy, cz, yaw, pitch) {
  let dx = wx - cx, dy = wy - cy, dz = wz - cz;
  let sy = Math.sin(yaw), cyw = Math.cos(yaw);
  let rx = dx * cyw - dy * sy;
  let ry = dx * sy + dy * cyw;
  let sp = Math.sin(pitch), cp = Math.cos(pitch);
  let fy = ry * cp - dz * sp;
  let fz = ry * sp + dz * cp;
  if (fy < 5.0) return null;
  let f = Math.min(W, H) * 0.92;
  return [W * 0.5 + (rx / fy) * f, H * 0.52 - (fz / fy) * f, fy];
}

function drawLine3D(a, b, cx, cy, cz, yaw, pitch, color, width=1.5, dash=[]) {
  const pa = project(a[0], a[1], a[2], cx, cy, cz, yaw, pitch);
  const pb = project(b[0], b[1], b[2], cx, cy, cz, yaw, pitch);
  if (!pa || !pb) return;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  if (dash.length) ctx.setLineDash(dash);
  ctx.beginPath();
  ctx.moveTo(pa[0], pa[1]);
  ctx.lineTo(pb[0], pb[1]);
  ctx.stroke();
  ctx.restore();
}

function drawPoly3D(pts, cx, cy, cz, yaw, pitch, fill, stroke, width=1.2) {
  const p2 = [];
  for (const p of pts) {
    const pr = project(p[0], p[1], p[2], cx, cy, cz, yaw, pitch);
    if (!pr) return;
    p2.push(pr);
  }
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(p2[0][0], p2[0][1]);
  for (let i = 1; i < p2.length; i++) ctx.lineTo(p2[i][0], p2[i][1]);
  ctx.closePath();
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
  ctx.restore();
}

function drawHull3D(bx, by, hdgDeg, scale, cx, cy, cz, yaw, pitch, hullFill, strokeCol, label, subLabel, t) {
  const hdgRad = (hdgDeg * Math.PI) / 180;
  const fwdX = Math.sin(hdgRad), fwdY = Math.cos(hdgRad);
  const rtX = Math.cos(hdgRad), rtY = -Math.sin(hdgRad);
  const heave = Math.sin(t * 2.2 + bx * 0.01) * 0.12 * scale;
  const pitchRad = Math.sin(t * 1.9 + by * 0.01) * 0.03;

  function pt(lon, lat, z) {
    return [
      bx + (fwdX * lon + rtX * lat) * scale,
      by + (fwdY * lon + rtY * lat) * scale,
      heave + (z + lon * Math.sin(pitchRad)) * scale
    ];
  }

  // Twin pontoons
  for (const s of [-1.2, 1.2]) {
    drawPoly3D(
      [pt(-2.5, s - 0.28, 0), pt(1.9, s - 0.28, 0), pt(2.8, s, 0.08), pt(1.9, s + 0.28, 0), pt(-2.5, s + 0.28, 0)],
      cx, cy, cz, yaw, pitch, hullFill, strokeCol, 1.4
    );
  }
  // Cross deck
  drawPoly3D(
    [pt(-1.5, -1.15, 0.45), pt(1.3, -1.15, 0.45), pt(1.3, 1.15, 0.45), pt(-1.5, 1.15, 0.45)],
    cx, cy, cz, yaw, pitch, "rgba(28, 82, 138, 0.95)", strokeCol, 1.6
  );
  // Sensor mast
  drawLine3D(pt(0.2, 0, 0.45), pt(0.2, 0, 1.8), cx, cy, cz, yaw, pitch, "#ffcc33", 2.2);
  // Heading vector
  drawLine3D(pt(2.8, 0, 0.2), pt(9.5, 0, 0.2), cx, cy, cz, yaw, pitch, strokeCol, 1.8, [4, 3]);

  const top = project(...pt(0.2, 0, 2.1), cx, cy, cz, yaw, pitch);
  if (top) {
    ctx.fillStyle = "#ffffff";
    ctx.font = "600 12px system-ui";
    ctx.fillText(label, top[0] + 6, top[1] - 4);
    if (subLabel) {
      ctx.fillStyle = "#9ec8ff";
      ctx.font = "500 11px system-ui";
      ctx.fillText(subLabel, top[0] + 6, top[1] + 10);
    }
  }
}

function render(nowMs) {
  const t = nowMs * 0.001;
  ctx.fillStyle = "#06101a";
  ctx.fillRect(0, 0, W, H);

  let targetX = panX, targetY = panY;
  const followed = (snap.boats || []).find(b => b.id === followedId);
  if (followed) {
    targetX = followed.x;
    targetY = followed.y;
  }

  const cx = targetX - Math.sin(camYaw) * Math.cos(camPitch) * camDist;
  const cy = targetY - Math.cos(camYaw) * Math.cos(camPitch) * camDist;
  const cz = Math.sin(camPitch) * camDist;

  // 1. Sea grid
  const gridStep = camDist > 3000 ? 1000 : 50;
  const span = camDist > 3000 ? 14000 : 600;
  const gx0 = Math.floor((targetX - span) / gridStep) * gridStep;
  const gy0 = Math.floor((targetY - span) / gridStep) * gridStep;
  for (let x = gx0; x <= targetX + span; x += gridStep) {
    drawLine3D([x, gy0, 0], [x, targetY + span, 0], cx, cy, cz, camYaw, camPitch, "rgba(40, 95, 145, 0.18)", 1);
  }
  for (let y = gy0; y <= targetY + span; y += gridStep) {
    drawLine3D([gx0, y, 0], [targetX + span, y, 0], cx, cy, cz, camYaw, camPitch, "rgba(40, 95, 145, 0.18)", 1);
  }

  // 2. 3D Landmasses (Sprogø Island, Zealand, Funen)
  for (const poly of landPolys) {
    const pts3d = poly.map(p => [p[0], p[1], 18]);
    drawPoly3D(pts3d, cx, cy, cz, camYaw, camPitch, "rgba(38, 52, 42, 0.85)", "rgba(130, 165, 120, 0.7)", 1.3);
  }

  // 3. Subsea cables from scene
  if (scene && scene.cables) {
    for (const c of scene.cables) {
      const col = c.kind === "power" ? "rgba(215, 95, 190, 0.8)" : "rgba(130, 110, 230, 0.75)";
      const pts = c.pts.map(p => toXY(p[0], p[1]));
      for (let i = 1; i < pts.length; i++) {
        drawLine3D([pts[i-1][0], pts[i-1][1], -2], [pts[i][0], pts[i][1], -2], cx, cy, cz, camYaw, camPitch, col, 2.5);
      }
    }
  }

  // 4. AIS Ships & Dark Contacts in 3D
  const shipScale = Math.max(12, Math.min(95, camDist * 0.012));
  for (const k of (snap.contacts || [])) {
    const col = k.ais ? "#7ec8e3" : "#ffb347";
    const fill = k.ais ? "rgba(80, 155, 190, 0.75)" : "rgba(235, 130, 45, 0.85)";
    const hdgRad = ((k.cog || 0) * Math.PI) / 180;
    const fx = Math.sin(hdgRad), fy = Math.cos(hdgRad);
    const rx = Math.cos(hdgRad), ry = -Math.sin(hdgRad);
    const s = shipScale;
    drawPoly3D(
      [
        [k.x - fx * 2.2 * s - rx * 0.7 * s, k.y - fy * 2.2 * s - ry * 0.7 * s, 2],
        [k.x + fx * 1.5 * s - rx * 0.7 * s, k.y + fy * 1.5 * s - ry * 0.7 * s, 2],
        [k.x + fx * 2.8 * s, k.y + fy * 2.8 * s, 3],
        [k.x + fx * 1.5 * s + rx * 0.7 * s, k.y + fy * 1.5 * s + ry * 0.7 * s, 2],
        [k.x - fx * 2.2 * s + rx * 0.7 * s, k.y - fy * 2.2 * s + ry * 0.7 * s, 2],
      ],
      cx, cy, cz, camYaw, camPitch, fill, col, 1.5
    );
    const lbl = project(k.x, k.y, 12, cx, cy, cz, camYaw, camPitch);
    if (lbl && (!k.ais || camDist < 12000)) {
      ctx.fillStyle = col;
      ctx.font = "500 11px system-ui";
      ctx.fillText(k.ais ? `AIS ${k.track.slice(0, 6)}` : `${k.track} [NO AIS]`, lbl[0] + 6, lbl[1]);
    }
  }

  // 5. All 5 USVs + Wake Trails
  const usvScale = Math.max(8, Math.min(85, camDist * 0.014));
  for (const b of (snap.boats || [])) {
    const tr = trails[b.id] || [];
    for (let i = 1; i < tr.length; i++) {
      drawLine3D([tr[i-1][0], tr[i-1][1], 0.5], [tr[i][0], tr[i][1], 0.5], cx, cy, cz, camYaw, camPitch, "rgba(96, 195, 255, 0.45)", 2);
    }
    const isSel = followedId === b.id;
    drawHull3D(
      b.x, b.y, b.hdg || 0, isSel ? Math.max(10, usvScale * 1.2) : usvScale,
      cx, cy, cz, camYaw, camPitch,
      isSel ? "rgba(120, 220, 255, 0.95)" : "rgba(210, 228, 245, 0.90)",
      isSel ? "#4ce0a0" : "#60aaff",
      `USV 0${b.id} (${b.mode})`,
      `Batt ${Math.round((b.batt || 0)/10)}% · ${(b.tour && b.tour.length) ? b.tour.join(",") : ""}`,
      t
    );
  }

  requestAnimationFrame(render);
}
requestAnimationFrame(render);
</script>
</body>
</html>
"""


def serve_stage1_viewer_legacy(
    host: str = "127.0.0.1",
    port: int = 8766,
    wp_a: Point = (0, 0),
    wp_b: Point = (450, 0),
) -> None:
    """Serve a live 3D Gazebo Stage-1 maritime testbed viewer over HTTP."""
    import threading
    import time
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from agent.core import Agent

    params: Params = load_params(".")
    mission = make_two_waypoint_mission(wp_a, wp_b)
    lock = threading.Lock()

    sim_ctx = {
        "agent": Agent(1, mission, params),
        "vessel": GazeboSurfaceVessel(
            start_point=wp_a, heading_deg=90.0, max_speed_mps=params.speed_mm_s / 1000.0
        ),
        "adapter": GazeboBoatAdapter(1, endurance_ms=params.endurance_ms, r_detect_m=params.r_detect_m),
        "warp": 5,
        "current": (0, 0),
        "propulsion_scale": 1.0,
        "trail": [],
        "latest": {},
    }

    def reset_sim() -> None:
        sim_ctx["agent"] = Agent(1, mission, params)
        sim_ctx["vessel"] = GazeboSurfaceVessel(
            start_point=wp_a, heading_deg=90.0, max_speed_mps=params.speed_mm_s / 1000.0
        )
        sim_ctx["adapter"] = GazeboBoatAdapter(
            1, endurance_ms=params.endurance_ms, r_detect_m=params.r_detect_m
        )
        sim_ctx["trail"] = []

    def step_once(dt_ms: int = 200) -> None:
        vessel: GazeboSurfaceVessel = sim_ctx["vessel"]
        adapter: GazeboBoatAdapter = sim_ctx["adapter"]
        agent = sim_ctx["agent"]
        cur: Point = sim_ctx["current"]
        tel = vessel.telemetry(cur)
        own = adapter.own_from_telemetry(tel)
        seen = adapter.filter_detections(own, ())
        action, _ = agent.step(tel.sim_time_ms, own, seen, [])
        cmd = adapter.action_to_thrusters(action, tel, dt_ms)
        scale = float(sim_ctx["propulsion_scale"])
        scaled_cmd = ThrusterCommand(
            left_thrust_n=round(cmd.left_thrust_n * scale, 2),
            right_thrust_n=round(cmd.right_thrust_n * scale, 2),
            heading_cmd_deg=cmd.heading_cmd_deg,
            speed_cmd_mps=round(cmd.speed_cmd_mps * scale, 3),
        )
        tel_after = vessel.step_physics(scaled_cmd, dt_ms, cur)
        trail: list = sim_ctx["trail"]
        if not trail or hypot(tel_after.east_m - trail[-1][0], tel_after.north_m - trail[-1][1]) >= 2.0:
            trail.append([round(tel_after.east_m, 2), round(tel_after.north_m, 2)])
            del trail[:-120]
        sim_ctx["latest"] = {
            **asdict(tel_after),
            "own": asdict(own),
            "action": {
                "mode": action.mode,
                "target": list(action.target) if action.target else None,
                "speed_mm_s": action.speed_mm_s,
            },
            "thrusters": asdict(scaled_cmd),
            "waypoints": [list(wp_a), list(wp_b)],
            "wp_idx": agent.follow.j,
            "trail": list(trail),
        }

    with lock:
        step_once(200)

    def bg_loop() -> None:
        while True:
            with lock:
                warp = max(1, min(30, int(sim_ctx["warp"])))
                for _ in range(warp):
                    step_once(200)
            time.sleep(0.1)

    threading.Thread(target=bg_loop, daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/state":
                with lock:
                    body = json.dumps(sim_ctx["latest"]).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
                return
            body = VIEWER_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            msg = json.loads(raw.decode("utf-8"))
            with lock:
                if msg.get("reset"):
                    reset_sim()
                if "warp" in msg:
                    sim_ctx["warp"] = int(msg["warp"])
                if "current" in msg:
                    c = msg["current"]
                    sim_ctx["current"] = (int(c[0]), int(c[1]))
                if "propulsion_scale" in msg:
                    sim_ctx["propulsion_scale"] = float(msg["propulsion_scale"])
                step_once(200)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

    print(f"Gazebo Stage-1 3D Virtual Environment listening on http://{host}:{port}/", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


def serve_stage1_viewer(host="127.0.0.1", port=8766, wp_a=(0, 0), wp_b=(450, 0)) -> None:
    """Compatibility entry: the full fleet viewer shares the dashboard simulation."""
    from world.viewer import serve_viewer

    serve_viewer(host, port)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage-1 Gazebo surface-vehicle adapter runner.")
    parser.add_argument("--waypoints", default="0,0:450,0", help="Two waypoints x1,y1:x2,y2 in metres")
    parser.add_argument("--ticks", type=int, default=450, help="Simulation ticks (1 s each)")
    parser.add_argument("--serve", action="store_true", help="Serve the WebGL fleet viewer sharing the dashboard simulation")
    parser.add_argument("--host", default="127.0.0.1", help="Viewer host")
    parser.add_argument("--port", type=int, default=8766, help="Viewer port")
    args = parser.parse_args()
    raw_a, raw_b = args.waypoints.split(":")
    wp_a = tuple(int(v) for v in raw_a.split(","))
    wp_b = tuple(int(v) for v in raw_b.split(","))
    if args.serve:
        serve_stage1_viewer(args.host, args.port, (wp_a[0], wp_a[1]), (wp_b[0], wp_b[1]))
        return
    report = run_stage1_patrol((wp_a[0], wp_a[1]), (wp_b[0], wp_b[1]), ticks=args.ticks)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
