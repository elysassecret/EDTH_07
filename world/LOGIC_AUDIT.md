# Logical integration audit: main vs local harbour/viewer candidate

Date: 7 November 2026. **Verdict: runs and passes the existing tests, but is not ready for full feature/mission acceptance.**

This is an audit, not a fix commit. No production implementation was changed during this review.
The branch's existing harbour/viewer changes were left intact. Diagnostic files are under
`runs/local/audit/` (ignored); this report is the only new repository source/document file.

## 1. Exactly what was compared

- Branch: `b/viewer-launch-swap`. HEAD and freshly fetched `origin/main` are both
  **`0435058003101fc276e71c36450cf5641c780a2a`**. A final fetch returned the same main.
- There are no missing committed main changes in this branch. The candidate consists of
  **uncommitted tracked changes and untracked files**, not branch commits available on GitHub.
  A successful `git diff HEAD..origin/main` alone would miss all that local work.
- A public, clean main snapshot was extracted with `git archive origin/main` into
  `/tmp/edth-main-audit.5xnI29`. Its Python tests and logical probes ran separately, using this
  laptop's existing Python environment. The private AIS CSV was not copied into that snapshot.
- `origin/c/live-run-ux` exists but is **not merged into main**. Its advertised live-run UX must
  not be counted as delivered in the main/candidate comparison. It was not merged by this audit.
- Requirements reviewed: `docs/PLAN.md`, `docs/ARCHITECTURE.md`, `docs/BUILD_PLAN.md`,
  `docs/FEATURE_PRIORITIES.md`, `agent/PLAN.md`, `agent/RULES.md`. The agent plan explicitly
  supersedes older build-plan pseudocode where documented. Seven real cable segments are not
  treated as a bug merely because the early scratch plan expected six.

### Local implementation delta

| Area | Compared with main | Assessment |
|---|---|---|
| `world/sim.py`, `world/harbour.py`, `world/harbour.json` | Water-side berths, westward initial headings, explicit moorings, physical-hash mooring state | Real simulator changes, not just visual polish; change mission timing and need fresh evaluation |
| `world/endurance.py` | Removes the quay land-check exclusion | More honest land diagnostic; older and newer land counts are not directly equivalent |
| `web/src/viewer/`, `web/viewer.html`, Vite/package changes | Separate Three.js entry reading the shared `/truth` feed | No second simulation on the supported browser-viewer entry; frontend tests/build pass |
| `world/viewer.py`, `world/gazebo.py` | Asset server/compatibility entry plus retained legacy code | Active entry is shared-feed; legacy alternate implementation needs cleanup |
| Native scene/adapter files and tests | Optional Gazebo/proxy work | Separate experimental scope, not proof of real Gazebo/hardware acceptance |
| `deck/video/`, `brag-output*/` | Other local untracked work | Not part of the harbour repair; not silently included as a release deliverable |

## 2. Checks actually executed

| Check | Result | Limit |
|---|---|---|
| Working-tree full Python suite: `uv run pytest -q` | **354 passed**, 367.93 s | Passing tests do not cover the counterexamples below |
| Clean main Python suite | **330 passed, 1 skipped**, 358.66 s | The clean archive has no built `web/dist`; not a fresh frontend installation/cross-OS proof |
| Working-tree frontend unit suite | **76 passed** | Includes local viewer unit cases |
| Entire browser suite: `pnpm ... playwright test` | **16 passed**, about 2.5 min | Mix of controlled fixtures, real demo workflow and viewer checks; not 16 independent live-world scenarios |
| Fresh TypeScript generation into `/tmp/edth-contract-audit.ts` | **Diff found** | Existing generated `web/src/contract.ts` lacks `TaskView.options` |
| Same logical probes on main and branch | **Same inherited failures reproduced** | Synthetic/adversarial inputs exercise invariants missing from normal-path tests |
| One real 12 h seed-1 launch run in clean main | Completed | Single-seed diagnostic, not final batch acceptance |
| Local candidate's recorded 12 h seed-1 run | Completed | Same core settings, changed physical startup/mooring behaviour |
| Repository-wide Ruff | **12 errors** in existing `deck/video/` / `brag-output/work/` | Scoped world checks passed earlier; unrelated files were not fixed |

Probe sources and evidence:

- `runs/local/audit/logical-probes.py`, `main-probes.json`, `branch-probes.json`
- `runs/local/audit/ais-probe.py`, `main-ais.json`, `branch-ais.json`
- `runs/local/audit/eval-probes.json`, `incomplete-headline.json`
- `runs/local/audit/main-endurance-12h.{md,json}`
- `runs/local/harbour-endurance-12h.{md,json}`

