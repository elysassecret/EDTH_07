# Merge handoff: our branch vs the team repo

Written 6 Nov 2026, 22:00, after a read-only comparison of **ours** (`FearedLynx/franko-initial-fable`, branch `claude/core`, 41 tests green on Python 3.14) against **team main** (`elysassecret/EDTH_07` at `d5040a2`, 171 tests green in a 3.14 scratch venv, one Windows-only chmod failure). Both repos follow the same build plan; they were written in parallel by different people, so the question is not "which repo wins" but **which pieces go where**, under the team's folder-ownership rule (`docs/PLAN.md` §3, `CLAUDE.md`). Franco owns slot D: `eval/`, `tools/`, `deck/`, `tests/smoke|eval|story`, `pyproject.toml`, `config/run.toml`, `.github/`.

## 0. The decision in five lines

1. **The team repo is the product.** Its brain (A), world (B) and console (C) are more correct than ours on the merge key, cost function, leases, energy model, directed radio, and console features 17–25. Ours does not replace any of that.
2. **The team repo has no proof.** `eval/` is empty, there is no warm-up, no fairness instrument, no AIS replay, no measured number, no deck, and the shore picture carries no contacts. Every one of those exists in ours and all but one land in Franco's folders.
3. **Port the proof, not the files.** Rewrite our `eval/`, `tools/`, `tests/story` onto the team `World.truth_view()` API; carry our docs into `deck/` and `docs/`; file our brain-side extras (deputy takeover, gossip liveness, shore contact picture, narrator) as issues to A and C with our code attached as reference.
4. **Drop our console, bridge, agent, world and radio.** Keep them only on our branch as a running fallback and a source of test ideas.
5. **Fix two honesty bugs before any number goes on a slide**: team issue #22 (shore segment age) and our fixed-100-m km calculation.

Why this ordering: the jury scores seven equal criteria, 0–10 each (Onboarding PDF p.4: relevant problem, feasibility, originality, mass-manufacturability, business opportunity, size of opportunity, pitch), and the deck must state "what did you achieve during the hackathon" and "how will this be deployed and mass-manufactured" (PDF p.3). The team repo covers feasibility on the engineering side; the measured gain (originality), the honest numbers (feasibility), and the three business criteria (43 % of the score, `docs/research/edth_jury_and_event.md` line 191) are all still missing on `main`, and they are D's job.

## 1. Scorecard by judging criterion

| Criterion (PDF p.4) | Team main today | Ours today | Action |
|---|---|---|---|
| Relevant problem | research notes (`docs/research/operations_incidents_law.md`), no slide | `docs/pitch.md` 0:00–0:35, `deck_outline.md` slide 2 | Port pitch + outline to `deck/` |
| Feasibility ("does it work?") | energy model with current, tide, SENTINEL (features 15–16); console 17–25; 171 tests; **but** shore ages wrong (#22), no contacts on shore (#17), cold start leaves M:0 never visited in 14 000 s | measured 3 modes × 5 seeds × 2 speeds × 2 radio ranges (`docs/results.md`); replay 240/240 hashes; warm-up and fairness tests F1–F5; real AIS crossings | Eval runner onto team world with warm-up (§3); issues #17, #22 to A |
| Originality ("the one insight, with a measured gain", jury doc line 202) | none measured; `world.check` prints hashes, not metrics | 7.7 → 3.0 km overdue off → elysa (median, 5 seeds); "fewer boats cannot close the gap, only choose where it lands" | Re-measure on team world, put on slide 7 |
| Mass-manufacturability | `buyers_market_manufacture.md` §5–6 | one pitch line (retrofit box estimate) | One slide with per-hull BOM from §5–6 |
| Business opportunity | `buyers_market_manufacture.md` §1–3, 7 (vehicle-day model, Saildrone/NORDEFCO precedent, jury doc line 209) | one pitch line | One slide: who signs, budget line, price per vehicle-day |
| Size of opportunity | `buyers_market_manufacture.md` §4, 8 | USD 3.9 bn / 0.8 bn / EUR 3–5 m Baltic in `pitch.md` | Reconcile the two sets of numbers, one sourced slide |
| Pitch | running order in jury doc line 263; no deck | timed 3:00 script, demo keys, failure ladder, do-not-say list | Rehearse from `pitch.md`; demo on the **team** console |

## 2. What to KEEP from ours (lands in Franco's folders, as `d/<thing>` PRs)

Ranked by effect on the score. Every PR: strip `Co-Authored-By` lines (team `CLAUDE.md` forbids them), `ruff check`, smoke green.

| # | Item | Lands in | Why (plan / issue / criterion) |
|---|---|---|---|
| 1 | `eval/metrics.py`, `run_batch.py`, `report.py` rewritten on `World.truth_view()['sample_visit_ms']` with **actual interval lengths** (`RouteSample.offset_m`) and `None` = never visited | `eval/` | Feature 12, issue #19, M7a/b. The only measured gain in either repo. Fixes our own bug: fixed 100 m per sample gives 24.1 km vs the real 23.6 km and double-counts joint samples (`eval/metrics.py:117,134`) |
| 2 | Warm-up (3 h, drain off, repair off), per-seed phase, ages-at-T−1 equality, pre-event hash equality (our F1–F5) | `eval/` runner now; `World(warm_ms, phase)` proposed to B | Issue #19 lists exactly this. Team starts cold at a fixed phase; `world/check.py:81` says so; detection time is identical across seeds, which is not a distribution. Without warm-up the km-overdue is a start-up artifact, not a response to the failure |
| 3 | `ais/replay.py` + lane-crossings-in-view observer, as an **eval-side** observer reading the private CSV (never feeding agents) | `eval/` | Second half of the headline metric (plan M7b). Answers the "synthetic data" criticism the jury research names (jury doc line 208). Team `ais/` is a README |
| 4 | `tools/scene_check.py`, `tools/timeline.py` adapted to team `load_scene` / `World` | `tools/` | Plan "Friday re-measure"; R1–R3 moved to D (`docs/PLAN.md` §1) |
| 5 | `tools/prepare_coastline.py` → `web/public/geo/land.geojson` (currently a 226-byte placeholder) | `tools/` + the three files C allowed | Issue #9, assigned to Franco, wanted Saturday morning. Cheapest visible win on the console |
| 6 | `docs/pitch.md`, `deck_outline.md`, `pre_existing_work.md`, `mentor_log.md`, `standing_orders.md`, `runbook.md` | `deck/` | PDF p.3 deck items c) and d); jury doc lines 190–194 (declare pre-existing work, filename `NN_ProjectName.pdf` with the **team** number, video link, noon deadline) |
| 7 | Story tests S1–S6 and real-scene R1–R3 on the team world (`World.inject`, `ShoreNode.picture()`) | `tests/story/`, `tests/eval/` (both empty on main) | BUILD_PLAN acceptance; "never cut: gaps shown openly" |
| 8 | `docs/results.md` method and `scorecard_*.md` format, re-run on the team sim | `docs/` (unowned; ask in chat first) | Plan Sun 09:00 "real numbers replace all scratch figures" |

