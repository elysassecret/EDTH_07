# server/ — owner: C

WebSocket bridge from sim to browser (`/shore` and `/truth`), replay, failure-injection commands.

Rule: only C edits files here. Others open an issue or ask in chat.

## Run the demo (one command, N3)

```bash
pnpm --dir web build                      # once, or after web/ changes
uv run python -m server --serve-web       # real sim + console on http://localhost:8765/
uv run python -m server --serve-web --mock   # same with the mock feed
```

## Files

- `feed.py`: WebSocket server shared by both sources. Steps the source at 10 Hz × warp,
  sends `/shore` and `/truth`, answers every command with an `ack`, serves `web/dist`.
- `bridge.py`: the real sim. `World` (Simeone) owns the ticks; `ShoreNode.picture()` (Javier)
  is sent on `/shore` unchanged; truth is mapped to a contract Snapshot for `/truth`.
  Answers go to `ShoreNode.command()`, failure injections to `World.inject()`.
  Only failure events (the exercise script and our injections) are added to `/shore`;
  synthetic contacts never are.
- `runlog.py` + `replay.py` (BUILD_PLAN step 13, test D3): the real sim writes one JSONL file
  per run to `runs/` (gitignored; `--no-log` turns it off). Line 1 is the header (seed, config
  hash, git commit, schema version); then every world event, every console command with the
  tick it arrived at, both snapshots every 10 sim-s and a replay hash every 60 sim-s. A full
  14 400 s run is about 8 MB. `uv run python -m server.replay runs/<file>.jsonl` rebuilds the
  run from the seed and the commands and names the first hash that differs.
- `evaluator.py`: the evaluator comparison, added by `feed.py` to **/truth frames only** (key
  `eval`): true vs last-known boat positions and data age, true contacts the shore picture lacks,
  links where truth and shore belief differ, true vs shore revisit age. /shore never carries it.
- `demo.toml` + `DEMO.md`: the video preset (`uv run python -m server --serve-web --demo`):
  seed 1, starts paused at 6900 s, relay loss injected at 11 100 s, about 2:26 after Run.
  Shot list, timings and narration in `DEMO.md`; `tests/server/test_demo.py` checks the beats.
- `narrator.py`: plain lines about what changed between consecutive /shore frames (task owners,
  modes, links, data age), e.g. "USV 04 took cable seg:G:0, seg:G:1; lane picket S now
  uncovered". Shore data only; it says "took", not why (the shore does not see bids). `feed.py`
  adds the latest lines to /shore frames as `narration`; the console shows them under
  "What changed".
- `mock_feed.py`: deterministic fake of the whole story, for UI work without the sim.
  `--tracks N` adds synthetic AIS-like tracks along the lane (labelled MOCK AIS, own random
  stream, so the story is unchanged) for the N4 load test:
  `uv run python -m server --serve-web --mock --tracks 240`. The evaluator view shows a frame
  readout (screen fps, feed frames/s, contacts).

  **Measured (7 Nov 2026, MacBook Pro M4, 24 GB, macOS 26.6.2):** 240 tracks at 240× auto:
  server frame 10.5 ms on average (150 frames, 1 h sim; budget 100 ms at 10 Hz); console in the
  Claude desktop browser pane: screen 120 fps, feed 9.5–10 frames/s, 240 contacts. Re-measure
  in Chrome on each demo laptop before quoting it.
- `alerts.py`: alerts for the real sim (feature 23), made from the shore picture and the
  console's own exercise events, never from truth. Alarm: held decision unanswered 05:00.
  Warning: held decision waiting; boat not heard for `stale_after_s`. Caution: no link,
  returning to Korsør, lane picket uncovered, exercise failure. One alert per id; `ack`
  marks it seen (an exercise-event alert goes away when acknowledged).

## mock_feed.py

```bash
uv run python -m server.mock_feed --port 8765 --seed 1
```

A deterministic fake of the swarm that plays `scenarios/fixed.toml` on the real geometry
(`data/scene-coordinates.json`, `config/*.toml`): boat 01 low battery at 7200 s, 04's shore link
cut at 7320 s, C-07 (camera only, no AIS) seen near 7500 s, keep-in-view and the 500 m look as
decision cards, "cannot hold" at 9200 s, link back at 10 800 s. Every number in it is a mock
input, not a sim result. Snapshots validate against `contract/views.py`
(`tests/server/test_mock_feed.py`).

Exercise injections on the real sim (`inject`): `battery_low`, `boat_off`, `link_off`/`link_on`
(any boat, any directed link) and `contact_start` with `lat`/`lon` (and optional `ais`): a
synthetic contact snapped to the nearest cable sample, with C-07's scripted speed and class;
truth only, so the shore learns of it only if a boat sees it. `boat_restore` switches a
switched-off boat back on: the same boat and agent, no reset or recharge (world/API.md, #63).

Evaluator scorecard (#59): `SimSource.scorecard()` reads D's `scorecard_console.json` (default
`runs/main/scorecard_console.json`, written by `uv run python -m eval.run_batch --out runs/main`;
`--scorecard PATH` picks another) and sends it on /truth only. No file, no scorecard: the panel
says it waits for eval/. `preliminary: true` shows PRELIMINARY next to the table.

Messages (JSON): `scene` once on connect (segment geometry, stations, `revisit_target_s` from
`config/run.toml`), then contract snapshots at
10 Hz, and an `ack` for every command. Commands: the contract's `confirm/stop/approve/decline`
and `inject`, plus mock-only `ack` (alert), `speed` (`value` or `"auto"`), `pause`, `reset`.

### Console extras: fields the console needs that the frozen contract lacks

Sent as extra keys (pydantic ignores them). To make them real they need a contract PR (A+B+C):

| Where | Field | Why the console needs it |
|---|---|---|
| Snapshot | `t0_utc` | show UTC "Z" times (feature 25, decision log) |
| Snapshot | `type` | tell snapshot / scene / ack apart on one socket |
| Boat | `hdg`, `sog_kn` | heading line and speed on the chart and cards |
| Boat | `via` | comms overlay: next hop toward shore (feature 21) |
| Boat | `heard` | a boat the shore never heard from has no real `last_heard` |
| Contact | `source` (`ais`/`camera`/`fused`), `name`, `trail` | feature 19 |
| Contact | `name_status`, `anchor_status` | "Name NOT READ, Anchor NOT SEEN" card text |
| Decision | `tier`, `actions` | Confirm/Stop vs Approve/Decline buttons (feature 22) |
| Decision | `route` | ghost-route preview (feature 22) |
| Decision | confirmed / stopped states | contract only has pending/approved/declined/delivered/expired |
| Event | `exercise` | EXERCISE banner on injected failures (feature 25) |
| Snapshot | `warp_mode`, `near_event` | warp display: auto/manual/paused, "slowing for event" (feature 25) |
| Link | `m` | link length, for the comms overlay |
