# Console/evaluator handoff — issue #8

Owner: Simeone (B). Implemented in `world/sim.py`; server and WebSocket stay with C.

```python
from agent.core import Agent
from agent.shore import ShoreNode
from world.sim import World

sim = World(root=".", seed=1, agent_factory=Agent, shore_factory=ShoreNode)
sim.step(0)  # first tick, no motion interval before t=0
sim.step(sim.next_tick_ms)  # subsequently 1000, 2000, ... with current config
truth = sim.truth_view()
shore = sim.shore.picture(sim.t_ms, speed=240)  # contract Snapshot for /shore
raw_reports = sim.shore_view()  # diagnostic only
sim.inject({"kind": "battery_low", "a": 1})
sim.inject({"kind": "link_off", "a": 4, "b": "shore"})
next_events = sim.upcoming_event_times()
sim.reset(seed=2)  # next processed tick is zero again
```

## Timing

- `t_ms`: current integer simulation time, zero before/at the first step.
- `next_tick_ms`: next unprocessed tick, initially zero. `step()` and `step(next_tick_ms)`
  are equivalent. Skips, duplicate times and backwards explicit times raise ValueError.
- One call processes exactly one tick. C controls real-time scheduling/warp; world never
  reads wall-clock time or sleeps. Calls are serial, not concurrent.
- Order: apply events -> move using previous actions -> move synthetic contacts -> deliver
  due radio -> step boats in ID order -> shore -> schedule broadcasts -> sensor visit credit.
  Positive radio delay means nothing sent this tick can arrive this tick.
- `upcoming_event_times() -> list[int]`: sorted unique unprocessed scripted/injected times.
- `inject(event, t_ms=None)`: default is next unprocessed tick (t=0 before start, t+tick
  after a step). Never rewinds or modifies an already processed tick. Explicit times must
  be unprocessed tick boundaries. Log records the actual application `t_ms`.

## Truth (`truth_view() -> dict`)

Detached data, **not a contract Snapshot**. C maps domain fields to contract models.

- `t`, `seed`, `boats`, `contacts`, `events` match the physical snapshot.
- Boats: `id`, integer-metre `x/y`, map `lon/lat`, battery `batt` permille, measured current
  `cur_x/cur_y` mm/s (currently zero), `enabled`, action and mode, actual over-ground `sog`
  mm/s, `hdg` whole navigation degrees and remaining cruise-equivalent `endurance_ms`.
  Current point model has no independent bow attitude; hdg is course over ground and retains
  its last value when stopped. Initial heading is unknown, represented as zero.
- `contacts`: all synthetic world contacts, not just those detected. Positions integer metres,
  sog mm/s and course whole degrees. Presence in truth is NOT evidence of agent detection.
- `links`: directed `{a, b, up, blocked}` for boat IDs and shore ID 0. `up` is physical
  feasibility given current positions/charge/link switches. This is not an observed shore
  topology; do not leak it into /shore as live knowledge.
- `sample_visit_ms`: list aligned with `sim.scene.samples`; most recent physical verification
  visit time, or None if never visited. A boat must actually come within r_verify_m.
- `seg_age`: task -> worst sample age in **milliseconds**, or None if any sample is unvisited.
  Cold start is explicit: no invented warm ages. Franco owns final metric/baseline semantics;
  these local visit observations are not a replacement for his evaluation pipeline.
- `events`: applied tape entries plus `t_ms`, `origin` (scripted/injected) and `exercise`.
  Injected commands are copied into the queue, so mutating the caller's dict cannot edit them.

## Console shore picture versus raw diagnostics

For the console `/shore` channel, C uses **`sim.shore.picture(sim.t_ms, speed)`** from
Javier's merged ShoreNode. It returns the contract Snapshot, with its display times in
**seconds**, built from delivered protocol data. Pass sim time in **milliseconds**.
`sim.shore.command(sim.t_ms, cmd)` handles confirm/stop/approve/decline transport; physical
injections go to world. Contact behaviour still depends on A's later phase.

`shore_view()` is only a raw diagnostic with explicit creation/receipt timestamps in ms;
it must not become a competing console snapshot builder. Its receipt time differs from
`picture().boats[*].last_heard`, which uses the original report timestamp in seconds.
Do not interchange the units or timestamp meanings.

## Raw delivered shore (`shore_view() -> dict`)

`{"t": current_sim_ms, "boats": [report, ...]}` with IDs sorted. Initially empty.
Each report contains:

- `id`: boat ID;
- `reported_ms`: **original heartbeat creation time**, never refreshed by forwarding;
- `last_heard`: local receipt tick of the newest accepted heartbeat;
- `hops`: that heartbeat's protocol hop count (not a next-hop ID);
- `heartbeat`: the original delivered payload (x/y, mode, batt, cyc, tour, roles).

Data age is `t - reported_ms`; delivery delay is `last_heard - reported_ms`. A duplicate,
older report, or truth update does not refresh either timestamp. The returned structures
are detached copies. A cut direct link may still deliver a new report through a peer:
that is valid fresh data, not a reason to freeze all shore updates for that boat.

There is no invented heading, speed, via ID, coverage, or contact data at shore. The current
raw report is not the full console picture. `ShoreNode.picture/command` now supplies the
console contract view and decision transport; contact response awaits A's next phase.
Do not source missing fields from truth or treat default
contract values as measured observations. Decision answers stay with A/C, not world.

## Commands and reset

Accepted physical kinds: battery_low, boat_off, link_off, link_on, contact_start,
contact_depart, evaluate. `battery_low`/`boat_off` accept either scenario `boat` or console
`a`. Link commands use `a` and `b`, where `b` is a boat ID or "shore" (also ID 0).
Links are **directed**: disabling 4 -> shore does not disable shore -> 4.

`reset(seed=None)` clears receipts, visits, events, injection queue and channel state and
constructs fresh Agent/ShoreNode objects from the supplied factories. Scripted events are
restored. C must not retain old node references across reset. Pending commands should be
recreated from the event log for replay; reset alone intentionally discards injections.

`state_hash()` is a physical/queue diagnostic, not a complete integrated replay hash.
C/D should include `Agent.view()` and the remaining protocol state when defining replay.

## Geometry coordination

The committed public approximate routes yield seven cable tasks under the strict 5 km
limit, including H:0..2. Consume Mission.tasks dynamically; do not assume H has two tasks.
Total clipped route length is about 23.60 km. No land/collision avoidance is claimed.

## Energy assumption

Battery is remaining cruise-equivalent time. With `hotel_load_permille=100`, motors-off
operation consumes a chosen 100/1000 of total cruise load; moving under power, including
SENTINEL correction, pays total cruise load (hotel already included). Fractional drain is
carried across ticks. Arriving at a target during a tick conservatively pays cruise load
for that tick. A stationary target or a zero-speed command is motors-off regardless of
mode label. UNAVAILABLE/disabled boats draw nothing in this simplified dock/offline model.
This is not a calibrated power curve or a measured saving; sensors/radio stay on while idle.
Seven-hour endurance and safety reserve remain unchanged. Current/tide physics is still
not enabled, so this is not the full drift-and-correct energy demonstration yet.
