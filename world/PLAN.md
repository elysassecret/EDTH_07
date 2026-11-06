# Simeone's world implementation tracker

## Agreed scope

- Branch `b/routes`: first small slice is routes, sampling and contract Mission construction.
- Simeone owns the deterministic loop in `world/sim.py`; server wraps it (coordinate with Alexandru).
- Start with basic kinematic motion and a simple battery model; record deferred realism here.
- Agent owns return decisions and networking (forwarding, dedupe, retries, expiry, hop limit).
- World owns physical motion, sensor visibility, battery/current and radio delivery.
- Edit only B's folders, tests/world and config/{scene,boat,radio,energy}.toml.

## Ordered delivery

1. Implemented — routes: `load_scene(root)` returns immutable Scene with Mission, boundary and samples;
   `load_mission(root)` is the convenience integration entry point. Tests accompany the slice.
2. Implemented — motion: millimetre-state kinematics; previous actions apply next tick.
   Retains fractional metres at 2.3 m/s. World currently runs with zero current.
3. Implemented — own sensors, range-limited synthetic contacts, basic uniform battery
   depletion and low-battery injection. Mode-specific drain remains deferred.
4. Implemented — physical radio: range checks at send/delivery, directed link-off,
   counter-keyed loss/delay by seed/time/link/send ordinal. No global draw stream consumed
   by unrelated nodes. Baseline modes with different traffic still need fairness validation;
   this is not yet a pre-drawn shared channel tape.
5. Implemented — loop and scenario integration: events -> motion using previous actions -> radio delivery
   -> boat steps in ID order, then shore -> broadcasts -> evaluator/snapshot.
   No same-tick radio delivery. Reset reconstructs all state, queues and random generators.
6. Fixed current/tide flip, mode-dependent battery drain and SENTINEL drift physics;
   integrate with the agent's safety return rule and station correction.
7. AIS replay once Franco supplies the private clip and core is green. No CSV in git.
8. Cue/triage work only after features 1–25 are green and a full video exists.

## Real-core integration milestone

- Fast-forwarded branch base to main `e0f345f` (auction phase), preserving B's local work.
- `--controller core` runs the merged Agent/ShoreNode against the real scene and physical
  channel. All five boats' heartbeats reach shore, including peer-hop northern reports.
- Added real-core tests: peer discovery, multi-hop shore delivery, directed link loss with
  peer fallback, stale reports after boat failure, shore isolation/rejoin and node reset.
- The merged real agent now moves, returns on low battery, and auctions released tasks.
  The actual seven-segment scene is tested through 7,300 s: boat 1 releases its work and
  remaining nodes converge on replacement cable owners. No hard-coded scratch winner.
- Issue #8 implemented: explicit tick/time API, seed reset, event lookahead, console injection
  aliases and logs, detached truth/shore views with original creation and local receipt times.
  See world/API.md for C's handoff. No server/web/contract edits.
- Local lint and full suite pass: 89 tests (includes upstream agent tests).
- Contact policy, operator command routing and ShoreNode.picture() are still later A phases.
  A successful world run is not a completed challenge story.
- Latest actual-agent 14,400 s run completes all seven events, with five delivered boat
  reports at shore and boat 1 UNAVAILABLE near home. North boats later return on energy;
  no contact handling or patrol-gap closure is claimed from these results.
- Next: current/tide physics and mode-dependent energy. Coordinate seven-segment geometry
  with A and D before result collection.

## Headless-world milestone

- `uv run ruff check .` and the full `uv run pytest -q` pass: 38 tests locally.
- `uv run python -m world --seconds 14400 --seed 1` completes all seven tape events;
  the exercise controller returns boat 1 near shore and marks it UNAVAILABLE.
- Reset/reconstruction, two hash seeds, radio link/range boundaries, sensor visibility,
  all-five movement and the full tape have automated coverage.
- This is a headless physical-world milestone, not proof of swarm repair or baseline gains.
- No changes to agent/, contract/, server/ or eval/ were needed.

## First-slice findings and assumptions

- Uses contract.geo's rounded integer-metre projection and the actual box corners in the JSON.
- Clips each selected public approximate cable; preserves source direction and bends;
  splits into equal-length pieces, rechecking the 5 km limit after coordinate rounding.
- Current committed scene produces **7 segments**, about **23.60 km** and **241 samples**.
  HVDC is just over 10 km after clipping, so needs three segments under the strict 5 km limit.
  This conflicts with the six-segment H:0..1 expectation in the older plans and A's scratch
  harness. Share with Javier/Franco: do not silently truncate the line or hard-code six tasks.
- Samples start at each segment's zero offset and repeat every 100 m, excluding the terminal
  endpoint. Each sample represents up to the next 100 m, with a shorter final remainder.
  Franco must use actual remainder lengths for km metrics, not assume every sample is 100 m.
- `lane_half_m = 750` is a chosen constant simulation band, not a surveyed boundary or a fit
  to the full P5/P95 envelope. The scene's end bins have broad asymmetric spreads; taking
  their maximum deviation as one constant band would put the configured stations in it.
  Stations are checked against this chosen band; no claim is made about land clearance.
- Cross-process hash-seed checks are local; cross-OS determinism still needs CI/two machines.

## Deferred / not implemented

- Real movement/auction/return core is integrated; contact policy and shore decision commands
  await Javier's later phases. Keep both real-core tests and stand-in physics tests.
- Default `python -m world` uses exercise controllers. `--controller core` runs real agents.
- Full current/tide integration and calibrated/mode-specific energy drain remain unimplemented.
- Basic battery model drains cruise-equivalent charge uniformly while enabled, including
  stationary time. It must not be used to claim SENTINEL endurance savings.
- Motion quantizes to millimetres per tick; fractional millimetres are not carried.
- Contact course vectors use trig once, quantized to mm/s. Cross-OS equality is unverified;
  explicit integer vectors are the fallback if CI finds differences.
- state_hash covers physical/queue state only, not external agent internals or all protocol
  state; a complete replay digest belongs to the integrated run logger.
- All five boats have initial positions, but the two sweepers move in the exercise controller;
  pickets and relay hold station. Tests also exercise all five moving.
- Low-battery injection caps charge at the agent's zero-current return threshold
  (home travel + reserve, times safety factor), not an arbitrary near-empty battery.
  Update this calculation alongside current integration; zero-current actual-agent return
  and task reallocation are now covered by the 7,300 s integration test.
- Refined energy model (hotel/propulsion calibration), ECO, DORMANT and tide-aware waiting.
- Land/bridge/collision avoidance, waves, wind, autopilot dynamics and real current forecasts.
- Track correlation: synthetic track IDs stand in for cross-boat association, per contract.
- AIS clip unavailable locally; no real-data replay or triage claims.
- Multiple disconnected clipped cable components fail explicitly; a future scene needs an
  agreed task-ID policy before supporting them. No implicit straight-line joining.
- Warm-up phase variation and baseline fairness need integration with Franco's evaluator.
