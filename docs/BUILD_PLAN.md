# Challenge 07 build plan

Extracted from reports/Challenge 07 scoring research.md. All hours are judgement estimates. Scratch-model figures must be replaced by real runs.


All hours are judgement estimates. Assign real names to slots A to D at kickoff; the notes hold no skill data, so this report does not. Sleep is assumed from 00:00 to 08:00.

### Before kickoff today

Log in to the EDTH platform and read `/challenges` and `/agenda`; both exist behind login and likely answer owner, mentors, hardware and start time. Confirm whether hacking starts at 18:00 ([Luma](https://luma.com/edth-2026-copenhagen)) or the plan's 19:00, and use any extra hour on the contract. Note the assigned team number, which starts the deck filename and is not the challenge number. Run the install below on every laptop, on venue Wi-Fi, with one Python minor version. Keep `ais-clip-box.csv` out of any public repository: EDTH treats shared material as non-confidential (Onboarding PDF p.1), and rare type and length combinations could narrow a vessel down. Copy `scene-coordinates.json` and the clip into `data/`, and list both on a "pre-existing work" slide: the Paris 2026 FAQ says only event work counts ([FAQ](https://events.eurodefense.tech/paris-2026/hackathon-faq)). Franciszek needs to empty the Recycle Bin to finish deleting the raw AIS data, as the notes record.

### Repo and install

```text
edth07/
  requirements.txt
  config/default.toml      every number, hashed into each run
  scenarios/fixed.toml     event tape
  data/                    scene-coordinates.json, ais-clip-box.csv (gitignored)
  contract/                frozen Fri 21:00; change needs A + B
    constants.py messages.py tasks.py views.py
  agent/      (A)          imports contract only
    core.py table.py auction.py tour.py relay.py contact.py deputy.py
  world/      (B)
    sim.py routes.py motion.py sensors.py radio.py channel.py
  eval/       (D)          never imported by agent/
    metrics.py run_batch.py report.py
  tools/      (D)          scene_check.py
  server/     (C)          bridge.py replay.py
  web/        (C)          index.html map.js panels.js
  ais/        (B)          replay.py cues.py
  evidence/   (C)          chain.py verify.py
  tests/      smoke/ protocol/ fairness/ story/
  runs/                    gitignored
```

Rules: each person stays in their folder, `contract/` changes by pull request only, `main` must always pass `pytest -q tests/smoke`, and a tagged `core-fallback` stays runnable.

`requirements.txt` (versions from PyPI metadata, not installed or tested here; if msgspec has no wheel for your Python, use dataclasses with stdlib json):

```text
numpy==2.5.4
shapely==2.2.0
websockets==17.4
msgspec==0.22.0
pytest==9.2.0
hypothesis==6.170.14
cryptography==50.0.2
rfc8785==0.1.4
pandas==3.0.5
pyproj==3.8.0
```

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "import numpy, shapely, websockets, msgspec, cryptography, rfc8785; print('ok')"
```

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Configuration: every number in one file

```toml
# config/default.toml  -- chosen test inputs, not measured capabilities
[scene]
file = "data/scene-coordinates.json"   # lines clipped to the 25 x 10 km box
scenario_lines = ["HVDC_Storebaelt_I", "MV_60kV_Sprogo_Funen", "Great_Belt_1_fibre"]
shore = [55.3316, 11.1303]             # Korsor
relay_station = [55.405, 10.975]
picket_n = [55.4578, 10.9081]          # on HVDC, 1.5 km west of lane
picket_s = [55.3543, 11.0135]          # on Great Belt 1, 1.5 km west of lane
segment_max_m = 5000
sample_step_m = 100

[boat]
speed_mps = 2.3            # sensitivity 3.0
endurance_s = 25200
reserve_s = 1800
r_verify_m = 500
r_detect_m = {dusk = 2000, ship_day = 5000, small_day = 1500, night_unlit = 500}
keep_in_view_m = 2000
standoff_m = 1852
standoff_floor_m = 500
ais_class_a_m = 20000
ais_class_b_m = 8000

[radio]
boat_m = 8000              # sensitivity 4000
shore_m = 14000
delay_s = [0.25, 1.0]
loss = 0.05
max_hops = 4

[run]
horizon_s = 14400
evaluate_s = 14000
revisit_target_s = 12000   # confirm Friday
tick_s = 1
seeds = [1, 2, 3, 4, 5]
```

### Contract: messages, tasks, constants

Time is integer milliseconds from the sim clock, passed as an argument. Agents never call `time.time()`. Messages cross the radio as encoded bytes, which blocks shared objects, the likeliest hidden leak.

```python
# contract/constants.py
HEARTBEAT=5_000; PEER_STALE=20_000; LEASE=60_000; SLOT=12_000
DEPUTY_GRACE=10_000; REBALANCE=300_000; SHORE_SILENCE=30_000
CONTACT_STALE=60_000; SHADOW_CAP=1_800_000; CUE_TTL=180_000
CYCLE_MAX=21_600_000   # 6 h
RELEASED, CLAIMED, VETOED = 0, 1, 2

# contract/messages.py   Envelope, every message
# msg_id, src, t_created, t_expire, kind, hops, payload
# kind in HB, BID, REC, OBS, CONTACT, VETO, ACK
# Expiry: HB and BID 12 s; REC, OBS, CONTACT 60 s; VETO 30 s. Retry every 5 s. Max 4 hops.
# Forwarding never refreshes t_created or an observation time.

# contract/tasks.py
@dataclass(frozen=True, slots=True)
class Rec: task:str; ver:int; state:int; bid:int; owner:int; deputy:int  # deputy 0 = none

def key(r): return (r.ver, r.state, -r.bid, r.owner)
def merge(a, b): return a if key(a) >= key(b) else b
```

| Task ID | Kind | Bid order | Created by | Notes |
|---|---|---|---|---|
| `relay` | relay | 1 | Mission file | Deputy allowed |
| `contact:C-07` | contact | 2 | Detecting boat | Deputy allowed; ID stable across boats |
| `cue:{track}:{cable}` | cue | 3 | Any boat hearing the ping | P1; expires after `CUE_TTL`; ID deterministic so records merge |
| `seg:H:0`, `seg:H:1`, `seg:G:0..2`, `seg:M:0` | seg | 4 | Mission file | HVDC, Great Belt 1, 60 kV |
| `pick:N`, `pick:S` | pick | 5 | Mission file | Lowest priority; a boat that wins any `seg` releases its `pick` |

Initial owners: 01 `seg:G:*` and `seg:M:0`; 02 `seg:H:*`; 03 `pick:N`; 04 `pick:S`; 05 `relay`.

```python
# agent/table.py  One lease per boat. Heartbeats renew all of a boat's tasks.
def lease_ok(b, t): return b == me or t <= last_hb[b] + LEASE

def is_open(task, t):
    r = table[task]
    if r.state == RELEASED: return True
    if r.state == VETOED or lease_ok(r.owner, t): return False
    if r.deputy and t < last_hb[r.owner] + LEASE + DEPUTY_GRACE: return False
    return True

def on_record(r):
    cur = table[r.task]; new = merge(cur, r)
    if new is cur: return
    table[r.task] = new; forward(new)
    if cur.owner == me and cur.state == CLAIMED and new.owner != me:
        drop_from_tour(r.task)

# agent/auction.py  Slotted rounds on shared time. No coordinator.
def on_slot(t):                     # fires when t % SLOT == 0
    e = t // SLOT
    close_round(e-1, t)
    for task in sorted(table, key=bid_order):
        if is_open(task, t) and can_bid(task, t):
            send(Bid(task, e, bid_cost(task), me)); break   # one bid per slot

def close_round(e, t):
    for task, bs in sorted(bids.pop(e, {}).items()):
        if not is_open(task, t): continue          # live claim arrived: cancel
        bs = sorted(bs, key=lambda b: (b.cost, -b.boat))
        if bs[0].boat == me:
            dep = bs[1].boat if len(bs) > 1 and kind(task) in ("relay", "contact") else 0
            publish(Rec(task, max_ver(task)+1, CLAIMED, bs[0].cost, me, dep))
            insert_into_tour(task)
            if kind(task) == "seg" and owns("pick"): release(my_pick())

def cycle_after(task):  return cheapest_insertion_length(tour, task) * 1000 // V_MM_S
def bid_cost(task):     return cycle_after(task) + 1_800_000 * (1000 - batt_permille) // 1000

def can_bid(task, t):
    if mode in (RETURNING, UNAVAILABLE): return False
    k = kind(task)
    if k == "seg":
        if mode == SHADOWING or i_am_relay(): return False
        r = table[task]
        if r.state == CLAIMED and 1 + live_peers(t) < n_active()//2 + 1:
            return False                       # expiry takeover needs a live majority
        cyc = cycle_after(task)
        return cyc <= CYCLE_MAX and energy_ok(cyc)
    if k == "pick":
        return mode == PATROL and not i_am_relay() and not owns("seg")
    if k == "relay":
        return shore_age(t) > SHORE_SILENCE and energy_ok_relay()
    if k == "contact":
        return (not i_am_relay() and not i_am_last_cable_owner()
                and energy_ok_contact() and contact_speed(task) <= V)
    if k == "cue":
        return (not i_am_relay() and not i_am_last_cable_owner()
                and eta_ok(task))     # (dist - R_VERIFY)/V <= t_cross - t - margin
# n_active drops boats that announced return, or have been silent 600 s.

def on_rebalance(t):                 # every REBALANCE, staggered by boat ID
    lo = min(available_peers(t), key=cycle)
    if my_cycle() > 1.25*lo.cycle and len(tour) >= 2 and not any_open(t):
        s = segment_whose_removal_lowers_max_cycle(lo)
        if estimated_cycle_after(lo, s) < my_cycle():
            publish(Rec(s, max_ver(s)+1, RELEASED, 0, me, 0))

# agent/deputy.py  P1. Relay and contact only.
def on_tick(t):
    for task, r in table.items():
        if r.deputy == me and r.state == CLAIMED and not lease_ok(r.owner, t):
            if can_bid(task, t):
                publish(Rec(task, r.ver+1, CLAIMED, bid_cost(task), me, 0))
            else:
                publish(Rec(task, r.ver+1, RELEASED, 0, me, 0))

# ais/cues.py  P1. Runs on each boat, only on pings inside its modelled reception range.
def on_ais(ping, t):
    hit = first_cable_hit(ping.x, ping.y, ping.sog, ping.cog, horizon_s=600)   # 10 min dead reckoning
    if not hit: return
    if (ping.sog_kn < 3 or lane_offset_m(hit.point) > 1000) and ping.ship_type not in EXCLUDE:
        open_task(f"cue:{ping.track}:{hit.cable}", hit.point, hit.t, expires=t+CUE_TTL)
# EXCLUDE = pleasure, sailing, SAR, pilot, law enforcement, military (report only).
```

Stop is a record: `Rec(contact_id, ver+1, VETOED, 0, 0, 0)`. Scout rule: the scout keeps the contact until another boat reports it in view within 2,000 m, and only then releases. Stale means no boat has observed it for 60 s. Offline rule: keep watching until reserve or the 1,800 s cap, never escalate, queue the report. Merge guarantee language: eventual convergence per connected group, given delivery. Name it correctly: fixed-order sequential single-item auction, per-task last-writer-wins register with a logical counter and replica-ID tie-break, and leases. It is not CBBA and not consensus, and it carries no SSI bounds.

Snapshot, sent over WebSocket at 5 to 10 Hz on two channels, `/shore` (delivered data only) and `/truth` (evaluator panel, labelled):

```json
{"t":0,"speed":240,"boats":[{"id":1,"x":0,"y":0,"mode":"PATROL","batt":1000,"link":"direct","tour":["seg:G:0"]}],
 "tasks":{"seg:G:0":{"v":1,"owner":1,"deputy":0,"state":1}},"seg_age":{},"contacts":[],"events":[]}
```

Run log is JSONL: line 1 holds seed, config hash, git commit and schema version; then events, snapshots every 10 sim-s, and a state hash every 60 sim-s. Replay re-runs from seed plus injection list and checks hashes.

### The fixed event script

`t = 0` maps to file clock **10:15** on 3 November 2026, treated as UTC (unverified). That window holds 33 crossings and 5 filtered ones. A boat's AIS receiver only gets pings inside its modelled range, never a global table.

```toml
# scenarios/fixed.toml
[[event]]
t = 0
kind = "reset"
warm = "warm_state.json"
ais_t0 = "2026-11-03T10:15:00"

[[event]]             # brief: "one USV runs low on battery and heads home"
t = 7200
kind = "battery_low"
boat = 1

[[event]]             # brief: "another loses its link to the control station"
t = 7320
kind = "link_off"
a = 4
b = "shore"

[[event]]             # synthetic; starts the 180 s dwell. Never a real vessel.
t = 7320
kind = "contact_start"
id = "C-07"
lat = 55.4505
lon = 10.8706
ais = false
sog_kn = 0.4
class = "dusk"

[[event]]
t = 9200
kind = "contact_depart"
id = "C-07"
sog_kn = 6.0
course = 255

[[event]]
t = 10800
kind = "link_on"
a = 4
b = "shore"

[[event]]
t = 14000
kind = "evaluate"
```

| Sim time | What happens | Screen |
|---|---|---|
| 0 to 3,700 | Warm start. 01 and 02 sweep, 03 and 04 picket, 05 relays | Roles, ages, links |
| About 3,770 | Replayed AIS cue: cargo track 3.3 km off lane at the HVDC (P1) | "Cue for a look", not "suspicious" |
| 7,200 | 01 low battery, heads to Korsør. Its cable tasks open | Caution. `seg:G:*` open |
| About 7,212 to 7,250 | 04 wins them, releases `pick:S` | "Lane picket S uncovered" stays visible |
| 7,320 | 04's direct shore link cut; traffic flows through 05. C-07 begins loitering | Crossed link; peer path shown |
| About 7,500 in the demo seed | 02 detects within 2,000 m; 180 s dwell met | Warning card; no AIS match |
| About 7,500 to 7,800 | 03 nearest free, moves to stand-off; 02 holds until 03 has it in view | "Keeping in view. Standing Order 2." `pick:N` open |
| Scripted | Confirm; then Approve "Close to 500 m, photograph both bows" | Name NOT READ, Anchor NOT SEEN until close |
| 9,200 | C-07 departs at 6 kn, above boat speed | "Cannot hold"; report queued; last course logged |
| After 9,200 | 03 returns to `pick:N`; no idle boat | Gap stays open at picket S |
| 10,800 | 04 link back; records merge | Reconciled ownership |
| About 12,570 | Military track off lane: no cue, report only | Keep clear |
| About 12,790, 13,330 to 13,360 | Replayed cues at Great Belt 1 during the degraded fleet: one tug; two slow tracks moving together | The cost of an alert, measured |
| 14,000 | Evaluate | Scorecard |

C-07 sits on the public HVDC line about 4 km west of the lane, 2.5 km from the north picket, so the picket cannot see it at 2,000 m and only a sweeping scout can. That is the "why patrol" case in one event. Detection time varies by seed because the scout's phase varies, so report it as a distribution. **Phase drives the spread in the scratch model (3.5 to 9.2 km), so the five batch seeds must vary warm-up phase as well as the radio tape.** Pick the demo seed where detection lands near 7,500 s. The time-warp must read this tape, slowing before each event, or the viewer misses the repair.

### Numbered steps

| # | When | Slot | Build | Depends on | Hours | Done test |
|---|---|---|---|---|---|---|
| 1 | Fri 19:00 | All | Assign names to slots. Confirm owner of 07 if known. Create repo, `pytest -q tests/smoke` empty pass | Pre-kickoff | 1 total | Names on the wall, repo cloned by four |
| 2 | 19:15 to 21:00 | A + B | M0 `contract/` as above, `config/default.toml`, `scenarios/fixed.toml`, fake radio timing test | 1 | 4 | Schema frozen; fake radio delivers a bid inside one slot |
| 3 | 19:15 to 21:00 | D + C | Mentor round (section below). Mentor log: "assumed X, mentor said Y, changed Z" | 1 | 3.5 | One-page decision: user, metric, policy, business line |
| 4 | 20:30 | C | Review `views.py` snapshot shape with A and B | 2 | 0.5 | C signs off the JSON |
| 5 | 21:00 to 24:00 | B | M1a `world/routes.py`: load JSON, equirectangular metres about 55.40 N 11.00 E, clip to box, split to ≤5 km, 100 m samples. `motion.py`: 2.3 m/s, 1 s tick | 2 | 3 | 6 segments, 23.5 km, 235 samples ±2; five boats move |
| 6 | 21:00 to 24:00 | A | M3 `table.py`, `core.py`: Rec store, merge, heartbeat, per-boat lease, `is_open`, `on_record` | 2 | 3 | D5 Hypothesis passes: merge commutative, associative, idempotent |
| 7 | 21:00 to 24:00 | C | `web/index.html`, `map.js`: Canvas in local metres, cables, lane, Korsør, boats, ages, from a fake snapshot. No tiles, no bundler | 4 | 3 | Map renders offline |
| 8 | 21:00 to 23:00 | D | M7a `eval/metrics.py`: sample ages, km overdue, worst age. Warm-up to `warm_state.json` | 5 | 2 | Ages seeded and identical across two runs |
| 9 | 23:00 to 24:00 | D | **Friday re-measure.** `tools/scene_check.py`: worst age per boat at 2.3 and 3.0 m/s, return limit per boat, radio graph at stations, chart check of all stations and C-07 by eye | 5 | 1 | Revisit target set; graph connected; no station on land |
| | **Sat 00:00** | | **Milestone: five boats, real scene, freshness on map** | 5, 7, 8 | | Reset deterministic |
| 10 | Sat 08:00 to 12:00 | A | M4a `auction.py`, `tour.py`: slots, bids, cheapest insertion, repair, pick release on seg win | 6 | 4 | P1, P2, P3, P6 pass; remove any boat and tasks reassign |
| 11 | 08:00 to 10:00 | B | M1b battery, return rule, `sensors.py` two radii, own-sensor views only | 5 | 2 | D6 import test passes; return rule fires at the computed time |
| 12 | 10:00 to 12:00 | B | M2a `radio.py` heap of (deliver_ms, seq, dst, msg), range check on send and deliver, `channel.py` pre-drawn drop and delay tape via `Generator.spawn` | 2 | 2 | Link-off drops packets; tape hash equal across modes |
| 13 | 08:00 to 11:00 | C | M8 `server/bridge.py`, `replay.py`; `/shore` and `/truth` | 7, 11 | 3 | D3 replay matches hashes |
| 14 | 11:00 to 12:00 | C | Failure controls: any boat, any directed link, logged | 13 | 1 | Works for IDs other than 01, 04, 05 |
| 15 | 08:00 to 11:00 | D | M7b `run_batch.py --modes static,off,elysa --seeds 1,2,3,4,5`, fairness tests | 8, 10 | 3 | F1 to F5 pass; config diff between modes is one key |
| 16 | 11:00 to 12:00 | D | First ON/OFF numbers. Apply the gate below. Tag `core-fallback` | 15 | 1 | Gap visible or the rule below fires |
| | **Sat 12:00** | | **Milestone: tagged fallback and baseline runner** | | | Fallback runs from a clean clone |
| 17 | 12:00 to 15:00 | A | M4b quorum, cycle cap, `on_rebalance`, priority order | 10 | 3 | P4, P5 pass |
| 18 | 15:00 to 18:00 | A | M5 `relay.py`, shore-age gossip, split and rejoin, plus integration | 12, 17 | 3 | P7, relay-loss test pass |
| 19 | 12:00 to 14:00 | B | M2b store-and-forward, retry, dedupe by `msg_id` | 12 | 2 | Stale shore data stays stale; observation time never refreshed |
| 20 | 14:00 to 16:30 | B | P1 `ais/replay.py`: load clip, feed pings by reception range, class A 20 km, class B 8 km | 16 green | 2.5 | No boat receives a ping outside range (test) |
| 21 | 16:30 to 18:00 | B | Integration on link loss with A | 18, 19 | 1.5 | Four-hop path works in the real geometry |
| 22 | 12:00 to 16:00 | C | `panels.js`: roles, link status, cable age, picket status, auto-warp from the tape | 13 | 4 | 240× between events, 5× for 120 sim-s around each |
| 23 | 16:00 to 18:00 | C | Decision cards, tiers, Confirm, Stop, Approve, Decline | 22 | 2 | Held action does nothing without an answer |
| 24 | 12:00 to 15:00 | D | M10 protocol tests in `tests/protocol/` | 10 | 3 | P1 to P6 in CI |
| 25 | 15:00 to 18:00 | D | **Deck v0: manufacture, business, market and team slides first** | 3 | 3 | A stranger reads the slides and names buyer, price, market |
| | **Sat 18:00** | | **Milestone: link loss** | | | Split, rejoin, relay loss pass; shore view stale correctly |
| 26 | 18:00 to 21:00 | A | M6 `contact.py`: contact task, scout holds, stand-off, keep-in-view, cannot-hold, Stop, last-scout guard | 18 | 3 | Story tests S1 to S4 pass |
| 27 | 21:00 to 23:00 | A | P1 M13 `deputy.py` | 26 on time | 2 | P8 passes; deputy gap logged against re-auction |
| 28 | 18:00 to 21:00 | B | P1 M16 `ais/cues.py`: dead reckoning, filter, cue task through the same auction, `eta_ok` | 20 | 3 | A replayed cue becomes one boat's task and the cost shows in km overdue |
| 29 | 21:00 to 23:00 | B | Real-scene tests R1 to R3, cross-boat integration | 28 | 2 | Green on three seeds |
| 30 | 18:00 to 21:00 | C | P1 M14 `evidence/chain.py`, `verify.py`: per-boat hash chain, Ed25519 on heads, heads in heartbeats, time source, zone label | 6 | 3 | Edit one line and the verifier names the first bad sequence |
| 31 | 21:00 to 23:00 | C | First full recording | 26 | 2 | A complete video exists on Saturday night |
| 32 | 18:00 to 21:00 | D | `eval/report.py` scorecard; story tests | 24 | 3 | One command prints the scorecard table |
| 33 | 21:00 to 23:00 | D | Deck v1, first timed rehearsal | 25, 32 | 2 | Under 3:00 with a stopwatch |
| | **Sat 23:00** | | **Milestone: contact and approval; feature freeze** | | | Nothing new after this |
| 34 | Sun 08:00 to 09:00 | D | Final batch, at least 5 seeds with varied phase, both speeds | Freeze | 1 | Median and range for every number |
| | **Sun 09:00** | | **Milestone: results** | | | Actual numbers replace all scratch figures |
| 35 | 08:00 to 10:00 | A | Bug fixes only | Freeze | 2 | Smoke and story green |
| 36 | 08:00 to 10:00 | B | Bug fixes; offline copy of everything on two laptops | Freeze | 2 | Runs with Wi-Fi off |
| 37 | 08:00 to 10:00 | C | 20 s clips for each failure choice, one keypress away | Freeze | 2 | Every boat, the relay, one link |
| | **Sun 10:00** | | **Milestone: code freeze** | | | Tag `final` |
| 38 | 10:00 to 10:30 | C + D | Final video; upload (unlisted); test the link signed out | 35 to 37 | 1 | **Video live by 10:30 at latest** |
| 39 | 09:00 to 11:30 | D | Final deck with real results and video link, `NN_ElysasSecret.pdf` | 34, 38 | 1.5 | **Submitted by 11:30**; reopened from the server |
| 40 | 10:30 to 12:00 | All | Timed rehearsals, three with a forced crash | 39 | 2 | Ten runs by pitch time across Saturday and Sunday |

Totals: A 22.25, B 22.25, C 22.75, D 23.25, plus 2 rehearsal, about **92 h against 96 wall-clock hours and 84 focused hours**. That leaves no slack, which is why the cut order is strict. If only one P1 survives, keep AIS cues, because they are the only real-data element and B has the capacity.

### Acceptance tests

Determinism: **D1** same seed in two processes with different `PYTHONHASHSEED` gives identical hashes. **D2** reset mid-run equals a fresh run. **D3** replay from the injection log matches hashes. **D4** grep test: no `time.time`, no global `random`, no iteration over a set without `sorted`. **D5** merge is commutative, associative and idempotent under Hypothesis. **D6** `agent/` imports neither `world/` nor `eval/`.

Fairness: **F1** warm state, event tape and channel tape hashes are equal across modes. **F2** segment ages at T−1 are byte-identical across modes, the strongest single test. **F3** repair-off produces zero repair claims after T. **F4** config diff between modes is exactly one key. **F5** at least 5 seeds, median and range, no single-seed headline.

Protocol: **P1** lost bid: cheaper boat wins on merge. **P2** winner dies mid-round: task re-auctioned next slot. **P3** refresh arrives mid-window: round cancelled. **P4** isolated boat claims nothing expired, and only the majority side claims on expiry (this replaces the plan's split test). **P5** rejoin: no boat idle after two rebalance periods. **P6** claim beats release at equal version. **P7** a group with a shore path elects no relay. **P8** deputy takes the relay with radio silent, or declines.

Story, from the plan: **S1** reset clears leases, queues, random state, ages and action counts, and five boats start 2/2/1. **S2** a different failed boat works the same way. **S3** starting to keep in view works before any operator input; Stop, expired Stop, stale, offline cap and battery return follow the policy. **S4** 04's lost link stays visibly crossed and peer observations still travel. **S5** no "gap closed" claim from assignment alone: a segment counts only after a sensor visit. **S6** relay loss with any current holder; no feasible replacement shows isolation.

Real scene, new: **R1** radio graph at stations is connected and 04 has a real direct link to cut. **R2** no station lies inside the lane band, and no scripted boat dwells there. **R3** AIS pings reach only boats inside modelled range.

### Milestones, cuts and the hard fallback rule

| Milestone | Exit check |
|---|---|
| Fri 21:00 | Contract, owners, default policies frozen; mentor decision written |
| Sat 00:00 | Five boats on the real scene, freshness on map, deterministic reset |
| Sat 12:00 | `core-fallback` tagged, baseline runner works, first gap measured, any boat removable |
| Sat 18:00 | Link loss, split and rejoin, relay takeover; deck v0 with business slides |
| Sat 23:00 | Contact and approval; feature freeze; first full video exists |
| Sun 09:00 | Final batch; real numbers replace all scratch figures |
| Sun 10:00 | Code freeze, tag `final` |
| Sun 10:30 at latest | Video uploaded and link tested signed out |
| Sun 11:30 | Deck submitted, filename starts with team number |
| Sun 12:00 | Hard deadline. Anything after it may not reach the pitch machine (Onboarding PDF p.2) |

**Cut order, first to go:** spoofed boat; evidence-log report (keep the chain); deputy; cue tasks down to one replayed cue; manual-operator run; extra scorecard rows; notification and retry queue; fallback branch variations; peer sharing down to a single-hop relay. **Never cut:** reset, the three-mode baseline, the video, the seven-criteria deck, gaps shown openly.

**Hard fallback rule.** Any milestone more than 60 minutes late triggers the next cut immediately, with no debate. If P0 for an owner is late, that owner's P1 is gone. If at **Sat 12:00 `core-fallback` does not run end to end, all P1 and all other features stop** until it does. If the first ON/OFF run shows no visible gap between modes, D stops feature work with A and fixes tasks or geometry before anything else, because the result slide depends on it. If `main` fails smoke or the batch at **Sun 09:30**, revert to the last green tag, disclose the reduced scope on the deck, and do not debug after 10:00. If the contact story is not running by Sun 09:00, ship Core with a labelled clip of what exists; a Core-only build is not a completed challenge scenario and the deck must say so.

Honesty rules hold throughout: no invented results, no hostile-intent claims, gaps shown openly, and every scratch figure above is replaced by a measured one or dropped.