Measured numbers from our branch (`docs/results.md`) stay **off the slides** until re-measured on the team world. They are a different simulator (float motion, no current, two-way cuts).

## 3. What to PROPOSE to A, B, C (issue with our module attached, they merge)

| # | To | Proposal | Reference in ours | Why |
|---|---|---|---|---|
| 9 | A | Shore picture built from delivered OBS/CONTACT: contacts with seen-by and age, delegated Confirm/Stop and held Approve/Decline cards, VETO/CMD on answer | `agent/shore.py:52-62, 95-135, 137-166` | Issue #17. Blocks the operator-facing video (PDF p.3 "demo"). Same logic, re-expressed on team `contract/views.Contact/Decision` |
| 10 | A | Shore segment age per sample, `None` for never reported; headline on screen is the **evaluator** value labelled truth, shore value labelled "reported" | `eval/metrics.py:112-114` | Issue #22 (assigned to Javier and Franco). Today shore shows 14 000 s for a never-visited segment and 3 s for one whose end a boat passed: a juror-visible wrong number |
| 11 | A | `via()` fix: shore edge only from `self.direct`, skip 0 in `nbr` | none needed | Issue #21, Alexandru's suggested fix is right |
| 12 | A | Deputy takeover (27 lines) | `agent/deputy.py`, test P8 | Team names a deputy and honours a 10 s grace but nobody takes over, so grace is a pure delay. Plan P1 feature 27 |
| 13 | A | Gossip liveness (peer-reported ages renew leases, optional HB field) and `KNOWN_OPEN_MS` bid guard | `agent/core.py:192-202`, `agent/auction.py:167-179` | Cuts range-edge ownership churn (plan F4) and stops the detecting boat winning the contact uncontested. Both found by our tests, not by design |
| 14 | B | `World(warm_ms=..., phase=...)` hook: drain off, repair off, warm hash | `world/sim.py:82-103, 269-275` | Issue #19; so eval does not poke `x_mm` directly |
| 15 | B | Relax or document `requires-python <3.13`: 3.14 + pip works (171 tests) | `docs/HANDOFF.md` §1 | Two-laptop demo risk; uv is not on Franco's laptop |
| 16 | B then A | AIS replay feed, then cue tasks | `ais/replay.py`, `agent/cues.py` | Feature 26, only after 1–25 green and a video exists (`docs/PLAN.md` §5) |
| 17 | C | `server/narrator.py`: pure function over `World.events`, shore events/decisions and task-owner diffs → plain-language lines, surfaced as an extra snapshot key and a panel | `server/bridge.py:111-190`, `web/panels.js:36-40` | Pitch criterion: the 3-minute slot leaves no time to explain the auction; the narrator says "Boat 4 won G:0, cheapest bid, picket S now uncovered" for you |
| 18 | C | Headline `cable km overdue` + three-mode scorecard pop-up on the console, fed by `eval/` over the WS | `server/bridge.py:107-108`, `web/panels.js:180-199` | Feature 24 says "headline number on screen"; team shows oldest-visit only. Label it truth (issue #22) |
| 19 | C + B | Injection kinds `boat_restore`, `contact_start` at click with snapping to the nearest cable sample, pause at horizon | `server/bridge.py:213-235, 313-315` | Feature 13 "judge picks a failure"; a juror asks "what if the contact is here?" |
| 20 | C + A | Evidence: boats sign their own heads, heads ride in heartbeats, shore stores `witnessed`; one-click tamper demo in the console | `evidence/chain.py:25-27, 91-93`, `server/bridge.py:261-277` | Feature 28. Team `build.py:226` says boats do not sign yet; team is stronger on t_obs/t_log and zones, keep that. Incident report is missing in both (D-sized, `tools/`) |
| 21 | C | Picket "UNCOVERED since HH:MM" duration in the caution alert text | `web/panels.js:81-88` | S5 "gap stays visible"; `server/alerts.py:65-68` has the alert without the duration |

## 4. What to DROP from ours (superseded)

| Ours | Team is better because | Keep only as |
|---|---|---|
| Merge key `(ver, state, -bid, owner, deputy)` | Team key puts VETOED first, so a Stop cannot be out-versioned (plan F1/F2) | nothing |
| Cost = cycle + transit + battery | Team adds a 12 000 s role penalty so pick:N stays free for the contact (plan F3); our own results show both pickets end uncovered | nothing |
| Single 60 s lease | Team: 60 s relay/contact, 3600 s seg/pick (plan F4, less churn) | our gossip liveness still worth proposing (#13 above) |
| Float motion, no current, 1 s drain | Team: integer mm, current with tide flip, hotel load, SENTINEL (features 15–16, "what kills a USV") | nothing |
| Two-way link cuts, pre-drawn tape, no ACK/retry | Team: directed one-way cuts, on-boat forwarding with retry/ACK (`agent/net.py`), counter-keyed channel | tape **hash** idea as a fairness check if B adds warm phases |
| `t % SLOT == 0` scheduling | Team `Every` crosses boundaries, not tick-fragile | nothing |
| Two config keys `sweep/repair` | Team single `policy` key (cleaner F4, "adjacent modes differ by one key") | nothing |
| Vanilla JS console, `ch`-tagged WS frames on `/ws` + `:8000` | Team console covers 17–25 (offline chart, alerts, ghost routes, comms overlay, FEED LOST, EXERCISE, must-return-by) and is the agreed contract `Snapshot` | local debugging page; demo fallback if the team build breaks on the demo laptop |
| `requirements.txt`, `pytest.ini`, 3.14-only venv | Team `pyproject.toml` + uv + 3-OS CI | nothing; install uv on this laptop |

Two things to say openly on the method slide, true in both repos: in `static` and `off` a boat that sees a candidate still holds it and moves to the ring (team `agent/core.py:238-242`, ours `agent/contact.py:82-85`), so "static" means no sweeping and no reassignment, not "never moves"; and repair in this geometry does not reduce lane crossings in view.

## 5. Order of work for Franco (Saturday)

1. **08:00** Install uv, `uv sync`, confirm 171 tests on `main`. Create `d/eval` from `main`.
2. **08:30–12:00** Items 1–3: `eval/metrics.py` on `truth_view()` with interval lengths, warm-up in the runner, AIS observer. Target: `uv run python -m eval.run_batch` prints a scorecard for static/off/elysa × 5 seeds on the team world. This is the Sat 12:00 `core-fallback` exit check ("baseline runner works").
3. **12:00** File issues 9–13 to Javier (one issue each, our file paths attached), 14–15 to Simeone, 17–21 to Alexandru. Comment on #22 with the answer in item 10.
4. **13:00–15:00** Item 5 (coastline, issue #9), item 4 (scene_check).
5. **15:00–18:00** Items 6 and 8: deck v0 with the business slides first (`docs/PLAN.md` §2 "start the deck skeleton with the business slides first"), using `buyers_market_manufacture.md` for the three business criteria and `pitch.md` for the script. Mentor round answers into `mentor_log.md`.
6. **Sun 09:00** Final seeded batch on frozen `main`; numbers onto slides; declare pre-existing work; filename with the team number; video link tested signed-out.

## 6. Sources

- Hacker Onboarding PDF p.3 (deck items a–d, pitch 3 min + 1–2 questions, filename, video link, noon deadline) and p.4 (seven criteria 0–10, scores guide a debate).
- `team_EDTH_07/docs/research/edth_jury_and_event.md` lines 160–210 (criteria, weak vs strong answers, 43 % gap), 246–281 (live demo risk, quote only seeded numbers).
- `team_EDTH_07/docs/PLAN.md` (roles, folder rule, timeline, cut rule), `CLAUDE.md`, `docs/FEATURE_PRIORITIES.md` (features 1–41, slide wording §7), `docs/ARCHITECTURE.md`, `world/VALIDATION.md`.
- GitHub issues `elysassecret/EDTH_07` #9, #17, #19, #21, #22.
- `Challenge07BuildPlan.md` (M1–M7, F1–F5, P1–P8, S1–S6, cut order).
- Ours: `docs/HANDOFF.md`, `docs/results.md`, `docs/pitch.md`.