Run the isolated logical probe from the repo root with
`uv run python -c "exec(open('runs/local/audit/logical-probes.py').read())"`.
It mutates temporary in-process objects, including the routing test graph, not production
files or the running server. The AIS probe uses an explicitly synthetic temporary CSV.

## 3. Confirmed high-priority defects inherited from main

### H1 — Coast routing can override the contact stand-off safety filter

**Code:** `agent/core.py:455–487`, particularly `target = self.water_step(target)` after
stand-off avoidance. **Plan:** automatic safety tier; standing orders 2/3, rules 15/16.

The contact filter first chooses a safe target. Coast routing then substitutes a waypoint
without rechecking contact clearance. In a probe using the real scene and the real
`seg:G:0` endpoint:

- Boat starts at `(-1971, -8069)`; goal is `(-5715, -5690)`.
- Known no-AIS contact is at `(-4578, -8501)`; no close approval exists.
- Final commanded waypoint becomes `(-3378, -8501)`.
- The commanded segment comes within **1,200 m**, inside the required **1,852 m** stand-off.

This reproduces in main and the candidate. It is a concrete semantic integration failure:
coast-safe and contact-safe filters are individually present but their composition is unsafe.

**Fix:** plan with both obstacle sets, or apply a final invariant check that rejects an unsafe
next segment rather than blindly running one filter after another. Include an explicit
return-safety policy for conflicts. **Regression:** real-scene coast + contact exclusion together,
not independent coast-only and contact-only tests. Owner A, with B geometry review.

### H2 — Closing an old auction round can give work to a returning/ineligible boat

**Code:** `agent/auction.py:55–84`, `agent/core.py:129–180`.

`on_slot()` closes the old round **before** checking `may_bid()`. `close_round()` checks task
openness but not the winner's current eligibility/energy/return state.

Reproduction uses a legitimate self-bid made by the real t=0 slot logic, not a fabricated
winning record: boat 2 bids on an open cable while charged, then its battery drops before
12 s. At 12 s `go_home()` releases its tasks, but round closure immediately awards it the
open cable. Result: **`returning=True`, mode RETURNING, still owns `seg:A:0`**. Its continuing
heartbeats can keep that unavailable task leased. The same sequence at the `off` cutoff
creates a repair claim when `may_bid()` is already false.

**Fix:** revalidate current winner eligibility before claiming; invalidate outstanding bids
on return/policy cutoff. **Regression:** low battery, role change, lost majority and policy-off
at round closure. Owner A. This protects both repair correctness and baseline F3.

### H3 — `/shore` can show AIS information that never arrived by radio

**Code:** `server/bridge.py:447–478` (`_ais_contacts`, `_shore`),
`world/sim.py:550–611` (`ais_contacts_view`). **Plan:** shore picture is delivered knowledge only.

The shore extras include AIS tracks if a physical boat is in reception range, using truth
positions, even if that boat has no radio path and boat-side AIS input is disabled.

Synthetic Class-B reproduction, run on both versions:

```
shore_direct_ais_in_range: false
physical_seen_by: [3]
boat_side_ais_enabled: false
boat_received_track: false
shore_received_obs: false
published_shore_contact: true
```

**Fix:** separate legitimate shore AIS reception from actual boat-delivered observations;
never use truth `seen_by` as proof of radio delivery. Explicitly disclose any independent shore
sensor source. **Regression:** isolated boat, out-of-shore-range track, and disabled boat AIS
must not populate `/shore`. Owners C + B/A interface coordination. This must not be solved by
letting agents import evaluator state.

### H4 — World reset undoes the evaluation warm-up's tide shift

**Code:** `eval/warm.py:94–106` vs `world/sim.py:121` (main line 116).

The evaluator assigns a shifted `world.current`, then calls `world.reset()`. Reset restores
`_base_current`, losing the shift. With the default 3 h warm-up:

- Expected world-time flip: **19,800 s**, i.e. mission **9,000 s**.
- Actual world-time flip: **9,000 s**, i.e. mission **−1,800 s**.

Modes can still have identical warm hashes and pass fairness while all simulate the wrong
mission-relative tide. History confirms the warm-up's direct assignment predates the newer
reset-to-base-current implementation (`33706f7`): another genuine integration regression.

**Fix:** configure/reset the base current consistently, rather than modifying a resettable
transient attribute. **Regression:** assert current direction at mission 0, 8,999 s and 9,000 s
with nonzero warm-up, plus deterministic reset. Owners D + B. Recompute affected results.

