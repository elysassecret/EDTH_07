# Connecting real boats: plan for features 39 and 40 (owner: C, with A and B)

**Status: a plan, not built.** Nothing in this repo talks to an autopilot or an external COP
today. This page is for the jury and for the team: what we would connect, where, and how we
would prove each step. Issues: #105 (independent runtimes), #107 (Gazebo stage 1).

## The one seam that makes it possible

Every boat's brain already has one narrow interface (`agent/core.py`, types in
`contract/mission.py`):

```text
Agent.step(t_ms, Own, detections, radio_inbox) -> (Action, radio_outbox)
  Own       = own position (local metres), battery (permille), measured current
  Action    = mode, target point (or None = drift), speed (mm/s)
```

The agent never sees the world, the evaluator or the server. In the simulator, `world/` fills
`Own` and carries out `Action`. On a real boat, an **adapter** does the same job against the
autopilot. The swarm logic, the auction and the shore console stay unchanged.

```text
                      on the boat                                  on shore
 ┌────────────────────────────────────────────────────┐     ┌──────────────────────────┐
 │ Agent (A) ── Action ──> MAVLink adapter ──> ArduPilot│     │ ShoreNode (A) ── server/ │
 │   ^                          │   Rover (boat frame)  │     │   (C) ── console (C)     │
 │   └── Own, detections <──────┘   + its own safety    │     │        └─ COP API (39)   │
 │   radio in/out <──────────── boat radio ─────────────┼─────┼─> shore radio            │
 └────────────────────────────────────────────────────┘     └──────────────────────────┘
```

## Feature 40: MAVLink bridge to one ArduPilot SITL boat

Target: **ArduPilot Rover in its boat frame, run as SITL** (software in the loop) on a laptop,
spoken to with `pymavlink`. One boat first. The other four stay simulated, so the swarm still
has peers.

| Agent side | MAVLink side (ArduPilot Rover) |
|---|---|
| `Own.x, Own.y` | `GLOBAL_POSITION_INT` lat/lon → local metres with the same projection as `contract/geo.py` |
| `Own.batt` | `BATTERY_STATUS` remaining (%) → permille |
| `Own.cur_x, cur_y` | not measured by the autopilot: 0 until a current sensor or estimate exists (say so) |
| `Action.target`, `speed_mm_s` | GUIDED mode, `SET_POSITION_TARGET_GLOBAL_INT` to the target and `MAV_CMD_DO_CHANGE_SPEED` |
| `Action.target = None` (drift) | HOLD mode |
| detections | none from the autopilot; camera stays simulated until a real detector exists |
| time | the adapter passes integer sim/wall ms in; the agent still never reads a clock itself |

Rules the adapter keeps:
- **The autopilot owns navigation safety.** Geofence, failsafes and collision avoidance stay
  in ArduPilot and on the boat. The agent only says where to go next; it can never switch those off.
- **Every command needs an answer.** The adapter waits for `COMMAND_ACK` and checks the
  boat's reported mode. A missing answer is reported as "not confirmed", never retried in a loop.
- **Lost telemetry is reported as lost.** If heartbeats stop, the agent gets no new `Own`. It
  goes stale the same way a silent boat does on the console today.

**Proof for the jury (demo step):** start SITL, start the adapter for USV 03, run the other
four in the simulator. Approve the C-07 "close for a look" card on the console, then show the
SITL boat's mode go to GUIDED, its position move toward the target, and the console's USV 03
card update from the delivered reports. Then stop SITL, and show USV 03 turning grey with a
growing "could be within" circle (#111) while the other boats carry on.

## Feature 39: integration API for an external COP (Blue Shadow type)

The console already gets exactly what an external COP would want: delivered tracks, boat
states, tasks, alerts and decisions, as the shore received them (`/shore`, see
`contract/views.py`). Feature 39 is a read-only export of that same shore picture:

- **What:** contacts (track, position, speed, course, AIS or camera only, last seen, who saw
  it), boats (position, mode, task in words, last heard), open decisions and alerts. Always the
  shore view, never `/truth`.
- **How:** a separate read-only WebSocket or HTTP endpoint in `server/` that sends the same
  JSON we already validate against `contract/schema.json`. A mapping layer to the partner's
  format (NMEA TTM/TLL targets, or their own API) sits outside the agent.
- **Never:** commands in through this door. Operator answers stay on the console with review,
  a five-second undo and a recorded acknowledgment.
- **Honesty carries over:** each item keeps its "last seen / last heard" time, so a COP
  cannot show an old report as live.

## Gazebo (B's stage 1) and how it fits

Gazebo is a richer simulated sea for the **same** adapter idea: `world/` would feed `Own` from
Gazebo instead of the Python motion model. With ArduPilot SITL plugged into Gazebo, the path
becomes agent → adapter → ArduPilot SITL → Gazebo boat. The Python world stays the default for
tests, batch evaluation and the offline demo. See #107.

## Order of work and what each step proves

| Step | Who | Proves |
|---|---|---|
| 1. Adapter against one SITL boat, other four simulated | A + C | The brain drives a real autopilot interface |
| 2. Agents as separate processes (#105) | A + B + C | A boat keeps working without shore or peers |
| 3. Read-only COP export (39) | C | The shore picture plugs into a partner's system |
| 4. SITL inside Gazebo (#107) | B | Decisions hold with real vessel motion and disturbance |
| 5. One supervised real boat | all, with the boat's operator | Only after 1–4, with the operator's own safety case |

## Questions we still need answered (ask Blue Shadow)

- Which autopilot and link do their boats use (ArduPilot/PX4 over MAVLink, or a vendor API)?
- How often do they get position and battery from a boat at sea, and over what radio?
- Which track format does their COP take in (NMEA, ASTERIX, their own API)?
