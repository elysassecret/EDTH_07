# edth07 — Elysa's Secret, EDTH Copenhagen 2026, Challenge 07

Five small USVs watch a 25 × 10 km box of the Great Belt (two power cables, a data cable, the lane). One watch officer on shore. No coordinator: every boat runs the same code and bids for work in a slotted auction; records merge by a fixed rule; leases catch dead boats; the shore console only sees what the radio delivered.

**Headline metric:** cable kilometres overdue at the end of the run (EDTH's "keep the gap in coverage as small as possible" in one number), always shown next to its cost, lane crossings in camera view. Three modes on identical inputs: `static` (pickets only), `off` (sweeps, no reassignment), `elysa` (sweeps plus reassignment).

## Run it

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pytest -q tests\smoke                       # must always pass on main
python -m tools.scene_check                 # Friday re-measure: lengths, stations, radio graph, return limits
python -m eval.run_batch                    # 3 modes x 5 seeds -> runs\<config-hash>\scorecard.md
python -m server.bridge --seed 1            # live demo: http://localhost:8000/ (dashboard), ws://localhost:8765/ws
python -m server.replay runs\<hash>\elysa_s1.jsonl   # re-run from seed + injections, check every state hash
python -m evidence.verify runs\<hash>\elysa_s1_evidence.json
pytest -q                                   # all acceptance tests (D1-D6, F1-F5, P1-P8, S1-S6, R1-R3), about 3 min
```

Data: `data/scene-coordinates.json` (public approximate cable lines from OSM, lane measured from one AIS day, stations) is committed. `data/ais-clip-box.csv` (anonymised AIS, 3 Nov 2026, inside the box) is **gitignored**: copy it in by hand and keep it inside the team. Without it the sim runs with AIS cues off.

## Layout

```
config/default.toml   every number, hashed into each run     scenarios/fixed.toml  the event tape
contract/             frozen: constants, messages, tasks (Rec + merge), views, config loader
agent/   (A)          core, table, auction, tour, relay, contact, cues, deputy, shore console. Imports contract only.
world/   (B)          geo, routes, motion, sensors, channel tape, radio, sim
eval/    (D)          metrics (ground truth), run_batch, report        tools/scene_check.py
server/  (C)          bridge (WebSocket + static), replay               web/  index.html map.js panels.js
ais/     (B)          replay of the clip, range-filtered per boat       evidence/  hash chain, Ed25519 heads, verifier
tests/                smoke, determinism, fairness, protocol, story (+ real scene)
```

## How the boats coordinate (one paragraph for a teammate)

Time is the shared sim clock in integer milliseconds. Every 5 s a boat broadcasts a heartbeat with its state, its whole task table and a summary of the peers it has heard; a heartbeat (or a peer's summary of you) renews your lease on all your tasks for 60 s. A task whose owner's lease expired, or that was released, is open. Every 12 s slot each boat bids once, on the first open task it is eligible for in the order relay, contact, cue, seg, pick, with cost = patrol cycle after cheapest insertion plus transit plus a battery term. At the next slot everyone closes the round with the bids it heard; the cheapest bid wins (tie: higher boat ID) and the winner publishes `Rec(task, ver+1, CLAIMED, bid, me, deputy)`. Records merge by `(ver, state, -bid, owner, deputy)`, highest wins, so a lost bid still resolves to the cheaper boat and a claim beats a release at equal version. Expiry takeovers of cable segments need a live majority (an isolated boat claims nothing). Every 300 s a boat whose cycle is 25% longer than the lightest peer releases one segment. Contact: a camera track with no AIS match, under 1 kn, over a cable for 180 s opens `contact:<id>`; the detecting scout holds it in view until the winner (nearest free boat, not the relay, not the last cable owner) reports it in view at 1 nm stand-off; faster than the boat means "cannot hold" and a queued report. Watching is pre-approved; closing inside stand-off waits for Approve; Stop is a VETOED record. Relay is a task too: a boat with no shore path for 30 s bids for it; relay and contact claims name a deputy who takes over without a bid round if the owner goes silent.

## Honesty rules

No invented results: every number on a slide comes from `eval/run_batch` (median and range over seeds). No hostile-intent claims: cues are "a cue for a look", the dark contact is synthetic and labelled. Gaps are shown openly: an uncovered picket stays on screen. Cable lines are public approximate routes, not surveyed. Radio ranges are modelled, nothing was measured. Detection never reads a name; only a pass within 500 m freshens a cable sample.

## What is real and what is modelled

Real: the box, the public cable lines, the lane measured from one AIS day, Korsør as the shore site, one day of anonymised AIS traffic replayed through range-limited receivers. Modelled: boat kinematics (2.3 m/s, no current, no land mask), radios (8 km boat, 14 km shore, 5% loss, 0.25 to 1 s delay, pre-drawn per link so all modes see the same weather), cameras (two radii: detect per class, verify 500 m), the dark contact. Not modelled: sea state, collision avoidance, the bridge, station-keeping.
