# Gazebo Stage-1 Maritime Testbed (`world/gazebo.py`)

Owner: **B** (`world/`). See `world/PRODUCT_BRIEF.md` ("Next-stage vision: a maritime testbed in Gazebo") and Issue **#107**.

> **Important boundary:** The fast deterministic Python `World` (`world/sim.py`) remains the default backend for unit tests, batch evaluation, and the offline console demo. Gazebo is an **optional** integration backend and is never required to run `uv run pytest`.

---

## 1. Pinned Software Stack (Offline-Capable)

| Component | Pinned Version | Purpose |
|---|---|---|
| **Gazebo Sim** | **Harmonic 8.6.0** (`gz-sim8`) | Rigid-body dynamics, surface buoyancy (`gz-sim-buoyancy-system`), hydrodynamics (`gz-sim-hydrodynamics-system`), and thruster plugins (`gz-sim-thruster-system`) |
| **Gazebo Transport** | `gz-transport13` (`13.4.0`) | Local pub/sub topics for `/clock`, `/model/usv_01/odometry`, and thruster commands |
| **VRX Reference Assets** | **VRX 2.3.0** (WAM-V / surface vessel parameters) | Reference hull mass, added-mass/damping coefficients, and twin-thruster geometry |
| **Python Bridge / Adapter** | Python `3.12` (`world/gazebo.py`) | Per-boat sensor/actuator adapter between Gazebo (or offline hydrodynamic hull model) and `contract/mission.py` (`Own`, `Detection`, `Action`) |

---

## 2. Offline Start Commands

### A. Self-Contained Stage-1 Patrol Verification (No External Network Required)
Runs one boat (`USV 01`) on a 2-waypoint patrol route through `GazeboBoatAdapter`, recording adapter observations, hull dynamics, and the agent's `tour` progress:

```bash
uv run python -m world.gazebo --waypoints "0,0:450,0" --ticks 450
```

### B. Headless Gazebo Harmonic Server (When `gz` Is Installed Locally)
Starts Gazebo in headless server mode (`-s`) with local cached models only (`GZ_SIM_RESOURCE_PATH` pointed at local models, no Fuel network fetches):

```bash
GZ_IP=127.0.0.1 \
GZ_SIM_RESOURCE_PATH="$PWD/world/gazebo_models" \
gz sim -s -r -v 2 world/gazebo_stage1.sdf
```

And attach the per-boat adapter to `usv_01`:

```bash
uv run python -m world.gazebo --connect-gz --model usv_01
```

---

## 3. Architecture & Strict Truth Isolation

```text
Agent (agent/core.py)
  │
  │ Action(mode, target=(x_m, y_m), speed_mm_s)
  ▼
GazeboBoatAdapter (world/gazebo.py)
  ├── Waypoint / Heading & Surge Controller
  │     └── Computes differential thruster commands (left_thrust_n, right_thrust_n)
  ├── Battery & Hotel-Load Integrator (world/motion.py rules)
  └── Observation Sanitizer (STRICT ISOLATION)
        └── Reads ONLY own-ship odometry + sim clock + range-gated detections
        └── Converts ENU float metres & sim ns -> Own(int m, int permille, int mm/s)
        └── NEVER exposes Gazebo ground-truth world state to the Agent
```

### Invariants Enforced by `GazeboBoatAdapter`
1. **Simulation Clock Only:** Time `t` passed to `Agent.step(t, own, seen, inbox)` comes exclusively from the simulation clock (`sim_time_ms`), never `time.time()`.
2. **Own-Sensor Boundary:** The adapter constructs `Own(x, y, batt, cur_x, cur_y)` from the boat's own noisy/measured odometry and onboard battery estimator, quantized to integer metres (`m`), permille (`0..1000`), and `mm/s`.
3. **Waypoint Following & Flotation Stability:** The surface-vessel dynamics verify bounded roll/pitch/heave (`|heave_m| <= 0.15 m`, `|pitch_deg| <= 5.0°`) and surge/yaw convergence across a 2-waypoint patrol tour.

---

## 4. Stage-2 Path: ArduPilot Rover SITL (Feature 40)

In Stage 2, the waypoint controller inside `GazeboBoatAdapter` is replaced by **ArduPilot Rover SITL** (`FRAME_CLASS = 2`, boat):
- `Agent` emits `Action(mode, target, speed_mm_s)`.
- Adapter sends `SET_POSITION_TARGET_LOCAL_NED` / guided waypoint over MAVLink UDP (`127.0.0.1:14550`).
- ArduPilot SITL drives Gazebo thrusters via `ardupilot_gazebo` (`fdm_port_in=9002`, `fdm_port_out=9003`).
