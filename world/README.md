# world/ — owner: B

Owner: Simeone (B). See `world/PLAN.md` for delivery status, assumptions and deferred work.

## Run the physical-world exercise

```bash
uv run python -m world --seconds 14400 --seed 1
uv run python -m world --controller core --seconds 14400 --seed 1
uv run pytest -q tests/world
```

The default uses explicitly labelled fixed-route stand-ins, **not Javier's swarm**.
`--controller core` uses the merged `agent.core.Agent` and `agent.shore.ShoreNode`.
The merged agent now moves boats, returns on low battery and runs the slotted auction.
Shore decision transport is merged; contact detection/response policy is a later agent phase. The world does not
substitute exercise behaviour for missing agent features.
Both modes print a final truth snapshot and physical-state hash; neither is an evaluation
result. Core mode also prints public agent views and the heartbeats actually received by
shore (original creation times and hop counts), not a fabricated live fleet picture.

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
  and optionally changes the seed.
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
Seven-hour cruise endurance is unchanged. Current/tide integration remains deferred.

See `world/API.md` for the issue #8 console bridge handoff, units and data-age semantics.

Rule: only B edits files here. Others open an issue or ask in chat.
