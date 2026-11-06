# HANDOFF — franko-initial-fable

State of the Challenge 07 build as of 6 Nov 2026 (pre-kickoff), written so that a new session or a new laptop can run it with nothing but this repo and the AIS clip.

## 0. Thirty-second summary

Five simulated USVs guard a 25 × 10 km box of the Great Belt. No coordinator: every boat runs the same code, bids for work in 12 s auction slots, merges task records by a fixed rule and uses 60 s leases to notice dead boats. The shore console sees only what the radio delivered. A fixed event tape (battery return at 7,200 s, link cut at 7,320 s, synthetic dark contact, departure, link back) plays through a 4 h mission; three modes (static, off, elysa) run on identical inputs and are scored on **cable kilometres overdue** beside **lane crossings in camera view**. Everything is deterministic, replayable and tested (37 acceptance tests). Dashboard, batch runner, replay checker and signed evidence log all work.

## 1. Get it running on another machine

Requirements: Python 3.12 or newer (built and tested on 3.14.3, Windows 11), Node optional (only `node --check` for JS), Chrome or any browser. No internet needed after `pip install`.

```powershell
git clone <this repo> edth07
cd edth07
py -3.14 -m venv .venv            # or python3 -m venv .venv
.\.venv\Scripts\Activate.ps1      # cmd: .venv\Scripts\activate.bat ; bash: source .venv/bin/activate
python -m pip install -r requirements.txt
pytest -q tests\smoke             # 4 tests, ~10 s. Must pass.
```

Then **copy `ais-clip-box.csv` into `data/`** by USB or chat. It is gitignored on purpose (Danish Maritime Authority AIS, anonymised, keep inside the team). The master copy is at `C:\Users\franc\Desktop\studia\ElysasSecret\EDTH\research_notes\Challenge 07 scoring research\ais-clip-box.csv` on Franciszek's laptop (6.9 MB, 61,408 rows). Without it everything still runs, with AIS cues and lane-crossing counts off.

Run:

```powershell
python -m server.bridge --seed 1          # live demo -> open http://localhost:8000/
python -m eval.run_batch                  # 3 modes x 5 seeds, ~90 s -> runs\<hash>\scorecard.md
python -m eval.run_batch --speed 3.0 --out runs\sens_speed3
python -m eval.run_batch --radio 4000 --out runs\sens_radio4
python -m tools.scene_check               # Friday re-measure printout
python -m server.replay runs\<hash>\elysa_s1.jsonl
python -m evidence.verify runs\<hash>\elysa_s1_evidence.json
pytest -q                                 # all 37 tests, ~3 min
```

Gotchas seen so far:
- `ModuleNotFoundError: websockets` = the venv is not active (in cmd use `activate.bat`, or call `.venv\Scripts\python.exe` directly).
- `only one usage of each socket address` = an old bridge still holds port 8765. `netstat -ano | findstr :8765` then `taskkill /F /PID <pid>`. Or run with `--http 8001 --port 8766` and change the port in `web/panels.js` (search `8765`).
- The bridge prints one line, then warms up 3 h of sim for ~10 s, then prints the ws line. Refresh the page after that.
- Boats move about 1 pixel every few seconds at 240×; watch the clock, the next-event countdown and the narrator panel.

## 2. Repository map

```
config/default.toml       every number; hashed into each run log. [agent] sweep/repair are the mode switches
scenarios/fixed.toml      the event tape (t in sim seconds)
data/scene-coordinates.json  box, cable lines (OSM), lane measured from AIS, stations   (committed)
data/ais-clip-box.csv     one AIS day inside the box (GITIGNORED, copy by hand)
contract/   constants.py messages.py tasks.py (Rec, key, merge) views.py config.py    frozen interfaces
agent/      core.py (Agent.step) table.py auction.py tour.py relay.py contact.py cues.py deputy.py shore.py
world/      geo.py routes.py motion.py sensors.py channel.py radio.py sim.py (Sim.step, warm-up, hashes, log)
eval/       metrics.py (ground truth) run_batch.py report.py
server/     bridge.py (WebSocket + static + narrator + injections) replay.py
web/        index.html map.js panels.js (no build step)
ais/        replay.py            evidence/ chain.py verify.py            tools/ scene_check.py timeline.py
tests/      smoke determinism fairness protocol story (incl. real scene)
docs/       manual.md (team manual) results.md (measured numbers) pitch.md deck_outline.md standing_orders.md
            runbook.md mentor_log.md pre_existing_work.md scorecard_*.md scene_check_output.txt HANDOFF.md
runs/       gitignored outputs
```

Git: work is on branch `claude/core` (also pushed as `franko-initial-fable`). Tag `core-fallback` = first green build. Teammates should branch from it; keep `main` for merges.

## 3. How it works (the mechanism, in order)

