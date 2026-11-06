# Simeone's world implementation tracker

## Agreed scope

- Routes/loop/API landed via PR #12; hotel-load energy landed via PR #14.
- PRs #14 and #15 (boat contact policy) merged after combined local validation.
  Branch `b/current-tide` is rebased on main `32a7c54`; current changes stay in B's folders.
- Simeone owns the deterministic loop in `world/sim.py`; server wraps it (coordinate with Alexandru).
- Start with basic kinematic motion and a simple battery model; record deferred realism here.
- Agent owns return decisions and networking (forwarding, dedupe, retries, expiry, hop limit).
- World owns physical motion, sensor visibility, battery/current and radio delivery.
- Edit only B's folders, tests/world and config/{scene,boat,radio,energy}.toml.

## Ordered delivery

1. Implemented — routes: `load_scene(root)` returns immutable Scene with Mission, boundary and samples;
   `load_mission(root)` is the convenience integration entry point. Tests accompany the slice.
2. Implemented — motion: millimetre-state kinematics; previous actions apply next tick.
   Retains fractional metres at 2.3 m/s. Configured current is now enabled by default;
   `current_enabled=False` supplies an explicit zero-current control for regression tests.
3. Implemented — own sensors, range-limited synthetic contacts, low-battery injection and
   motors-off hotel load versus powered cruise drain. Power ratios are simulation assumptions.
4. Implemented — physical radio: range checks at send/delivery, directed link-off,
   counter-keyed loss/delay by seed/time/link/send ordinal. No global draw stream consumed
   by unrelated nodes. Baseline modes with different traffic still need fairness validation;
   this is not yet a pre-drawn shared channel tape.
5. Implemented — loop and scenario integration: events -> motion using previous actions -> radio delivery
   -> boat steps in ID order, then shore -> broadcasts -> evaluator/snapshot.
   No same-tick radio delivery. Reset reconstructs all state, queues and random generators.
6. Implemented basic fixed-current/tide reversal and SENTINEL drift/correction, with hotel
   versus powered energy. Agent return uses measured current; hull calibration is deferred.
7. AIS replay once Franco supplies the private clip and core is green. No CSV in git.
8. Cue/triage work only after features 1–25 are green and a full video exists.

## Current/tide milestone (current branch)

- Uniform current is loaded from B's energy config; bearing is the direction water flows
  toward. Runtime vectors are integer mm/s, reversed once at tide_flip_s.
- Motion integrates the old vector up to the reversal instant, splitting a tick if needed;
  sensors at that instant report the new vector. No one-tick-early reversal.
- World passes measured current to each agent and applies the same projected-current
  safety rule for the scripted low-battery injection. The agent still owns return decisions.
- SENTINEL drifts with motors off, then A's hysteresis commands powered correction.
  Tests verify both energy rates and station distance under the configured field.
- Synthetic contact SOG/course are already ground-relative and are NOT given extra drift.
- With main's boat contact phase, seed 1 detects C-07 locally on 02 at 7,859 s; 03 claims
  watch at 8,052 s; dwell/cannot_hold flags are produced. At evaluate: 01 is UNAVAILABLE,
  02/04 PATROL, 03/05 SENTINEL. This is one scenario check, not a benchmark or promise
  for other seeds. The full-world test asserts local detection, watcher, flags and release.
- Shore picture still has no contacts: #15 explicitly leaves shore contact/decision/alert
  presentation for A's next phase. The console contact story is therefore NOT complete.
- Old zero-current regressions explicitly disable current; they remain as control cases.
- Post-merge validation against main `32a7c54`: 130 tests pass in the full local suite;
  lint and targeted formatting pass. No merge conflicts or interface failures found.
  Separately re-ran all 14 C bridge compatibility cases from origin/c/sim-bridge `986cc45`,
  including the full tape schema check and localhost WebSocket test, against this world.
  No server/web files changed. These remote-branch checks are not part of the 128 count.
  Calibrated propulsion, wind, real forecasts, cross-OS validation and final seeded metrics
  remain deferred. No real-hull savings or complete contact story is claimed.

## PR #12 energy review follow-up (zero-current control)

- Javier confirmed seven segments and real-scene integration; #12 is merged.
- Added `hotel_load_permille=100` as a chosen simulation input, not calibrated hull power.
  Motors-off operation pays hotel load; powered transit/correction pays total cruise load.
  Fractional drain is retained; total cruise load includes hotel load (not counted twice).