### H5 — The headline gate can approve an incomplete, non-comparative experiment

**Code:** `eval/report.py:123–159` and `eval/run_batch.py`.

Actually ran five `elysa` cases, seeds 1–5, `warm_s=6000`, mission horizon **60 s**. Result:
`headline_ok=True`, no failed fairness checks, even though:

- No `off`/`static` comparison ran.
- The failure at mission 7,200 s was never reached.
- All `ages_hash_T1` values were **None**.

Checks are skipped when modes are absent, and missing checkpoint values are not an explicit
failure. Counting five seeds plus varied outcomes is not evidence of failure-response benefit.

**Fix:** distinguish diagnostic output from accepted comparative batches. Require intended
modes, matching minimum seed sets, nonmissing T−1 checkpoints, and completion to the scoring
point before comparative headline approval. **Regression:** five short runs, missing modes,
missing per-mode seeds, and None checkpoints must remain PRELIMINARY. Owner D.

### H6 — Contact dwell means first-ever track age, not qualifying slow dwell

**Code:** `agent/contact.py:58, 137–146`. **Plan:** slow/no-AIS/near-cable for 180 s.

`first` is set for every observation, including fast/nonqualifying observations. The task's
dwell test later subtracts that first-ever time. A track first seen fast at t=0 and first
seen slow at t=180 s immediately gets a contact task and `dwell=True`: it has **zero observed
slow dwell**. Gaps/changes in qualifying behaviour do not reset the clock.

**Fix:** maintain a separate qualifying-dwell clock, with explicit reset/gap rules; keep first
sighting separately for history. **Regression:** fast→slow, away→near cable, AIS→no-AIS, and
observation gaps. Owner A. Do not change alert words to hide this false evidence.

## 4. Additional confirmed defects / integration gaps

| ID / priority | Code | Reproduced or verified result | Required repair / owner |
|---|---|---|---|
| M1 / P2 — stale decision lifecycle | `agent/shore.py:155–179` | Release `contact:gone`, advance to t=120 s with no fresh observation: keep/close cards remain `pending`. `over` ignores released/stale tasks, so alerts can escalate for work no longer active. | Withdraw/revise stale or released proposals; revalidate at dispatch. A + C |
| M2 / P2 — cancelled swap still advertised | `server/bridge.py:366–375`, `world/sim.py:512–532`, local `web/src/viewer/lifecycle.ts:13–24` | Inject low battery at the dock, then switch boat off. Physical `world.swapping={}` but feed still says `{'4': 601}`. The local viewer's UNAVAILABLE guard does not distinguish this from a real swap. | Track cancellation/active dock state rather than infer only from historical start/completion events; test in both UIs. C + B |
| M3 / P2 — return-by models disagree | `agent/shore.py:316–325` vs `agent/core.py:332–365`, `agent/auction.py:145–242` | At `(797,8644)`, no current, reported return-by is **306 s later** than the agent's water-route rule. Shore uses straight distance. Bidding reach/cycle/peer-fit also retain straight-line assumptions: that is a separate under-budgeting risk, not proof of observed depletion. | Send the agent's own model estimate/time in its report, not truth; investigate eligibility against actual route/leg direction and reserve rules. A + C |
| M4 / P2 — backend accepts Stop on a cable | `agent/shore.py:241–269`, `server/bridge.py:242–250` | `{'cmd':'stop','id':'seg:G:0'}` returns `ok=True` and creates an absorbing VETOED cable record. Stop was designed for contact decisions, not arbitrary mission tasks. | Validate an existing eligible decision, contact task, state and allowed action server-side, not only in the UI. A + C |
| M5 / P2 — workload metric counts cards as actions | `eval/metrics.py:257` | Open two automatically generated contact cards; send zero operator commands. `operator_actions` reports **2**. | Count actual accepted operator actions separately from proposals/messages. D + A/C |
| M6 / P2 — generated TS contract drift | `web/src/contract.ts:224`, `contract/schema.json`, `contract/views.py:60` | Fresh generation adds `TaskView.options`; checked-in type lacks it, and live panel code does not consume it. Python schema freshness test does not check TS freshness. | Regenerate TS from the existing frozen schema (no schema change needed); wire accepted feature UI and add freshness check. C |
| M7 / P2 — fail-open navigation fallback | `agent/water.py:148–149, 191–195` | A blocked crossing with no connected waypoints returns the same blocked direct route. Confirmed with a disconnected synthetic graph; not a claim that the stock 12 h route hit this fallback. | Explicit no-route outcome and safe hold/report policy; assert every returned segment is admissible. A |
| M8 / P2 — local physical inputs missing from provenance | `server/runlog.py:29–37`, local `world/harbour.json` | Main and candidate produce the **same config hash** although berths/moorings and trajectory differ. New layout is outside the hash manifest; compiled viewer geometry also has no scene layout revision check. | Include physical layout/coast inputs and model revision; expose layout identity in scene extras for the viewer. C + B |
| M9 / P2 — feed-loss bound exceeds plan | local `web/src/viewer/feed.ts:61,74`; `web/src/store.ts` | Viewer waits >2,200 ms then polls every 250 ms; cannot meet N5's within-2-s stalled-feed bound. Main store also polls its 2,000 ms threshold and needs a strict-bound test. | Shared deadline policy with margin for polling; test an open stalled socket, not only graceful closure. C |

