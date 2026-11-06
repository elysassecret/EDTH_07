# server/ — owner: C

WebSocket bridge from sim to browser (`/shore` and `/truth`), replay, failure-injection commands.

Rule: only C edits files here. Others open an issue or ask in chat.

## mock_feed.py (until the real sim exists)

```bash
uv run python -m server.mock_feed --port 8765 --seed 1
```

A deterministic fake of the swarm that plays `scenarios/fixed.toml` on the real geometry
(`data/scene-coordinates.json`, `config/*.toml`): boat 01 low battery at 7200 s, 04's shore link
cut at 7320 s, C-07 (camera only, no AIS) seen near 7500 s, keep-in-view and the 500 m look as
decision cards, "cannot hold" at 9200 s, link back at 10 800 s. Every number in it is a mock
input, not a sim result. Snapshots validate against `contract/views.py`
(`tests/server/test_mock_feed.py`).

Messages (JSON): `scene` once on connect (segment geometry, stations), then contract snapshots at
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
| Link | `m` | link length, for the comms overlay |
| Command | `ack` (alert acknowledge) | feature 23 |