- Seven-hour endurance stays unchanged. The eight-hour alternative needs a team decision.
- Seed 1 at 14,000 s: 03 remains operational and takes H:0..2 when 02 returns; 05 keeps relay.
  03 no longer returns just for sitting idle. **pick:N opens due to the takeover**: hotel load
  does not erase the sweeper's energy limit or magically close every gap.
- `/shore` uses A's merged `ShoreNode.picture(t_ms, speed)`; world.shore_view is raw diagnostics.
  Distinguish picture seconds/original report time from raw ms/local receipt time.
- At this prior checkpoint current/tide was deferred; the next section's status table
  and current/tide milestone above reflect the latest branch. Hull calibration remains deferred.
- Validation: full local suite 118 passing; lint and targeted formatting checks pass.
  Includes full seed-1 evaluation plus reset/re-run, fractional drain, correction-load and
  delivered ShoreNode.picture energy checks.

## Where Simeone stands against the ordered plan

| Work item | Status |
|---|---|
| Scene/Mission, <=5 km segmentation, samples | Implemented and tested; seven tasks documented |
| Basic motion and deterministic loop/reset | Implemented and tested against real Agent |
| Local synthetic sensors and battery injection | Implemented and tested |
| Physical radio and agent-owned multi-hop | Implemented; loss/link/rejoin/staleness tested |
| Console tick API / issue #8 | Implemented; C must wire the real bridge to this API |
| Motors-off hotel load / SENTINEL energy | Implemented in this follow-up; chosen ratio, not hull data |
| Fixed current/tide and drift-and-correct physics | Implemented on b/current-tide; chosen fixed field |
| Warm-state phases, shared channel fairness, final metrics | Needs coordination with Franco |
| AIS replay | Blocked on Franco supplying private clip |
| Cue/triage | Gated behind main features and full video |
| Contact response/operator policy | Boat policy tested with current; shore contact/decision picture still pending |

This is progress by deliverable, not a claim that timed team milestones or the whole
console demo are complete. Next: full bridge/contact integration with Javier/Alexandru as
those phases land, and baseline/warm-state coordination with Franco. Do not start triage yet.

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
- Contact policy is still a later A phase; shore command transport and picture() have now merged.
  A successful world run is not a completed challenge story.
- Latest actual-agent 14,400 s run completes all seven events, with five delivered boat
  reports at shore and boat 1 UNAVAILABLE near home. North boats later return on energy;
  no contact handling or patrol-gap closure is claimed from these results.
- Next: current/tide physics and cross-system contact integration. Coordinate seven-segment
  geometry and cold-start metric semantics with A and D before result collection.

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

- Real movement/auction/return, boat contact policy and shore decision transport are integrated;
  shore contact/auto-decision/alert presentation awaits A's next phase. Keep both real-core
  tests and stand-in physics tests.
- Default `python -m world` uses exercise controllers. `--controller core` runs real agents.
- Fixed current/tide and motors-off energy are now implemented with chosen inputs;
  real forecasts, hull-calibrated power and tide-aware waiting are not.
- Motion quantizes to millimetres per tick; fractional millimetres are not carried.
- Contact course vectors use trig once, quantized to mm/s. Cross-OS equality is unverified;
  explicit integer vectors are the fallback if CI finds differences.
- state_hash covers physical/queue state only, not external agent internals or all protocol
  state; a complete replay digest belongs to the integrated run logger.
- All five boats have initial positions, but the two sweepers move in the exercise controller;
  pickets and relay hold station. Tests also exercise all five moving.
- Low-battery injection caps charge at the agent's measured-current return threshold
  (home travel + reserve, times safety factor), not an arbitrary near-empty battery.
  Tests cover zero, aiding and opposing vectors. This is not a forecast-based route planner.
- Refined energy model (hotel/propulsion calibration), ECO, DORMANT and tide-aware waiting.
- Land/bridge/collision avoidance, waves, wind, autopilot dynamics and real current forecasts.
- Track correlation: synthetic track IDs stand in for cross-boat association, per contract.
- AIS clip unavailable locally; no real-data replay or triage claims.
- Multiple disconnected clipped cable components fail explicitly; a future scene needs an
  agreed task-ID policy before supporting them. No implicit straight-line joining.
- Warm-up phase variation and baseline fairness need integration with Franco's evaluator.
