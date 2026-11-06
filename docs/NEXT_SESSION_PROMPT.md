# Prompt for the next session (paste everything below the line)

---

You are continuing EDTH Copenhagen 2026, Challenge 07 ("Swarm Coordination for Collaborative Missions", team Elysa's Secret). I am Franco, slot D in the team: I own `eval/`, `tools/`, `deck/`, `tests/smoke`, `tests/eval`, `tests/story`, `config/run.toml`, `pyproject.toml`, `.github/`. Today is Saturday 7 Nov 2026. Feature freeze Sat 23:00, code freeze Sun 10:00, deck and video due Sun 12:00.

## Repositories on this laptop

- **Team repo (the product):** `C:\Users\franc\Desktop\studia\ElysasSecret\EDTH\team_EDTH_07`, remote `elysassecret/EDTH_07`, branch `main`. Python 3.12 via uv per `pyproject.toml`, but Python 3.14 + pip also runs it (171 tests pass). Rules in `CLAUDE.md` and `docs/PLAN.md`: edit only my folders, branch names `d/<thing>`, PR to `main`, `uv run ruff check . && uv run pytest -q tests/smoke` before every PR, **no `Co-Authored-By` or "Generated with Claude" lines in commits or PRs**, never commit `data/*.csv`.
- **My reference branch (proof and docs, different simulator):** `C:\Users\franc\Desktop\studia\ElysasSecret\EDTH\edth07`, remote `FearedLynx/franko-initial-fable`, branch `claude/core`. Read-only source of code to port. Do not develop there any more.
- **The decision document:** `edth07/docs/MERGE_HANDOFF.md`. Read it first. It lists KEEP (port into my folders), PROPOSE (issues to teammates), DROP, with the judging criterion or issue number behind each line. `edth07/docs/HANDOFF.md` explains how my reference branch works.
- **AIS clip:** `EDTH\research_notes\Challenge 07 scoring research\ais-clip-box.csv` (6.9 MB). Copy into `team_EDTH_07/data/` by hand. Gitignored. Never commit it.
- **Judging:** seven criteria scored 0–10 each (relevant problem, feasibility, originality, mass-manufacturability, business opportunity, size of opportunity, pitch), deck must say what was achieved during the hackathon and how it is deployed and mass-manufactured, 3-minute pitch, filename `<team number>_ProjectName.pdf`, video linked in the deck. Sources: Hacker Onboarding PDF p.3–4, `team_EDTH_07/docs/research/edth_jury_and_event.md` lines 160–210.

## Ground rules for this session

- Work in `team_EDTH_07` only, on `d/<thing>` branches cut from a fresh `origin/main`. Commit small and often with plain messages, no attribution lines. Never touch `agent/`, `contract/`, `world/`, `ais/`, `server/`, `web/`, `evidence/` except the three files in `web/public/geo/` that issue #9 explicitly permits.
- Determinism: no `time.time()`, no global `random`, `sorted()` over any set or dict order that matters. Eval never feeds anything into agents.
- Honesty: no invented numbers anywhere. Never-visited is `None`, not a large age. Label every number as truth (evaluator) or shore (reported). Say "cue for a look", never "suspicious".
- When a step needs a teammate's folder, stop and write the GitHub issue instead (templates in step 4). Do not work around ownership.
- Ask me only when a choice changes the headline number's definition. Otherwise decide and note it in the PR description.
- Report after each step with: what passed, exact command, what is still open.

## Step 0: environment (target 08:30)

1. Install uv (`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`), then in `team_EDTH_07`: `git fetch origin && git checkout main && git pull`, `uv sync`, `uv run pytest -q` (expect ~171 pass; `tests/server/test_evidence.py::test_private_key_is_owner_only` may fail on Windows chmod, that is environment-only, note it and move on).
2. Copy the AIS CSV into `data/`. Confirm `git status` does not list it.
3. `git checkout -b d/eval`.

## Step 1: eval runner on the team world (target 12:00; this is the Sat 12:00 `core-fallback` exit check "baseline runner works")

Port from `edth07/eval/{metrics.py,run_batch.py,report.py}` onto the team API. Team API facts (verified): `world.sim.World(root, seed, agent_factory, shore_factory, current_enabled)`, `.step()`, `.t`, `.seed`, `.params` (dataclass with `policy` in `static|off|elysa`, speeds; copy with `dataclasses.replace` then `w.reset()` as `world/check.py:43-45` does), `.truth_view()` returns `seg_age` (ms or `None`), `sample_visit_ms` (241 entries, `None` if never visited), `boats[{id,x,y,batt,enabled,mode,hdg,sog,endurance_ms,lon,lat}]`, `contacts`, `events`, `links`, `current`; `w.scene.samples` is a list of `RouteSample(task, offset_m, point)` at offsets 0,100,… excluding the endpoint (last interval shorter); `w.nodes[b]` is the Agent with `table.recs`, `contacts.first/by/flags`; `w.shore.picture()` and `w.shore.decisions`; `w.inject(...)`; `w.state_hash()` (physical only). Scenario tape in `scenarios/fixed.toml`.

Build:

1. `eval/metrics.py`: `Metrics(world)` with `on_tick()` reading `truth_view()`. Per-sample age from `sample_visit_ms`; **km from actual interval lengths** (diff of `offset_m` within a task, last interval = segment length minus last offset; get segment length from `scene` or from the next sample); `km_overdue` vs `revisit_target_s` from `config/run.toml` (12 000 s); `worst_age_s`; `never_visited_km` reported separately; time to all segments owned (diff `table.recs` across boats, a task is owned when any live boat holds a CLAIMED record); detection time and in-view time for the scripted contact from `nodes[b].contacts.first` and `by[track][owner]['dist'] <= keep_in_view_m`; watcher id from `table.recs['contact:C-07']`; operator actions = `len(shore.decisions)` answered; repair claims after the first failure (version diffs per task per tick, only in `off` mode must be 0); boat distance travelled = sum of `sog * tick`. Ages hash at the tick before the first failure (T−1).
2. **Warm-up**: the team world starts cold at a fixed phase (`world/check.py:81`). Until B ships a `World(warm_ms, phase)` hook (issue in step 4), implement warm-up in the runner: derive a per-boat phase from `numpy.random.default_rng(seed).spawn(5)`, set each boat's start position along its first task polyline before the first step (`Follower.start_nearest` picks it up, `agent/core.py:160-168`), run `warm_s` (10 800) ticks with policy effectively `off` and then reset `charge_ms` to `endurance_ms` and the sim clock to 0 if the API allows; if the clock cannot be reset, keep the offset and document it. Record `warm_hash = w.state_hash()` at the end of warm-up and assert it is identical for `off` and `elysa` at the same seed (fairness test F1). Note in the PR exactly what is byte-identical and what is not.
3. `eval/ais_observer.py`: port `edth07/ais/replay.py` + `Metrics.on_ais` as an **eval-side** observer: read the CSV with pandas, count real cargo/tanker crossings of the three patrolled cables after the first failure, mark "in view" if a live boat is within `keep_in_view_m` (2 000 m) at the crossing. Never pass pings to agents. Degrade gracefully if the CSV is absent (metric row says "AIS clip not present").
4. `eval/run_batch.py`: CLI `--modes static,off,elysa --seeds 1,2,3,4,5 --speed 2300|3000 --radio 8000|4000 --out runs/<config_hash>`; writes one JSONL per run (metrics every 60 s, injections, hashes) and `scorecard.md` via `eval/report.py` (median and min–max per metric per mode; "detected in k of n seeds"). Config hash = sha256 of all `config/*.toml` + `scenarios/fixed.toml` + seed, as `world/check.py:32-36` does.
5. `tests/eval/test_metrics.py`: synthetic world stub tests for interval lengths (sum of km == 23.6 ± 0.05), None handling, overdue counting. `tests/eval/test_fairness.py`: F1 warm-hash equality off vs elysa, F2 ages at T−1 identical, F3 off mode makes 0 repair claims after T, F4 adjacent modes differ by one config key (`policy`). Mark the slow ones `@pytest.mark.slow` and keep `tests/smoke` under 30 s.
6. Run the main batch (3 modes × 5 seeds at 2 300 mm/s) and both sensitivities. Write `docs/results.md` (ask in chat first, `docs/` is unowned) with the table, the honest readings (what repair did and did not improve, detection as a distribution, never-visited km), and the command that reproduces every number. Numbers from the old `edth07` branch are **not** to be reused.
7. PR `d/eval` → `main` titled "eval: metrics, warm-up runner, three-mode scorecard (feature 12, issue #19)". Body: commands, what is byte-identical, open questions for B (warm-up hook), link to #19 and #22.

## Step 2: scene check and coastline (target 15:00)

1. `tools/scene_check.py` from `edth07/tools/scene_check.py` on `world.routes.load_scene(root)`: segment count and km, 241 samples, stations in water and outside the lane band, radio graph connectivity at 8 and 4 km, return-trip limit, pre-event worst age at 2.3 and 3.0 m/s. Print once, save output to `docs/scene_check_output.txt`.
2. Issue #9: `tools/prepare_coastline.py` using shapely: OSM land polygons (osmdata.openstreetmap.de WGS84 split), clip to `data/scene-coordinates.json` box corners + 10 km margin (include Korsør 55.3316 N 11.1303 E and Sprogø), simplify ~20 m, write `web/public/geo/land.geojson` (EPSG:4326, `[lon, lat]`, polygons only, < 1 MB, `properties.source` and `properties.licence` = "© OpenStreetMap contributors, ODbL"). Optional in the same script: `infra.geojson` with the Great Belt Bridge as `{"kind":"bridge","name":...}`. Download needs the internet once; cache the raw file outside the repo. Do not touch anything else in `web/`. PR `d/coastline`, assign Alexandru as reviewer.
3. If time: `tools/incident_report.py` reading `runs/*.jsonl` into a one-page markdown timeline (events, decisions, operator answers, chain OK line), feature 28's missing half.

## Step 3: story and real-scene tests (target 17:00)

`tests/story/test_story.py` S1–S6 and `tests/story/test_real_scene.py` R1–R3 from `edth07/tests/story/`, rewritten on `World.inject` and `w.shore.picture()`: S1 battery return releases tasks and they are re-owned within 2 slots; S2 link cut → shore marks the boat stale and relay path appears; S3 contact detected → held → shadowed in view; S4 cannot-hold on departure; S5 picket uncovered stays visible in the picture until the end; S6 rejoin converges tables. Anything that needs shore contacts (S3/S4 on the shore side) depends on issue #17; write the test, mark it `xfail(reason="#17")`, so it flips green when Javier merges.

## Step 4: issues to teammates (write at 12:00, right after the eval PR is open)

One issue each, title, body with the file path in `FearedLynx/franko-initial-fable` (branch `claude/core`) to use as reference, why (criterion or plan step), done-when. Do not open PRs into their folders.

- **To Javier (A):**
  1. "Shore picture from delivered OBS/CONTACT: contacts, seen-by, Confirm/Stop and Approve/Decline cards" — closes #17; reference `agent/shore.py:52-62,95-135,137-166`; blocks the video.
  2. Comment on **#22**: headline on screen and deck is the evaluator per-sample truth labelled "truth"; shore shows per-sample "reported" age and `None` for never reported; eval PR implements the truth side.
  3. "Deputy takeover" — reference `agent/deputy.py` (27 lines) and test P8; team honours grace but nobody takes over.
  4. "Gossip liveness in heartbeat (optional `peers` field) and 6 s known-open bid guard" — reference `agent/core.py:192-202`, `agent/auction.py:167-179`; cuts range-edge churn, stops detector winning the contact uncontested.
  5. "#21 via() fix" — endorse Alexandru's fix (shore edge from `self.direct` only, skip 0 in `nbr`).
- **To Simeone (B):**
  6. "World warm-up hook `World(warm_ms, phase)`: drain off, repair off, warm hash" — reference `world/sim.py:82-103,269-275`; issue #19; eval currently pokes positions directly.
  7. "Relax or document `requires-python <3.13`" — 3.14 + pip passes the suite; demo-laptop risk.
  8. "AIS replay feed into sensors" (feature 26, only after 1–25 green) — reference `ais/replay.py`; cues in `agent/cues.py` follow for Javier.
- **To Alexandru (C):**
  9. "Narrator panel: plain-language event log" — reference `server/bridge.py:111-190`, `web/panels.js:36-40`; pure function over `World.events`, shore events/decisions, task-owner diffs; pitch criterion.
  10. "Headline `cable km overdue` and three-mode scorecard on the console" — fed by `eval/` over an extra snapshot key; feature 24; label truth.
  11. "Injection kinds: `boat_restore`, `contact_start` at click snapped to nearest cable sample, pause at horizon" — reference `server/bridge.py:213-235,313-315`; feature 13 judge-picks-a-failure; needs B's `World.inject`.
  12. "Evidence: per-boat signed heads in heartbeats, shore `witnessed`, one-click tamper demo" — reference `evidence/chain.py:25-27,91-93`, `server/bridge.py:261-277`; feature 28; keep their t_obs/t_log and zones.
  13. "Picket UNCOVERED since HH:MM in the caution alert" — `server/alerts.py:65-68` lacks duration; plan S5.

## Step 5: deck and pitch assets (target 20:00)

1. Copy `edth07/docs/{pitch.md,deck_outline.md,pre_existing_work.md,mentor_log.md,standing_orders.md,runbook.md}` into `deck/`, strip anything that quotes a number from the old branch, replace with "[from Sun 09:00 batch]".
2. Write the three business slides first (`docs/PLAN.md` §2) from `docs/research/buyers_market_manufacture.md`: mass-manufacturability (per-hull BOM, standard boats and radios, retrofit box), business opportunity (who signs, budget line, price per vehicle-day; Sweden/Saildrone 1 440 vehicle-days under NORDEFCO as precedent), size of opportunity (one sourced multi-billion figure and the steps to it). Reconcile the figures in `pitch.md` with that file; one set of numbers only.
3. Deck v0 as markdown outline in `deck/DECK.md` with 13 slides, each with its criterion in brackets, the "achieved this weekend" slide, the pre-existing-work declaration, a placeholder for the video link, and the filename rule. Do not fake screenshots; mark where real ones from the team console go.
4. PR `d/deck`.

## Step 6: Sunday morning (09:00–11:30)

1. `git checkout main && git pull` after the `final` tag. Re-run the full batch and both sensitivities. Replace every placeholder in `deck/DECK.md` and `docs/results.md`. Median and range for every number.
2. Run `python -m server.replay` on the demo seed and `evidence.verify`; put the result lines in the deck's feasibility slide.
3. Check: filename starts with the **team number** (ask me), video link works signed-out, pre-existing work declared, no number on a slide without a run behind it.

## Definition of done for this session

- `d/eval` merged or open with green CI: `uv run python -m eval.run_batch` prints a scorecard on the team world with warm-up, interval-length km, None handling, AIS crossings when the clip is present.
- `docs/results.md` with honest re-measured numbers (or a clear "not yet" line).
- `land.geojson` real and under 1 MB.
- 13 issues filed with reference paths.
- `deck/` populated, business slides drafted.
- A final message listing: every command that was run and passed, every PR and issue URL, and what is still open for Sunday.
