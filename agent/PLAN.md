# Slot A, swarm brain: implementation plan

Owner: Javier (A). Implementer: Claude Sonnet, phase by phase, reviewed by Javier.
Written Fri 6 Nov 2026 from a full read of `docs/` and `contract/`, plus a scratch model of the bid rules on the real scene (section 3).

This file is the single brief for `agent/`, `contract/`, `tests/agent/`, `tests/contract/` and `config/agent.toml`. Where it differs from `docs/BUILD_PLAN.md` pseudocode, **this file wins**, and section 3 says why.

---

## 0. How to use this document (read first, Sonnet)

1. Read `CLAUDE.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`, then this file. Read `docs/BUILD_PLAN.md` only for context: its pseudocode has the bugs listed in section 3.
2. Work **one phase at a time** (section 9), in order. Each phase is one branch `a/<phase-name>` and one PR. Do not start the next phase until the current phase's done check passes.
3. Before every commit run:
   ```bash
   uv run ruff check . && uv run pytest -q tests/smoke tests/contract tests/agent
   ```
4. **Folders you may edit:** `agent/`, `contract/`, `tests/agent/`, `tests/contract/`, `config/agent.toml`. Nothing else. If something outside is needed, write it down for Javier.
5. **`contract/` freezes Fri 21:00.** After that, any change to `contract/` needs a PR approved by A, B and C. Phase 0 must therefore be complete and reviewed before 21:00.
6. **Stop and ask Javier** when you meet any item marked **DECIDE** that is still open, or when B's `world/` or C's `server/` does something this plan does not describe. Do not guess an interface with another owner.
7. Hard rules (from `CLAUDE.md`, enforced by tests):
   - `agent/` imports only `contract/` and the standard library (`numpy` is allowed but not needed). Never `world/`, `eval/`, `server/`, `ais/`.
   - No `time.time()`, no `datetime.now()`, no module `random`, no `hash()` of strings, no iteration over a `set` without `sorted()`. Time is the integer argument `t` in sim milliseconds.
   - **No module-level mutable state.** Everything lives on the `Agent` / `ShoreNode` instance. Then a reset is just constructing new objects (S1, D2).
   - Integer metres and integer milliseconds in anything that crosses the radio or is hashed. Distances with `math.isqrt`, never `math.sin/cos/atan2` (they can differ across platforms, and N2 requires Mac = Windows = Linux).
   - No invented numbers in comments, logs or UI strings. Say "cue for a look", never "suspicious" or "hostile".
   - No Claude attribution in commits or PRs.
8. **Do not write code before the hackathon officially starts** (18:00 or 19:00 Fri, see `docs/BUILD_PLAN.md`). Only event work counts; this plan is preparation, code is not.
9. Comment density: short docstrings, a one-line comment where a rule is not obvious. Match `contract/` style.

---

## 1. What A builds, and how Javier explains it in 60 seconds

**Job:** the logic that runs on every boat. Each boat sees only its own position, battery, camera detections and radio inbox. From those it decides what to do. There is no coordinator: if any boat or link fails, the others notice and redistribute the work.

**60-second script (Javier, for the jury):**
> Every task, a cable segment, a lane picket, the relay, a contact, is a record with an owner and a version number. Boats share records over a short-range radio, and when two records disagree, every boat applies the same rule, so they all end up agreeing without a leader. A boat proves it is alive with a heartbeat every 5 seconds. If it goes silent, its tasks open. Open tasks are sold in 12-second rounds on shared GPS time: each free boat bids the patrol loop it would have after adding that task, plus a battery term, and the cheapest wins. Cables come before the lane, and a contact comes before both. A boat that loses its link keeps working; when it comes back, the records merge. The operator does not steer: watching starts on its own under a standing order, and anything beyond watching waits for a person.

**Correct names** (say exactly these; a juror may check):
- Allocation: *fixed-order sequential single-item auction* (not SSI with bounds, not CBBA).
- Agreement: *per-task last-writer-wins register with a logical counter and a replica-ID tie-break* (a state-based CRDT). Not consensus.
- Liveness: *leases* (Gray and Cheriton 1989).
- Guarantee: *eventual convergence within each connected group, given delivery.* We accept duplicate patrol, never a silent gap.

---

## 2. Ground truth from the repo (numbers Sonnet must use)

| Item | Value | Source |
|---|---|---|
| Boats | 5, IDs 1–5. Shore node ID 0 | `docs/PLAN.md`, this plan |
| Roles at start | 01 `seg:G:0..2` + `seg:M:0`; 02 `seg:H:0..1`; 03 `pick:N`; 04 `pick:S`; 05 `relay` | `docs/BUILD_PLAN.md` |
| Bid order | relay 1, contact 2, cue 3, seg 4, pick 5 | `docs/BUILD_PLAN.md` |
| Speed | 2.3 m/s (sensitivity 3.0) | `config/boat.toml` |
| Endurance, reserve | 25,200 s, 1,800 s | `config/boat.toml` |
| Verify radius, keep-in-view, stand-off, floor | 500 m, 2,000 m, 1,852 m, 500 m | `config/boat.toml` |
| Detection radius (scripted dusk contact) | 2,000 m, applied by `world/` | `config/boat.toml` |
| Radio | boat 8 km, shore 14 km, delay 0.25–1 s, loss 5 %, max 4 hops | `config/radio.toml` |
| SENTINEL drift radius, return safety | 300 m, ×1.2 | `config/energy.toml` |
| Timing constants | `contract/constants.py` (HEARTBEAT 5 s, PEER_STALE 20 s, LEASE 60 s, SLOT 12 s, DEPUTY_GRACE 10 s, REBALANCE 300 s, SHORE_SILENCE 30 s, CONTACT_STALE 60 s, SHADOW_CAP 1,800 s, CUE_TTL 180 s, CYCLE_MAX 6 h) | repo |
| Scene | `data/scene-coordinates.json`; projection equirectangular about 55.40 N 11.00 E, kx = 63,212 m/deg lon, ky = 111,190 m/deg lat | scene file |
| Stations (lat, lon) | Korsør shore 55.3316, 11.1303; relay 55.405, 10.975; pick N 55.4578, 10.9081; pick S 55.3543, 11.0135 | `config/scene.toml` |
| Event tape | 7,200 battery_low boat 1; 7,320 link_off 4–shore; 7,320 contact C-07 starts (no AIS, 0.4 kn, dusk); 9,200 C-07 departs at 6 kn, course 255; 10,800 link_on 4–shore; 14,000 evaluate | `scenarios/fixed.toml` |
| Run | 14,400 s, tick 1 s, seeds 1–5 | `config/run.toml` |

