# world/ — owner: B

Owner: Simeone (B). See `world/PLAN.md` for delivery status, assumptions and deferred work.

## Python setup and Windows fallback (#51)

Keep the repository's Python **3.12** pin (`.python-version` and `requires-python`).
A reported pip run on 3.14 is not cross-platform lockfile/determinism validation; do not
relax the supported range just to bypass an installation-directory problem.

Install Python/dependencies while internet is available, before the offline demo check.
These setup commands are not a promise that uncached packages can be downloaded offline.
From the repository root, the normal setup is:

```bash
uv python install 3.12
uv sync --locked
uv run python --version
uv run pytest -q tests/smoke
```

If Windows reports `Missing expected target directory for Python minor version link`
while installing managed Python under `%APPDATA%`, Franco reports this workaround worked
on his laptop. In **PowerShell**, choose the per-user local installation directory first:

```powershell
$env:UV_PYTHON_INSTALL_DIR = Join-Path $env:LOCALAPPDATA "uv\python"
uv python install 3.12
uv sync --locked --python 3.12
uv run python --version
uv run pytest -q tests/smoke
```

Keep that environment variable in each terminal used for the demo. To make it persistent
for your user account (optional), run the following after the commands above:

```powershell
[Environment]::SetEnvironmentVariable("UV_PYTHON_INSTALL_DIR", $env:UV_PYTHON_INSTALL_DIR, "User")
```

New terminals inherit the persistent setting. Confirm `uv run python --version` reports
3.12 before proceeding. This workaround is a reported Windows installation fix, not a
claim that every Windows setup has the same problem. No deletion of existing Python
installations, administrator access, global pip installs or lockfile changes are required.
If it still fails, keep the error for the team and use the tested backup laptop rather than
silently switching Python versions on stage. Both laptops still need the actual offline check.

## Run the physical-world exercise

```bash
uv run python -m world --seconds 14400 --seed 1
uv run python -m world --controller core --seconds 14400 --seed 1
uv run pytest -q tests/world
uv run python -m world.check --jobs 4 > /tmp/edth-world-audit.json
```

The default uses explicitly labelled fixed-route stand-ins, **not Javier's swarm**.
`--controller core` uses the merged `agent.core.Agent` and `agent.shore.ShoreNode`.
The merged agent now moves boats, returns on low battery and runs the slotted auction.
Boat contact detection/response, delivered shore contacts/cards, oldest-first repair and
deputy takeover are merged. The world does not substitute exercise behaviour or truth
positions for missing radio reports. The bridge/UI restore rollout remains tracked in #63.
Both modes print a final truth snapshot and physical-state hash; neither is an evaluation
result. Core mode also prints public agent views and the heartbeats actually received by
shore (original creation times and hop counts), not a fabricated live fleet picture.

`world.check` runs cold seeded-position integration cases across seeds, speeds and policies;
it is **not eval/'s final benchmark**. See `world/VALIDATION.md` for the performed checks,
recording artifacts, known shore-semantic gaps and remaining release gates.

## Integrate

- `world.routes.load_scene(root)` -> Scene (Mission, boundary, coverage samples).
- `world.routes.load_mission(root)` -> contract Mission.
- `world.sim.World(root, seed, agent_factory, shore_factory)` owns the loop.
  Pass factories matching `Agent(me, mission, params)` and `ShoreNode(mission, params)`.
- `step(t_ms=None)` processes t=0 first, then advances by configured ticks. An explicit
  time must equal `next_tick_ms`. Returns evaluator truth; `t_ms` exposes the current time.
- `truth_view()` adds directed links, sample visits and cold-start segment ages.
- `shore_view()` returns only accepted delivered heartbeats, with receipt and creation times.
- `upcoming_event_times()` returns unprocessed event times in integer sim milliseconds.
- `inject(event, t_ms=None)` queues the next unprocessed tick by default. Explicit times
  must be future tick boundaries. Injection `kind`/fields match the scenario event tape.
- `reset(seed=None)` reconstructs physical state and all supplied nodes, clears injections,
  and optionally changes the seed. Sweepers start at deterministic seeded cable offsets;
  seed 1 preserves the original demo. Pickets/relay keep stations. No past visits are invented.
  `vary_start_phase=False` explicitly requests the legacy positions for a control run.
- `snapshot()` is **truth only**. For `/shore`, C uses `sim.shore.picture(sim.t_ms, speed)`
  (the agent's contract Snapshot). `shore_view()` stays a raw delivered-report diagnostic,
  not a second console picture. Do not substitute world truth for missing delivered data.
- `state_hash()` covers world physical/queue state, not a complete agent-state replay hash.

Physical radio checks range at send and delivery and applies directed link switches.
It never forwards, parses, retries or deduplicates payloads: those belong to `agent/net.py`.
Counter-keyed seeded loss/delay avoids a shared RNG consumed by unrelated transmissions;
full baseline fairness still needs Franco's cross-system tests.

Energy uses cruise-equivalent battery units. Moving under power pays total cruise load;
stationary/motors-off boats pay `hotel_load_permille` of it (100 is a chosen simulation
input, not measured hull data). SENTINEL correction pays cruise load, not the idle rate.
Seven-hour cruise endurance is unchanged. The configured uniform current now affects
motion and own sensors, reversing at `tide_flip_s`; bearing is where the water flows toward.
SENTINEL drifts until the agent commands correction. Use `World(..., current_enabled=False)`
only for an explicit no-current control. Real forecasts and calibrated hull physics remain deferred.

See `world/API.md` for the issue #8 console bridge handoff, units and data-age semantics.

Rule: only B edits files here. Others open an issue or ask in chat.
