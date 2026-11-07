# Integration proof and remaining gates

This records checks performed in this development session, not a final scorecard.
Do not use the figures below as coverage improvement, real-hull performance or a claim
that the complete contact demo/video is delivered.

## Latest acceptance checkpoint: main b50da01

All **270 tests passed** on this Mac, including the slow real-world story and fairness
cases. Lint passed. A new world-only regression replays a seeded sequence of boat off /
restore, directed link cut / restore and battery return through 120 s, comparing physics,
public agent views and the delivered shore picture at checkpoints; reset reproduces it.
Existing server log/replay and hash-seed subprocess tests also pass.

Delivered shore contacts/cards, sample-age and via fixes, oldest-first repair and deputy
are now merged. The old missing-contact/gap observations below describe earlier baselines,
not unresolved assertions about current main. Final seeded scorecards still need D's
acceptance; passing tests is not permission to put preliminary figures on slides.

World boat_restore is merged, but the current bridge still rejects that command: #63
tracks C's enablement. The new regression deliberately replays World.inject payloads, not
pretends server command replay can accept restore already. Python 3.12 stays pinned;
world/README documents Franco's reported Windows installation workaround (#51).
No fresh Windows run, full uploaded video or two-laptop offline test is claimed here.

## Earlier merged implementation

- #12: world scene, physical loop and console API.
- #14: motors-off hotel load, preserving seven-hour cruise endurance.
- #15: boat-side contact policy.
- #16: fixed current/tide and real-scene contact integration.
- #20: real-sim bridge, decision UI, alerts, coverage display and demo controls.
- Integrated engine baseline for the checks below: main `00e892d`.

## Automated and browser checks

- Combined main/world/console Python suite: **156 tests passed** before adding world.check;
  **160 tests passed** with the four audit checks. Lint and targeted formatting passed.
- Strict TypeScript plus Vite production build passed with frozen dependencies.
- Built-console browser test used headless Chromium and blocked all external HTTP requests.
  No external HTTP request attempts or browser exceptions occurred.
- Verified five boat cards and local map canvas; Exercise controls -> USV 02 -> Switch off
  -> accepted -> stale/NO LINK card; truth/shore switch with explicit truth label; reset
  through the WS API; UI Pause/Run; FEED LOST after stopping the server; automatic reconnect.
- A fresh Python environment was created from the lock with `uv sync --locked --offline`
  using this laptop's package cache. Server CLI and smoke tests passed in that fresh env.
- These were tests on one laptop, not physical Wi-Fi-off or two-laptop certification.
- Local artifacts: `/tmp/edth-browser-check/artifacts-pr20/` contains screenshots, result.json,
  server log and a WebM visibly labelled **NOT FINAL DEMO**. These are temporary session
  artifacts, not the final uploaded video or committed repository files.
- Server HTTP readiness was 331 ms (NOT full console/map cold start), and the graceful
  server-loss banner appeared in 112 ms in that one run. Do not generalize these into
  platform-wide guarantees, complete startup certification or abrupt-failure timing.

## Seeded starting-position follow-up (#28)

The earlier fixed-phase audit below is historical (engine `00e892d`). The new default
reset uses deterministic, policy/speed-independent cable offsets for sweepers. Pickets
and relay keep stations. Seed 1 retains the existing demo reference. No historic visits,
lease state or battery depletion are fabricated. `vary_start_phase=False` is an explicit
legacy-position control; truth initial_phase metadata records the strategy and placements.

Validated with original PR #27 in an isolated worktree: all 15 cases (5 seeds x 3 modes,
14,000 s) complete; F1–F5 pass and each mode has 5 distinct coverage outcomes. The overall
batch still exits 1 / PRELIMINARY because shore-gap checks fail. No headline is claimed.
Raw local artifacts: `/tmp/edth-seeded-eval.json` and `/tmp/edth-seeded-eval.txt`.