1. **Scene.** `world/routes.py` projects lat/lon to local metres (equirectangular about 55.40 N 11.00 E), clips the three scenario cables to the rotated box, splits them into ≤5 km segments (7 total: H:0-2, G:0-2, M:0; 23.6 km) and samples every 100 m (241 samples). Pickets N and S sit on H and G 1.5 km west of the lane; relay station at 55.405 N 10.975 E; shore is Korsør.
2. **Tick.** `Sim.step` once per sim second: apply tape events and injections, move boats and vessels, serve AIS pings to boats within class range, deliver radio, step each agent with only its own sensors and inbox, step the shore node, update metrics, log snapshot (every 10 s) and state hash (every 60 s).
3. **Warm-up.** Each run starts at t = −10,800 s with repair off and no battery drain, so all modes start from the same positions and ages (hash logged as `warm_hash`). Seeds vary each boat's phase along its loop and the radio tape.
4. **Radio.** Broadcast to every node in range (8 km boat, 14 km shore), per-link drop/delay pre-drawn per seed (`channel.py`), messages are bytes, 4 hops max, cuts and failures per directed link or node.
5. **Table and merge.** `Rec(task, ver, state, bid, owner, deputy)`; merge key `(ver, state, -bid, owner, deputy)`, highest wins. States RELEASED/CLAIMED/VETOED(=closed). Heartbeats every 5 s carry the whole table plus peer summaries; a heartbeat or a peer summary renews that boat's lease (60 s).
6. **Auction.** `auction.on_slot` every 12 s: one bid on the first open eligible task in order relay, contact, cue, seg, pick, after the task has been seen open for ≥6 s. Cost = loop length after cheapest insertion + transit + battery term. `close_round` next slot: cheapest wins, tie to higher ID, publish claim at ver+1 (deputy = runner-up for relay/contact). Quorum: expired *segments* need a live majority. Rebalance every 300 s if my loop > 1.25× the lightest peer.
7. **Roles.** Relay: a boat with no shore path for 30 s bids (needs a live peer; scouts defer to idle/picket boats). Picket: lowest priority, released when the boat wins a segment or contact. Return: when battery − reserve ≤ trip home, release everything and go to Korsør.
8. **Contact.** `contact.py`: camera track, no AIS match within 500 m/60 s, < 1 kn, within 500 m of a cable sample for 180 s → open `contact:<id>`, detector HOLDS until the winner reports in view. Winner SHADOWs at 1,852 m stand-off (500 m after Approve), closes on cannot-hold (contact faster than 2.3 m/s), stale 60 s, cap 1,800 s, Stop (VETOED record) or return; offline → report queued.
9. **Cues (P1).** `cues.py`: dead-reckon each AIS ping 600 s; if it meets a cable and (sog < 3 kn or crossing > 1 km off lane) open `cue:<track>:<cable>` (expires 180 s); military/law enforcement = report only. Winner goes, looks within 500 m, closes.
10. **Metrics.** `eval/metrics.py`: sample age = time since a live boat passed within 500 m; km overdue vs 12,000 s target; worst age; time to all segments owned; crossings of scenario cables by real AIS tracks and whether a live boat was within 2 km; detection and in-view times; operator actions.
11. **Evidence.** Per-boat hash chain, Ed25519 heads (keys derived from seed), heads carried in heartbeats; `evidence.verify` names the first bad sequence.

## 4. Measured results (final code, 5 seeds, medians)

| Cable km overdue at end | static | off | elysa |
|---|---|---|---|
| 2.3 m/s, 8 km radio (main) | 20.1 | 7.7 | **3.0** (1.5 to 5.5) |
| 3.0 m/s | – | 3.3 | 1.3 |
| 4 km boat radio | 20.8 | 7.7 | 5.1 |

Main run also: lane crossings in view 14 / 13 / 16 of 17; time to all segments owned 60 s (elysa); dark contact detected in 2 of 5 seeds (33% over 30 seeds; phase-dependent, loiter window 1,880 s of an 8,700 s sweep); median 193 s loiter-to-detection, 426 s to shadow in view. Full tables and the honest readings: `docs/results.md`, `docs/scorecard_*.md`. Demo seed = 1 (detect 7,525 s, in view 7,757 s, cannot hold 9,200 s).

Checks passed: replay matched 240/240 hashes; same seed across processes with different PYTHONHASHSEED identical; off mode makes 0 repair claims after T; adjacent modes differ by exactly one config key; evidence chains verify and a one-line edit is caught.

## 5. Deviations from the written plan (and why)

- HVDC is 10.02 km in the box → 3 segments, not 2 (7 segments total). Finer repair granularity; keep.
- Quorum rule is applied to segments only; applying it to relay deadlocked re-election on the cut-off side.
- A task must be seen open for half a slot before a bid, or the detecting boat wins the contact uncontested.
- Relay bids need a live peer, and cable scouts defer to idle/picket boats; otherwise isolated boats all turned into relays (found by the 4 km sensitivity).
- Liveness is gossiped: a peer's summary of you renews your lease. Heartbeats are not forwarded.
- In this geometry repair does **not** reduce lane crossings in view (boat 4 sweeps G past the lane crossing). Pickets end uncovered, crossings do not drop. Say what was measured.
- Deps trimmed to numpy, websockets, pytest, hypothesis, cryptography, pandas (no shapely/pyproj/msgspec).

## 6. What is still for humans (plan steps not doable here)

Mentor round and one-page decision (`docs/mentor_log.md`), deck (`docs/deck_outline.md`), video, 20 s failure clips, rehearsals, chart check that stations are water, `[TO CONFIRM]` items: pre-event code rule, submission time, challenge owner, team number, target user. Known soft spots a juror may probe: no land mask, modelled radios, thresholds set on the same AIS day, detection depends on scout phase.

## 7. If you only have five minutes

`python -m server.bridge --seed 1`, open the page, Shore view, press space when the clock reaches ~02:00:00, then Resume and watch boat 1 leave, boat 4 take its segments and picket S go red, the 4–shore link cut, boat 2 find the contact and boat 3 take it. Then click Kill 5 and watch the north elect a new relay. The narrator panel explains each step in a sentence.