Other lower-priority cleanup: `StatusDetails` calls claimed segments “Cables watched” based on
ownership alone (`web/src/ui/LiveStatus.tsx:34–42`); prefer “assigned” so it cannot contradict the
sensor-visit coverage headline. `world/gazebo.py:293–797` retains an obsolete alternate viewer
with another projection and a separate background simulator. The supported `--serve` entry
uses `world.viewer`, so this is dead/explicit-legacy scope, not evidence of two active simulations
in the current browser viewer. Remove/isolate it before packaging rather than present it as
another equivalent implementation.

## 5. Measured main vs candidate behaviour: not a cosmetic-only change

Same real-agent seed-1 12 h shore-launch diagnostic:

| Metric | Clean main | Local candidate |
|---|---:|---:|
| Samples visited at least once | 241/241 | 241/241 |
| Minimum battery at sea | 10.7% | 11.2% |
| Battery swaps | 5 | 5 |
| Longest gap / final age | 8 h 47 min | 8 h 47 min |
| Samples exceeding the revisit target in that metric | **196** | **228** |
| Scripted dark contact seen / held | No / no | No / no |
| On-land diagnostic | 0 sampled centres **outside quay only** | 0 sampled centres **including quay** |

The candidate fixes real startup defects, but it is **not demonstrated to preserve or improve
mission performance**. Changed berths/moorings change travel/role timing; in this seed the
revisit measure worsens. This does not prove a general regression over seeds; it does require
fresh paired evaluation, not reuse of old headline figures. Do not compare the two land zeros
as equal tests: main excludes the area where its boats spawn on land.

The full Python story tests pass in a deliberately selected warmed seed (`tests/story/test_story.py`,
seed 11, 600 s warm-up), and the real preset demo's approval/restoration workflow passes the
browser test. That demonstrates the feature path exists. It does **not** show that the default
cold shore-launch run delivers the same story or maintains the target.

## 6. Main-product plan coverage (features 1–25)

“Exercised” below means existing tests/code paths pass, not universal correctness or field
certification. Known defects take precedence over green tests.