Full seed-2 elysa through 14,000 s passes D1 (fresh processes with different PYTHONHASHSEED)
and D2 (mid-run reset versus fresh), recorded in `/tmp/edth-seeded-repeat.txt`.
Original eval tests: 14 pass and 1 expected gap xfail. Newer d/eval-warm integration tests:
29 pass and 1 expected gap xfail; no eval/ edits made. Its warm-up helper can explicitly
disable world placement before using its own phase algorithm. Cold spatial variation is
not the same as a pre-mission sensor history; D still owns final warm-state semantics.

## Historical fixed-phase world audit (diagnostic, not eval/)

```bash
uv run python -m world.check --jobs 4 > /tmp/edth-world-audit.json
```

- 30 completed cases: seeds 1–5 x speeds 2300/3000 mm/s x static/off/elysa, through 14,000 s.
- All 10 elysa/off pre-event **physical** hash comparisons matched at the tick before
  the first failure. Hashes exclude complete agent internals; full replay remains a separate gate.
- Starts cold at a fixed phase, with the same chosen current/power inputs. Five radio seeds
  are NOT five warm-up phases. Detection time was identical across seeds at each speed.
  Do not report that as a detection-time distribution or final median/range result.
- At 2300 mm/s in elysa, local detection is 7,859 s, watcher 03 claims at 8,052 s, and dwell /
  cannot_hold flags occur. At 3000 mm/s, detection is 7,320 s, watcher 02 claims at 7,512 s,
  and capped/dwell occur instead. The differing outcomes are preserved, not tuned away.
- All 30 shore pictures still have no contacts: boat policy alone is not the completed
  operator-facing contact story. This is tracked in #17.
- The command reports configuration hashes, explicit policy/speed overrides, diagnostic
  physical hashes, contacts and final boat tasks. It reports no cable-km improvement,
  risk scores, AIS detection quality or final baseline metric.

## Coverage discrepancy confirmation

At t=14,000 s, seed 1, current-enabled real world:

| Segment | Samples visited / total | Worst truth age | Shore segment age |
|---|---|---|---|
| M:0 | 0 / 34 | unknown (None) | 14,000 s |
| G:0 | 35 / 35 | 13,796 s | 5,144 s |
| H:0 | 34 / 34 | 4,379 s | 3 s |

Truth uses worst per-sample age; current shore code resets a whole segment from any-point
proximity and uses t-0 for never-observed segments. These are different quantities, not
just network delay. None in truth means at least one unvisited sample, not necessarily
that the entire segment is unseen (in this M case all 34 actually are unseen).
No gap should be declared closed from assignment alone. A/D must settle delivered sample
semantics and the headline before final claims; see #22. B did not edit their code.

## Gates that cannot be completed by B alone

| Gate | Owner / tracking | What remains |
|---|---|---|
| Delivered shore contacts / automatic decisions | A, #17 | Resolved by #42; current slow story tests pass |
| Directed next-hop semantics | A, #21 | Resolved by #35; current routing checks pass |
| Shore versus truth coverage meaning | A+D, #22 | Per-sample implementation merged #38; latest suite passes |
| Restore through dashboard/command replay | C, #63 | World supports it; bridge rejection must be removed |
| Warm-state, policy definition, channel fairness, metrics | D with A/B, #19 | Varied phases, full eval/, final median/range |
| Static baseline semantics | A+D, #19 | #35 fixes scout hold; D owns final baseline interpretation |
| AIS replay | Private clip from D, #19 | Clip is unavailable to B; never commit CSV |
| Offline land/satellite assets | D, #9 | Coastline placeholder and missing Sentinel image |
| Full video | C/team | Record actual completed story; upload and check signed out |
| Two laptops / cross-platform determinism | Team | Actually run clean clones offline on both machines |

Triage remains gated. Do not replace these gates with the partial recording, cold-start
audit, passing unit tests, or a truth-fed fake shore picture.