Expected story (from `docs/BUILD_PLAN.md`, adjusted by section 3): 01 leaves at 7,200 and releases its cable tasks; **04** wins them and releases `pick:S`; 04's shore link is cut; 02 detects C-07; **03** (still a free picket) wins the contact, releases `pick:N`, holds at stand-off; 02 resumes when 03 has it in view; operator approves "close to 500 m"; at 9,200 C-07 outruns the boat, "cannot hold"; 03 returns to `pick:N`; `pick:S` stays visibly open; 04's link returns and records merge without churn.

---

## 3. Findings: what is wrong in the BUILD_PLAN pseudocode, with evidence

The scratch model is `geo_check.py` in Claude's session scratchpad (not project code). It projects the scene, clips the three scenario cables to the box, splits them into ≤5 km segments, and replays the bid rules by hand with straight-line transits, no radio, no land. Its numbers are **[Scratch model]**: good enough to find design bugs, not results to quote. B's `world/routes.py` is the source of truth for geometry.

Scratch geometry: H 2 × 4,735 m, G 3 × ~3,410 m, M 1 × 3,183 m, total 22.9 km (docs say 23.5 km; the difference is clipping detail). Initial cycles with cheapest insertion: **01 = 10,969 s, 02 = 8,466 s** (01's equals brute-force optimum).

### F1. `merge` is not commutative when keys tie (bug in `contract/tasks.py`)
`key = (ver, state, -bid, owner)` ignores `deputy`. Two records equal on the key but with different deputies give `merge(a, b) = a` and `merge(b, a) = b`. Hypothesis (D5) will find this in seconds.
**Fix:** the key must cover every field: `(r.state == VETOED, r.ver, r.state, -r.bid, r.owner, r.deputy)`. Then `merge` is `max` under a total order: commutative, associative, idempotent.

### F2. A Stop can be silently undone
Stop is `Rec(contact, ver+1, VETOED, …)`. If boats reach `ver+2` before the Stop arrives (a re-claim on a slow link), the claim wins and the operator's Stop is lost.
**Fix:** the first key element `state == VETOED` makes a Stop absorbing: once a contact is stopped it stays stopped on every boat. Only contacts are ever vetoed.

### F3. The pure-minimax bid strips both lane pickets and leaves no free boat for the contact
Auction after 01 leaves (bidders 02, 03 at pick N, 04 at pick S), cost in seconds:

| Bid rule | G:0 | G:1 | G:2 | M:0 | End state |
|---|---|---|---|---|---|
| `cycle_after` only (BUILD_PLAN) | 04 (tie with 03, won on ID) | 03 | 03 | 04 | **both pickets gone**; 03 drives ~13 km south; no free boat for the contact |
| + travel time to the task ("reach") | 04 | 04 | 03 (8,781 vs 8,952) | 04 | both pickets gone again |
| + reach + **role penalty 12,000 s** when a picket would leave its picket | 04 | 04 | 04 | 04 | 04 cycle 10,969 s (same as 01 had); **03 keeps `pick:N`**, free for the contact |

Minimax balances load even when one boat can already meet the 12,000 s revisit target; it pulls a second picket off the lane for nothing and then the contact has no eligible boat (all remaining boats own cables, the relay is excluded). The story in `docs/BUILD_PLAN.md` silently assumed the third row.
**Fix:** `bid = cycle_after + reach + battery_term + role_penalty`, where `role_penalty = role_penalty_s` (config, default 12,000 s) is added when (a) a picket bids on a cable segment, or (b) a cable sweeper bids on a contact. One knob, explainable as "cables before lane, and we only pull a boat off its role when no cheaper option exists".

### F4. With a 60 s lease, boat 04 loses its sector while it is alive
After 04 takes 01's tour, it spends about **3,780 s of every 10,969 s loop more than 8 km from the relay**, the longest stretch about **3,440 s**, around `seg:M:0` (M:0 near end 8.5 km, far end 11.0 km from the relay). Its shore link is cut 7,320–10,800, and 02, 03 are 12+ km north. So 04 is silent to everyone for most of an hour. With a 60 s lease the majority (02, 03, 05) declares its four segments expired and re-auctions them, pulling 03 or 02 far south; when 04 reappears its lower versions lose and it drops everything. That is version churn in the middle of the demo window (the technical notes flagged "version churn at range edge" as a real risk; this is the concrete case).
**Fix:** two leases. `LEASE` (60 s) for `relay` and `contact`, where seconds matter. `seg_lease_s` (config, default **3,600 s**) for `seg` and `pick`, which have hours of slack against a 12,000 s target. A boat that runs out of battery releases its tasks explicitly (instant), so the long lease only delays the silent-death case (`boat_off`). Console text for C: "USV 04 silent 23 min · sector kept until 60 min". D runs 600 / 1,800 / 3,600 s as sensitivity.
Upgrade path (P2, not now): extend a silent boat's lease only while its dead-reckoned position along its announced tour is beyond nominal radio range of the listener's group.

### F5. Rebalance must never treat a picket or the relay as "idle"
Pickets and the relay have no tour, so `cycle = 0`. The pseudocode's `lo = min(available_peers, key=cycle)` would hand cable segments to pickets with no failure at all, changing behaviour before the first event (that also breaks F2 "ages at T−1 byte-identical across modes").
**Fix:** "available peer" = live, in PATROL, holding no `pick`, `relay` or `contact`. Pre-event check on the scene: 01/02 cycle ratio is 1.30 > 1.25, so the trigger fires, but the second guard refuses: 02's cycle after taking any one of 01's segments would be 18,132–21,154 s, above 01's current 10,969 s [Scratch model]. **No pre-event release.** Keep a test for exactly this.

### F6. Winning the relay or a contact must release cable and picket tasks
The pseudocode only releases `pick` on a `seg` win. A boat that wins `relay` keeps its segments it can no longer sweep, and a contact watcher keeps `pick:N` so nobody sees it open. The brief says "the others close the gap it leaves behind", which only happens if the tasks are released.
**Fix:** on winning `relay`: release every `seg` and `pick` held. On winning a `contact`: release every `seg` and `pick` held. On winning a `seg`: release `pick`.

### F7. Smaller correctness points
- A broadcast does not loop back: **store your own bid** in `bids[e][task]` when you send it, or a lone bidder never wins.
- Slot actions must trigger on **crossing a slot boundary** (`t // SLOT != self.last_slot`), not `t % SLOT == 0`; the world might change its tick.
- Every `sorted(...)` needs a total key: tasks by `(BID_ORDER[kind], task_id)`, bids by `(cost, -boat)`.
- Leases use the heartbeat's `t_created` (shared sim clock), never receive time, so a forwarded heartbeat still counts and a delayed one does not extend a lease.
- Stagger periodic sends by boat ID (`(t + me * 1_000) // HEARTBEAT`) so five heartbeats do not all land in the same tick.
- Contact "free" rule: the docs say "not the last cable owner", which is ambiguous. Use **"not the last sweeper"**: I own a `seg` and no other live boat owns any `seg`. Taking one sweeper off a single cable is fine, because its segments are released and re-auctioned (F6).

### F8. Who forwards radio messages is undecided (DECIDE with B before 21:00)
`docs/PLAN.md` gives B "peer hops, store-and-forward, dedupe by msg_id" (step 19), while the agent pseudocode calls `forward(new)`. If both forward, traffic doubles and hop counts lie; if neither does, the relay boat does nothing.
**Recommendation:** `world/radio.py` (B) is the physical layer only: one broadcast reaches every node in range, with delay, loss and link-off. **Forwarding, dedupe, hop limit, expiry and retry live in `agent/net.py` (A)**, because on a real boat the boat computer routes, not the radio, and it keeps any global routing table out of the sim (no hidden coordinator). B's step 19 shrinks by about 2 h; A's grows by about 2 h. Fallback if B disagrees: B forwards, and `agent/net.py` keeps only encode/decode, dedupe and expiry.

---

## 4. The pasted swarm paradigms: what we take, what we reject

The paste proposes multi-agent RL, virtual structure plus artificial potential fields (APF), consensus formation control, and a leader-follower + APF hybrid. Its references were not verified here and are not needed.

| Idea | Verdict | Why |
|---|---|---|
| MARL (thrust/steering from trained policies) | **Reject** | Solves motion control; our boats are kinematic points in a 2D sim, so there is no thrust to learn. No training time, not explainable in 60 s, breaks determinism tests D1–D3. |
| Consensus formation (graph Laplacian) | **Reject** | Our boats are 6–20 km apart doing different jobs; there is no formation. The plan already says "not consensus", and our CRDT merge already gives agreement on *who does what*. |
| Leader-follower | **Reject** | A leader is a single point of failure, and losing a boat is the event we demo. "No coordinator" is a core claim. |
| APF for collision avoidance | **Reject for now** | Our boats are kilometres apart; collision is not modelled. Say so openly ("collision avoidance stays in the autopilot"). |
| **Layered control with an independent safety layer** | **Take** | This maps exactly onto the operator policy's automatic-safety tier. `agent/safety.py` is a last pass over every action that no mission logic can override: return on reserve, the 500 m stand-off floor, no closing inside 1,852 m without approval, no station in the lane band. |

One honest sentence for the deck: "Formation control and learned controllers solve keeping boats together; our problem is deciding which boat does which job when boats and links fail, so we use an auction and a mergeable task table."

---

## 5. Phase 0 interfaces: `contract/` (finish and review before Fri 21:00)

Everything here is shared with B (world) and C (server, web). Keep it small and boring.

### 5.1 `contract/constants.py` (edit)
Keep all existing constants. Add:
```python
SHORE = 0                  # node ID of the shore station; boats are 1..5
RETRY = 5_000              # resend period for VETO and CMD until ACK or expiry
MAX_HOPS = 4
REBROADCAST = 30_000       # each node re-advertises its whole task table
CONTACT_DWELL = 180_000    # slow, no-AIS track observed this long becomes a contact task
EXPIRY = {"HB": 12_000, "BID": 12_000, "REC": 60_000, "OBS": 60_000,
          "CONTACT": 60_000, "VETO": 30_000, "CMD": 30_000, "ACK": 30_000}
```
Tunable values (`seg_lease_s`, `role_penalty_s`, `rebalance_ratio`, `policy`, loiter speed) go in `config/agent.toml`, not here, so D can run sensitivity without touching the frozen contract.

### 5.2 `contract/tasks.py` (edit)
```python
BID_ORDER = {"relay": 1, "contact": 2, "cue": 3, "seg": 4, "pick": 5}

def kind(task: str) -> str:            # "seg:G:0" -> "seg", "relay" -> "relay"
def key(r: Rec) -> tuple:              # (r.state == VETOED, r.ver, r.state, -r.bid, r.owner, r.deputy)
def merge(a: Rec, b: Rec) -> Rec:      # a if key(a) >= key(b) else b  (assert a.task == b.task)
def to_wire(r: Rec) -> list:           # [task, ver, state, bid, owner, deputy]
def from_wire(x: list) -> Rec
```
`tests/smoke/test_smoke.py::test_merge_is_deterministic` must still pass (it does with the new key).

### 5.3 `contract/messages.py` (edit)
Add `"CMD"` to `KINDS`. Envelope and codec:
```python
@dataclass(frozen=True, slots=True)
class Msg:
    id: str        # f"{src}:{seq}", seq counts up per node from 1; deterministic
    src: int       # 0 = shore
    tc: int        # t_created, sim ms; forwarding never changes it
    te: int        # t_expire = tc + EXPIRY[kind]
    kind: str
    hops: int      # 0 when sent by src
    p: dict        # payload, JSON-safe ints, strs, bools, lists only

def encode(m: Msg) -> bytes:   # json.dumps(..., sort_keys=True, separators=(",", ":")).encode()
def decode(b: bytes) -> Msg
```
Payloads (document them in the module docstring):

| Kind | From | Payload |
|---|---|---|
| HB | boat | `x, y` (int m), `mode`, `batt` (permille), `cyc` (cycle ms, 0 if none), `tour` (task IDs in visit order), `roles` (task IDs held), optional `head` (reserved for C's evidence chain: `[seq, hash]`) |
| HB | shore | `{}` (its arrival is the shore-age signal) |
| BID | boat | `task, e, cost, boat` (e = slot number, cost in ms) |
| REC | any | `recs`: list of wire records (1 for a change, the whole table on re-advertise) |
| OBS | boat | `track, x, y, sog` (mm/s), `cog` (deg), `ais`, `to` (t observed), `by`, `dist` (m from observer) |
| CONTACT | boat | `id` (contact task ID), `first` (t first seen), `flags` {`dwell, name, anchor, cannot_hold, capped`}, `course` |
| VETO | shore | `rec`: the wire record with state VETOED |
| CMD | shore | `task` (e.g. `contact:C-07`), `dec` (`close`), `ans` (`approve` or `decline`) |
| ACK | boat | `of` (msg id acknowledged) |

### 5.4 `contract/geo.py` (new)
One projection for A, B and C: `LAT0, LON0, KX, KY`, `to_xy(lat, lon) -> (int, int)` (metres, x east, y north), `to_lonlat(x, y) -> (lon, lat)` (floats for the map only), `dist(a, b) -> int` with `math.isqrt`.

### 5.5 `contract/mission.py` (new): the A ↔ B interface
```python
@dataclass(frozen=True, slots=True)
class TaskSpec:
    id: str                              # "seg:H:0", "pick:N", "relay"
    pts: tuple[tuple[int, int], ...]     # seg: polyline (>= 2 pts); pick, relay: one point

@dataclass(frozen=True, slots=True)
class Mission:
    boats: tuple[int, ...]               # (1, 2, 3, 4, 5)
    tasks: tuple[TaskSpec, ...]          # fixed order
    initial: tuple[tuple[str, int], ...] # (task_id, owner) at t = 0
    shore: tuple[int, int]
    lane: tuple[tuple[int, int], ...]    # measured centreline
    lane_half_m: int                     # band half-width for the keep-out

@dataclass(frozen=True, slots=True)
class Params:                            # built from config/*.toml by load_params(); agent never reads files
    speed_mm_s: int; endurance_ms: int; reserve_ms: int
    r_verify_m: int; keep_in_view_m: int; standoff_m: int; standoff_floor_m: int
    sentinel_radius_m: int; return_safety_permille: int
    seg_lease_ms: int; role_penalty_ms: int; rebalance_ratio_permille: int
    loiter_sog_mm_s: int; policy: str; repair_off_after_ms: int

@dataclass(frozen=True, slots=True)
class Own:                               # own sensors, from world each tick
    x: int; y: int                       # GNSS, metres
    batt: int                            # permille of full charge
    cur_x: int = 0; cur_y: int = 0       # measured current, mm/s (feature 15; 0 until B ships it)

@dataclass(frozen=True, slots=True)
class Detection:                         # camera, only what world says this boat can see
    track: str                           # sim track ID, e.g. "C-07" (stands in for correlation; disclose)
    x: int; y: int; sog: int; cog: int; ais: bool

@dataclass(frozen=True, slots=True)
class Action:
    mode: str                            # PATROL, SENTINEL, SHADOWING, RETURNING, UNAVAILABLE
    target: tuple[int, int] | None       # None = motors off, drift
    speed_mm_s: int

def load_params(root: str = ".") -> Params   # tomllib over config/boat.toml, energy.toml, agent.toml, run.toml
```
B builds `Mission` in `world/routes.py` from the scene (B owns geometry and segmenting). The agent receives it at construction.

### 5.6 `contract/views.py` (edit, with C at 20:30)
Pydantic v2 models for the snapshot and commands, plus `contract/export.py` so `uv run python -m contract.export` writes `contract/schema.json` (C generates TypeScript from it). Start from the docstring already in `views.py`; add `lon, lat` beside `x, y` on boats and contacts (MapLibre needs them). Fields A needs C to accept: boat `mode`, `link` (`direct` | `peer` | `none`), `last_heard`, `tour`, `roles`; contact `watcher`, `flags`, `first_seen`, `last_seen`, `seen_by`; decision `id, task, dec, state` (`pending`, `approved`, `declined`, `delivered`, `expired`). Bump `SCHEMA_VERSION` to 1 at freeze.

### 5.7 Open decisions for Javier to settle at the 19:15 contract session

| # | Decide with | Question | Recommendation |
|---|---|---|---|
| D-1 | B | Who forwards (F8) | Agent forwards; world is physical layer only |
| D-2 | B | Who decides "return home" | Agent decides from `Own.batt` and `Own.cur_*`; world only drains battery and applies the `battery_low` event |
| D-3 | B | Detections carry the sim track ID | Yes; disclose "correlation is assumed" |
| D-4 | B | Units and frame | int metres in `contract/geo.py` frame; int ms; battery permille |
| D-5 | B | Who builds `Mission` | B in `world/routes.py` |
| D-6 | B, D | World calling convention | Each tick: world steps boats in ID order, then the shore node; each gets the bytes delivered this tick; each returned byte string is broadcast once from that node at `t` |
| D-7 | C | Shore protocol code | A ships `agent/shore.py` (`ShoreNode`); C's server wraps it, so C never re-implements encoding, dedupe or retries |
| D-8 | D | Baseline switch | One key, `policy` in `config/agent.toml`: `elysa`, `off`, `static` (section 7.11) |
| D-9 | A, B, C | F1, F2 contract fixes, CMD kind, reserved HB `head` | Accept before freeze |

---

## 6. Agent architecture

```text
agent/
  net.py      envelope, msg ids, dedupe, expiry, flooding with hop limit, retry until ACK
  table.py    task records, merge, per-boat heartbeats, two leases, is_open, max_ver
  tour.py     integer geometry, tour (legs + directions), cycle length, cheapest insertion, follower
  auction.py  slots, bids, cost, eligibility, close round, claims and releases, rebalance
  contact.py  tracks, dwell, contact task, scout hold, watcher, stand-off ring, approvals, stop, cannot hold
  safety.py   last pass over the action: reserve, stand-off floor, approval gate, lane keep-out
  core.py     Agent: owns all state, runs step() in a fixed order
  shore.py    ShoreNode: shore heartbeat, picture of delivered data, commands with retry
  deputy.py   P1, relay and contact only
```

### 6.1 Public API
```python
class Agent:
    def __init__(self, me: int, mission: Mission, params: Params): ...
    def step(self, t: int, own: Own, seen: tuple[Detection, ...],
             inbox: list[bytes]) -> tuple[Action, list[bytes]]: ...
    def view(self) -> dict: ...   # JSON-safe, deterministic order; for /truth, state hash, tests

class ShoreNode:
    def __init__(self, mission: Mission, params: Params): ...
    def step(self, t: int, inbox: list[bytes]) -> list[bytes]: ...
    def command(self, t: int, cmd: dict) -> None: ...   # {"cmd": "stop"|"approve"|"decline"|"confirm", "id": ...}
    def picture(self, t: int) -> dict: ...               # only what the shore has received
```
At construction every agent builds the same initial table from `mission.initial`: `Rec(task, 1, CLAIMED, 0, owner, 0)` for each pair. Its own tour is built by cheapest insertion of its initial `seg` tasks in task-ID order. No messages are needed to start.

### 6.2 Order inside `Agent.step(t, …)` (fixed; determinism depends on it)
1. **Inbox:** for each raw message in arrival order: decode; drop if seen or expired; queue for forwarding if `hops < MAX_HOPS`; dispatch by kind.
2. **Own sensors:** store position and battery; turn detections into own OBS and update dwell.
3. **Return rule** (7.6). If it fires: mode RETURNING, release every task held, clear tour. Sticky until at shore, then UNAVAILABLE.
4. **Slot boundary:** close round `e - 1`, then send at most one bid for slot `e` (7.4). Skipped by policy where section 7.11 says so.
5. **Rebalance boundary** (7.7), staggered by boat ID.
6. **Deputy check** (P1, 7.10).
7. **Periodic sends:** HB every 5 s, whole-table REC every 30 s, OBS for tracks in view every 5 s, CONTACT on flag change. All staggered by `me * 1_000`.
8. **Behaviour:** choose target and mode from the current role (6.3).
9. **Safety filter** (7.9).
10. Return `(action, outbox)`; outbox = new messages + forwarded ones, in that order.

### 6.3 Roles and modes (derived each tick, in priority order)
| Condition | Mode | Target |
|---|---|---|
| Returning | RETURNING | shore, cruise speed |
| At shore after returning | UNAVAILABLE | none |
| Own a contact task (watcher) | SHADOWING | stand-off ring point (7.8) |
| Holding a contact as scout | SHADOWING | ring point, until relieved |
| Own `relay` or a `pick` | SENTINEL | station: drive back when > 300 m away, stop when < 100 m (hysteresis), otherwise drift |
| Own `seg` tasks | PATROL | next waypoint of the tour follower |
| Nothing | SENTINEL | hold current position |

ECO and DORMANT exist in `contract/constants.py` but are not built this weekend (features 29+).

---

## 7. Algorithms

### 7.1 Network layer (`net.py`)
- `send(t, kind, payload) -> bytes`: `id = f"{me}:{seq}"`, `tc = t`, `te = t + EXPIRY[kind]`, `hops = 0`. Remember the id as seen.
- `receive(t, raw) -> Msg | None`: decode; return None if `id` already seen or `t > te`. Remember `id` with its `te`; prune ids whose `te < t` once per second (iterate the dict in insertion order, no sets).
- `forward(m) -> bytes | None`: same message with `hops + 1` if `m.hops < MAX_HOPS`, else None. Never change `tc`, `te` or an observation time. Forward every kind, including BID (bids must cross hops inside one slot).
- Retry: VETO and CMD from the shore are resent every `RETRY` until an ACK with `of = id` arrives or `te` passes. A resend reuses the same `id`, so boats that already have it drop it and boats that missed it accept it.

### 7.2 Task table (`table.py`)
State: `recs: dict[str, Rec]`, `last_hb: dict[int, int]` (max HB `tc` per boat).
```python
def lease_ms(task): return LEASE if kind(task) in ("relay", "contact") else params.seg_lease_ms
def lease_ok(b, task, t): return b == me or t <= last_hb.get(b, -inf) + lease_ms(task)
def is_open(task, t):
    r = recs[task]
    if r.state == RELEASED: return True
    if r.state == VETOED or lease_ok(r.owner, task, t): return False
    if r.deputy and t < last_hb.get(r.owner, 0) + lease_ms(task) + DEPUTY_GRACE: return False
    return True
def apply(r) -> bool:          # True if the table changed
    cur = recs.get(r.task); new = r if cur is None else merge(cur, r)
    if new == cur: return False
    recs[r.task] = new         # caller forwards, and drops the task from its tour if it lost ownership
    return True
def max_ver(task): return recs[task].ver if task in recs else 0
```
Unknown task IDs (a new contact) are inserted on first sight. `last_hb` for boats that have never been heard: treat as 0, so their initial tasks expire after their lease if they never speak.

### 7.3 Tours (`tour.py`)
- Distances: `isqrt(dx*dx + dy*dy)` on ints. Segment length = sum over its polyline.
- A tour is a list of legs `(task_id, reversed)`. Leg start and end are the polyline ends in that direction.
- `cycle_m(legs)` = for each leg: its length + straight transit from its end to the next leg's start, wrapping around. One segment alone gives 2 × length (back and forth).
- `insert(legs, task) -> legs`: try every position `0..n` and both directions; pick the smallest cycle; ties: lowest position, then forward. `cycle_after(task) = cycle_m(insert(legs, task)) * 1_000_000 // speed_mm_s` (metres to ms: m × 1000 mm × 1000 ms / (mm/s)).
- `remove(legs, task)` keeps the order of the rest. The follower keeps pointing at the same next waypoint where possible.
- `reach_ms(pos, task)`: to the nearest end of a `seg`, to the point of `pick` / `relay`, to the ring point of a contact; `dist_m * 1_000_000 // speed_mm_s`.
- Follower: waypoints are the leg's polyline points in order, then the next leg's start. Advance when within 10 m (the world moves ≤ 2.3 m per tick).
- Expected on the real scene (scratch): 01 cycle 10,969 s, 02 cycle 8,466 s. Put a test with B's real `Mission` once it exists; until then use the segment ends listed in section 8.

### 7.4 Auction (`auction.py`)
```python
def on_slot(t):                              # when t // SLOT changes
    e = t // SLOT
    close_round(e - 1, t)
    if policy_blocks_bidding(t): return
    for task in sorted(table.recs, key=lambda k: (BID_ORDER[kind(k)], k)):
        if table.is_open(task, t) and can_bid(task, t):
            c = bid_cost(task, t)
            bids.setdefault(e, {}).setdefault(task, []).append((c, me))   # F7: keep your own bid
            send("BID", {"task": task, "e": e, "cost": c, "boat": me})
            break                            # one bid per slot

def close_round(e, t):
    for task, bs in sorted(bids.pop(e, {}).items()):
        if not table.is_open(task, t): continue          # a live claim arrived: cancel (P3)
        bs = sorted(bs, key=lambda b: (b[0], -b[1]))
        if bs[0][1] != me: continue
        dep = bs[1][1] if len(bs) > 1 and kind(task) in ("relay", "contact") else 0
        claim(task, bs[0][0], dep, t)

def claim(task, cost, dep, t):
    publish(Rec(task, table.max_ver(task) + 1, CLAIMED, cost, me, dep))
    k = kind(task)
    if k == "seg": insert into tour; release my pick (if any)
    if k in ("relay", "contact"): release every seg and pick I hold; clear tour       # F6
    if k == "pick": hold station

def release(task, t):
    publish(Rec(task, table.max_ver(task) + 1, RELEASED, 0, me, 0)); drop from tour
```
Received bids are stored under their `e`; drop bids for `e` older than the current round. When `apply()` shows I lost a task I had claimed, remove it from my tour (losers drop at once, never outbid a live claim).

**Cost (ms):**
```python
batt_term = 1_800_000 * (1000 - own.batt) // 1000
seg:      cycle_after(task) + reach_ms(task) + batt_term + (role_penalty_ms if I hold a pick else 0)
pick:     reach_ms(task) + batt_term
relay:    reach_ms(task) + batt_term
contact:  reach_ms(ring point) + batt_term + (role_penalty_ms if I hold any seg else 0)
cue:      reach_ms(cue point) + batt_term          # only if B ships cues (P1)
```

**Eligibility `can_bid(task, t)`:**
- Never while RETURNING or UNAVAILABLE.
- `seg`: not SHADOWING, not holding `relay`; if the record is an expired claim (state CLAIMED), require a live majority: `1 + live_peers(t) >= n_active(t) // 2 + 1`; `cycle_after <= CYCLE_MAX`; `energy_ok`.
- `pick`: PATROL or SENTINEL, holds no `seg`, `pick`, `relay` or contact.
- `relay`: `shore_age(t) > SHORE_SILENCE` and `energy_ok`.
- `contact`: not holding `relay`; not the last sweeper (F7); contact not VETOED, not `cannot_hold`, not `capped`; last observed contact speed `<= speed_mm_s`; `energy_ok`.
- `live_peers(t)`: boats other than me with `last_hb` within `PEER_STALE`. `n_active(t)`: me plus boats heard within 600 s whose last HB mode is not RETURNING or UNAVAILABLE.
- `energy_ok(task)`: `remaining_ms - reserve_ms >= return_safety_permille * (reach_ms + one pass of the task + return_ms from the task's far end) // 1000`.

### 7.5 Relay and shore age
- The shore node sends an HB every 5 s. Flooding carries it up to 4 hops with its original `tc`. `shore_age(t) = t - max tc of any shore HB received` (or `t` if never). No separate gossip needed.
- P7 falls out: any boat in a group with a shore path hears shore HBs, so it never bids on `relay`.
- When `05` dies, `relay` opens after 60 s. Only boats cut from shore bid; the north picket (7.2 km from the relay station, 19.9 km from Korsør) is the likely winner. It releases `pick:N` (F6) and moves to the station. If nobody is cut off, `relay` stays open and the console shows it; that is S6.

### 7.6 Return rule (feature 6 and 15)
```python
remaining_ms = own.batt * endurance_ms // 1000            # at cruise; conservative while drifting
ground = speed_mm_s + current component toward shore      # integer dot product / |u|
ground = max(ground, speed_mm_s // 4)
return_ms = dist(pos, shore) * 1_000_000 // ground        # m and mm/s -> ms (10 km at 2.3 m/s = 4,347,826)
fire when remaining_ms <= return_safety_permille * (return_ms + reserve_ms) // 1000
```
On firing: release every task explicitly (others re-auction at the next slot, which is why the story shows 7,212–7,260), mode RETURNING, HB says so (peers drop it from `n_active`).

### 7.7 Rebalance (fix for idle boats, F5)
Every `REBALANCE`, at `t // REBALANCE` boundaries offset by `me * 60_000`:
- `available` = live peers in PATROL that hold no `pick`, `relay` or contact.
- `lo` = the one with the smallest HB `cyc` (ties: lowest ID).
- If `my_cycle * 1000 > rebalance_ratio_permille * lo.cyc` (config 1.25 becomes 1250), `len(tour) >= 2`, and no open task I could bid on: pick the segment whose removal lowers my cycle most (ties: task ID). Recompute `lo`'s cycle with that segment inserted, from `lo`'s HB tour and the mission geometry. Release it only if that is below my current cycle. At most one release per period.
- Research warns rebalance raised worst age in one scratch run; keep `rebalance_ratio` in config so D can measure it, and do not remove the idle-boat fix.

### 7.8 Contact (`contact.py`)
**Tracks.** `tracks[track]` keeps the observation with the largest `to` (ties: lowest `by`). `first_seen[track]` keeps the smallest `to`. Both are merges, so every boat converges.
**Dwell.** A track is a candidate when `ais` is false, `sog <= loiter_sog_mm_s` (config, default 515 mm/s ≈ 1 kn) and it lies within 1,000 m of any cable polyline in the mission. When a boat sees a candidate and `t - first_seen >= CONTACT_DWELL`, it publishes `Rec("contact:" + track, 1, RELEASED, 0, 0, 0)` and a CONTACT message with `dwell` set. Two boats doing this at once publish identical records; merge makes it harmless.
**Scout hold.** A boat that sees a candidate holds it (SHADOWING, ring point) until one of: the contact's owner reports it in view (`OBS.by == owner` and `dist <= keep_in_view_m`), the contact is VETOED, `cannot_hold`, `capped` or stale. It keeps its segments while holding; it simply pauses.
**Watcher.** The auction winner (7.4). Target = ring point: `c + (b - c) * R // |b - c|` with integer maths, `R = (standoff_m + keep_in_view_m) // 2` (1,926 m; inside the 2,000 m detection range, outside the 1,852 m stand-off ring). Recompute every tick from the latest track position. Starts at once: this is the "delegated under standing order" tier.
**Close (held for approval).** On a CMD `{dec: "close", ans: "approve"}` for a contact it owns, the watcher sets `R = standoff_floor_m` (500 m). When within `r_verify_m`, set flags `name` and `anchor` (meaning "a look within 500 m happened"; the sim draws nothing), then go back to the normal `R`. Decline or no answer: stay on the ring. ACK every CMD.
**Stop.** A VETO record makes the contact VETOED forever (F2). Watcher and scout release their hold and resume.
**Cannot hold.** If the watcher observes `sog > speed_mm_s`, set `cannot_hold`, record `course`, release the contact. Nobody is eligible afterwards. The CONTACT message is the queued report.
**Stale.** No observation for `CONTACT_STALE`: the watcher releases. **Cap.** Watching longer than `SHADOW_CAP` since the claim: set `capped`, release. Offline: nothing special; held actions simply never get approved.
**Report wording** (for C): "Keeping in view. Standing Order 2", "Cannot hold; report queued; last course 255". Never "hostile", "suspicious" or "shadowing a threat".

### 7.9 Safety filter (`safety.py`)
Applied last, cannot be overridden:
1. RETURNING wins over everything.
2. Never target a point within `standoff_floor_m` of any known contact.
3. Never target a point within `standoff_m` of a contact unless a close approval for that contact is active.
4. Never hold a station inside the lane band (`lane_half_m` of the centreline). Crossing the lane while sweeping is allowed; dwelling is not (R2). If a station is in the band, that is a mission error: raise at construction.

### 7.10 Deputy (P1, `deputy.py`; first thing to cut)
For `relay` and `contact` only. The winner names the second-lowest bidder as `deputy` (already in `close_round`). Each tick, if I am the deputy of a CLAIMED record whose owner's lease has expired: claim it at `ver + 1` with no auction if `can_bid`, otherwise publish RELEASED (decline). Report the measured gap against a re-auction (expect a saving of one or two slots on a healthy link).

### 7.11 Baseline policies (`policy` in `config/agent.toml`, the one key that differs between modes, F4 fairness)
| Policy | Before `repair_off_after_ms` | After it |
|---|---|---|
| `elysa` | Full behaviour | Full behaviour |
| `off` | Identical to `elysa` (F2 needs byte-identical ages at T−1) | No BID, no rebalance, no deputy takeover. Released tasks stay open. Return rule, contact detection, scout hold and OBS still run |
| `static` | Every boat holds a fixed station: pickets and relay at theirs; 01 and 02 at the midpoint of the first segment of their initial tour. No auction ever | Same |

`repair_off_after_ms` comes from the scenario's first failure event (7,200,000), identical across modes; confirm with D (D-8).

---

## 8. Test harness and tests

### 8.1 `tests/agent/harness.py`: a tiny fake world (test-only)
A needs to test the protocol before B's world exists, and without importing it.
- Nodes: five `Agent`s and one `ShoreNode`. Positions as ints; each tick move each boat toward its `Action.target` by at most `speed_mm_s / 1000` m (SENTINEL with no target: stay).
- Radio: a broadcast from node `a` at tick `t` is delivered at `t + delay` to every node within range (boat 8,000 m, shore 14,000 m), unless the directed link is switched off. Delay fixed at 1,000 ms by default. Optional loss from a `random.Random(seed)` instance (never the module-level random).
- Controls: `kill(b)`, `link(a, b, on)`, `set_batt(b, permille)`, `add_track(id, x, y, sog, cog, ais)`, `move_track(...)`. Detections: tracks within 2,000 m.
- Two missions: a small synthetic one (fast unit tests) and a scene-like one using these scratch segment ends (metres, contract frame), replaced by B's `Mission` once `world/routes.py` exists:
  ```text
  seg:H:0 (-8682, 5417) -> (-3947, 7029)    seg:H:1 (-3947, 7029) -> (788, 8641)
  seg:G:0 (-5709,-5687) -> (-2381,-5197)    seg:G:1 (-2381,-5197) -> (1039,-5087)
  seg:G:2 (1039,-5087)  -> (4439,-4976)     seg:M:0 (-2278,-7893) -> (-4544,-10025)
  shore (8237,-7605)  relay (-1580, 556)  pick:N (-5809, 6427)  pick:S (853,-5081)  C-07 (-8180, 5615)
  ```

### 8.2 Test list
| ID | File | Test | Phase |
|---|---|---|---|
| D5 | `tests/contract/test_merge.py` | Hypothesis over random `Rec`s with the same task: commutative, associative, idempotent; folding any permutation gives one result; VETOED beats any version | 0 |
| C1 | `tests/contract/test_messages.py` | encode/decode round trip; encoding is byte-stable (sorted keys) | 0 |
| N1–N4 | `tests/agent/test_net.py` | dedupe; expired dropped; hop limit 4; forwarding keeps `tc` | 1 |
| T1–T3 | `tests/agent/test_table.py` | relay lease 60 s vs seg lease; `is_open` with deputy grace; heartbeat via forward still renews | 1 |
| G1 | `tests/agent/test_tour.py` | cheapest insertion deterministic; single segment cycle = 2 × length; on the scene-like mission, 01 ≈ 10,969 s and 02 ≈ 8,466 s (±2 %) | 2 |
| P1 | `tests/agent/test_protocol.py` | Lost bid: cheaper boat wins after merge | 2 |
| P2 | same | Winner killed mid-round: task re-auctioned next slot | 2 |
| P3 | same | Heartbeat arrives mid-round: round cancelled, no takeover | 2 |
| P6 | same | Claim beats release at equal version | 2 |
| P0 | same | Kill any one boat (try every ID): all its tasks owned again within lease + 3 slots | 2 |
| P4 | same | Isolated boat claims nothing expired; only the majority side claims | 3 |
| P5 | same | Rejoin: no boat idle after two rebalance periods | 3 |
| P9 | same | **New (F4):** a boat out of range for less than `seg_lease` keeps its segments; no version change on rejoin | 3 |
| R0 | same | **New (F5):** scene-like mission, no events: no task changes owner in 7,200 s | 3 |
| P7 | same | Group with a shore path elects no relay | 4 |
| S6 | same | Relay killed: a cut-off boat takes it, or `relay` stays open and visible | 4 |
| P8 | same | Deputy takes relay with radio silent, or declines | 6 |
| ST | `tests/agent/test_story.py` | The fixed scenario on the scene-like mission (section 2 expected story), asserting: by 7,300 s 04 owns all of `seg:G:*`, `seg:M:0`; `pick:S` open; 03 still holds `pick:N`; 03 wins the contact; 02 resumes its tour after 03 reports in view; at 9,200 + a few seconds `cannot_hold`; by 9,800 s 03 holds `pick:N` again; no `seg` changes owner between 7,320 and 10,800 | 5 |
| S3 | same | Watching starts with no operator input; Stop ends it; an expired Stop changes nothing; close approval moves the watcher to 500 m and back | 5 |
| DT | `tests/agent/test_determinism.py` | Two harness runs give identical `view()` JSON; a subprocess with a different `PYTHONHASHSEED` gives the same digest | 1 |
| RL | `tests/agent/test_rules.py` | Grep `agent/`: no `time.time`, `import random`, `from random`, `datetime.now`, `hash(`; no imports of world, eval, server, ais | 1 |

D owns the cross-system tests (D1–D3, F1–F5, smoke). A's tests above stay inside A's folders.

---

## 9. Phases (each = one branch, one PR)

Times are the team schedule from `docs/PLAN.md`; hours are judgement estimates.

| Phase | When | Branch | Build | Done check |
|---|---|---|---|---|
| **0 Contract** | Fri 19:15–21:00 | `a/contract` | Section 5 in full; D5, C1; resolve D-1…D-9 with Javier, B, C | Smoke + contract tests green; B and C approve the PR before 21:00; `python -m contract.export` writes `schema.json` |
| **1 Core** | Fri 21:00–24:00 | `a/core` | `net.py`, `table.py`, `core.py` skeleton (HB, REC re-advertise, inbox handling, `view()`), `shore.py` heartbeat only, `tests/agent/harness.py` | N1–N4, T1–T3, DT, RL green; in the harness five agents converge on one table |
| **2 Auction** | Sat 08:00–12:00 | `a/auction` | `tour.py`, `auction.py`, return rule, `policy` switch, integration with B's world (first real run around 11:00) | G1, P0–P3, P6 green; **core-fallback (Sat 12:00) runs end to end with B's world** |
| **3 Robustness** | Sat 12:00–15:00 | `a/robust` | Quorum, cycle cap, `energy_ok`, two leases, rebalance with F5 | P4, P5, P9, R0 green |
| **4 Relay** | Sat 15:00–18:00 | `a/relay` | Shore age, relay bids, SENTINEL hysteresis, `ShoreNode.picture()` and `command()` with retry | P7, S6 green; C renders the shore picture |
| **5 Contact** | Sat 18:00–21:00 | `a/contact` | `contact.py`, `safety.py`, CMD and VETO handling | ST, S3 green on the scene-like mission and on B's world |
| **6 Deputy (P1)** | Sat 21:00–23:00 | `a/deputy` | `deputy.py` | P8 green; gap vs re-auction logged |
| Fixes | Sun 08:00–10:00 | `a/fix-*` | Bug fixes only | Smoke and story green |

Feature freeze Sat 23:00. Code freeze Sun 10:00.

**Cut order for A** (first to go): deputy; rebalance ratio rule (keep the idle-boat case); close approval movement (keep the flags); SENTINEL hysteresis (plain station keeping); ShoreNode commands (C sends records directly). **Never cut:** merge, leases, auction, return rule, F3 and F4 fixes, the contact keep-in-view, determinism.

**Hard rule** (from `docs/PLAN.md`): a milestone over 60 minutes late triggers the next cut immediately.

---

## 10. Risks and what D should measure

| Risk | Signal | Mitigation |
|---|---|---|
| Timing semantics with B's world (the riskiest integration point) | Bids land in the wrong round; leases flap | Agree D-6 tonight; first real integration Sat 11:00, not 11:59 |
| Rebalance oscillates | Version counts climb | One release per period; D measures version count per task |
| Seg lease too long for a silent death | Dead boat's segments go overdue | Measure 600 / 1,800 / 3,600 s; show the countdown on the console |
| Role penalty value | Story differs from section 2 | `role_penalty_s` in config; D runs 0 / 6,000 / 12,000 |
| Contact never detected in some seeds | Scout phase misses C-07 | Expected (docs say report detection as a distribution); pick the demo seed accordingly |
| Shore link 14 km is a modelled assumption | | Say "narrowband or licensed link, modelled" |

Numbers D should report from A's side: time from event to all cable segments owned; versions per task (churn); contact: time from detection to watcher in view; slots per reassignment; deputy gap vs re-auction (if built).

---

## 11. Do not

- Do not claim consensus, CBBA, SSI bounds, "no radio traffic", "detects dark ships", "prevents" anything, or any saving percentage.
- Do not let the agent read files, config or the clock; everything comes through `Params`, `Mission`, `Own`, `Detection` and the inbox.
- Do not give agents world truth (no global positions, no ground-truth ages). Visit credit and ages are D's evaluator, from true positions.
- Do not change `contract/` after 21:00 without A + B + C approval.
- Do not build ECO, DORMANT, cues, spoofing or radio hardware unless Javier says so.