| Feature(s) | Audit assessment |
|---|---|
| 1 — real Great Belt scene | Implemented/exercised; approximate public geometry, not surveyed navigation data |
| 2 — five boats on 2+2+1 roles | Placed/demo/eval presets retain initial roles; default launch deliberately removes owners and auctions them. Plan needs explicit preset/scope update; do not describe both as the same initial condition |
| 3 — revisit age | Per-sample truth and delivered shore sampling implemented/tested; actual target still missed. Ownership is not coverage |
| 4 — seeded reset/replay | Existing deterministic/reset/replay tests pass; H4 changes scenario meaning despite repeatability; M8 leaves new inputs out of provenance |
| 5 — decentralised auction | Implemented/tested but H2 violates close-time eligibility; priority-first task order is intentional, not a bug that the globally lowest score is not always chosen |
| 6 — low battery, release, repair | Normal-path return/swap/rejoin tests pass; H2 can retain work during return |
| 7 — range-limited radio/peer hops | Physical radio/protocol tests pass; H3 breaks delivered-information semantics in AIS shore extras |
| 8 — relay takeover | Existing relay/deputy tests pass; not a guarantee of a replacement in every geometry/radio range |
| 9 — split/rejoin | Merge/quorum/rejoin tests pass; H2 must also respect eligibility after changing network conditions |
| 10 — dark contact/scout/watcher | Selected story and demo pass; H1/H6/M1 are correctness defects, and default seed-1 launch misses the contact |
| 11 — remaining gap visible | Per-sample headline is conservative/tested; “Cables watched” ownership wording should be corrected |
| 12 — three-mode baseline/metrics | Runner exists and fairness tests pass; H4/H5/M5 prevent full acceptance of current evaluation semantics |
| 13 — failure injection | Normal boat/link/off/restore paths pass, including real browser workflow; state/cancellation metadata needs M2 repair |
| 14 — operator policy | UI review/undo/read-only paths and real approval delivery pass; H1/M1/M4 still violate policy or proposal lifecycle invariants |
| 15 — current-aware return | Agent uses water route/current; M3 shore/eligibility estimates are inconsistent, H4 alters evaluated tide timing |
| 16 — SENTINEL drift/correct | Implemented/tested; new mooring is a separate dock state, not an assertion that all SENTINEL boats should stop drifting |
| 17 — offline chart | Local assets/build/browser tests pass; not a fresh physical Wi-Fi-off/two-laptop certification |
| 18 — fleet role/mode/battery/age | Implemented/exercised; return-by estimate needs M3 repair |
| 19 — contact tracks/source | Camera/received tracks exist; H3 AIS shore path breaks provenance and must be fixed |
| 20 — stale data honesty | Existing stale/freeze tests pass; AIS exception H3 and strict watchdog deadline M9 remain |
| 21 — comms overlay | Directed-link/peer display tests pass; do not equate truth reception range with delivered shore knowledge |
| 22 — decision cards/ghost routes | UI and command delivery exercised; M1/M4 lifecycle/validation and H1 path-safety composition remain |
| 23 — three-level alerts | Dedup/ack/escalation tests pass; stale proposals can create false alarms through M1 |
| 24 — coverage overlay/headline | Implemented/exercised; does not establish target attainment or validate old benchmark figures |
| 25 — warp/log/feed lost/exercise | Implemented/exercised; M2/M9 and exercise-state reconciliation need follow-up; live-run UX branch is not yet main |

Secondary scope must stay separate: AIS replay exists, but boat-side use is optional/gated and
triage is not implemented merely because AIS ships can be drawn. Deputy/evidence/report paths
exist and have tests, but are not a reason to call every feature 26+ delivered. DORMANT/tide-wait,
real forecast integration, a 24/7 rotation scheduler and calibrated native-vessel dynamics are
not certified here. Decorative daylight/waves are not sensor/weather physics.

## 7. Why passing tests did not catch this

- Individual safety filters were tested independently, not as a composition.
- Auction tests cover dead winners and incoming live claims, not an eligible bidder becoming
  ineligible exactly at closure.
- Fairness tests compare modes to each other, not their timeline to the intended tide time.
- Headline tests reject one seed but do not reject a varied five-seed incomplete experiment.
- Dwell tests start with already-qualifying tracks rather than transitions into eligibility.
- Console fixture tests validate UI behaviour on supplied frames; they cannot establish that
  backend frame provenance is correct. The isolated-AIS probe tests that missing boundary.
- Harbour tests cover representative launch/return paths, not global collision avoidance,
  all seeds, berth reservation or mission-level coverage performance.

## 8. Fix order / acceptance gates

1. **A+B:** close H1/H2 first: final combined navigation invariants and close-time auction
   eligibility. Add regression cases before changing behaviour.
2. **C with A/B:** close H3, M1/M2/M4: delivered AIS only, valid proposal/action transitions,
   active/cancelled swap state. Test through actual bridge snapshots and both UIs.
3. **A:** close H6 and align agent/shore/bid energy estimates (M3). Use reported model estimates,
   never truth to “improve” the operator's picture.
4. **D+B:** fix H4/H5/M5, then rerun matching seeds/modes/speeds with the correct warm timeline.
   Historical `eval/results.md` belongs to its stated old revision; do not relabel it current.
5. **C+B:** fix type generation, layout/input provenance, no-route handling and watchdog deadlines.
   Separate the selected demonstration preset from default operational launch acceptance.
6. Run the full Python + frontend + browser suites **and** the new failing-invariant probes;
   a green old suite alone is insufficient. Review mission target/contact results explicitly.
7. Stage/review the intended new files, exclude CSVs/runs/video scratch output, fix unrelated
   lint in the correct owners' scope, then create the release PR. The current branch has no
   committed implementation delta, so it is not yet reproducible from GitHub alone.

No claim is made that every possible bug is enumerated. The audit establishes concrete blockers,
current evidence and a repair order; it does not certify hardware safety, Windows/mobile GPU
behaviour, physical offline operation or final presentation/video delivery.
