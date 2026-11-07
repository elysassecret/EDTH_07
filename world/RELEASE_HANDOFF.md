# B release-candidate handoff — #72

## Scope and tested revision

Checked on 7 November 2026: **`86806cb9904584be56e18f1b2596a238f55374b2`**,
main after #69 and #70. This is integration evidence, **not D's accepted benchmark,
feature sign-off, full video, cross-platform proof or two-laptop certification**.
PR #76 is still a separate UI candidate and is not included in this revision.

Machine used: **Mac14,9, macOS 26.6 arm64**, Python **3.12.13**, uv **0.13.5**,
Node **26.6.0**, pnpm **12.18.0**. These identify this local check, not a new supported
Node/Python range or a claim that another machine has been tested.

No private AIS CSV is present in this checkout. No production physics, agent, contract,
server, evaluator or web source was changed for this handoff.

## Reproducible integration evidence

From that revision, after dependency setup:

```bash
uv sync --locked
uv run ruff check .
uv run pytest -q --junitxml=/tmp/edth-72-tests.xml
```

Results: lint passed; **273 existing Python tests passed**, including slow story and
fairness cases. The new `tests/world/test_contact_handoff.py` adds **three separately
run passing cases**; it was added after the baseline run collected its tests:

```bash
uv run pytest -q tests/world/test_contact_handoff.py
```

| Requirement / handoff | Existing executable evidence |
|---|---|
| Millimetre motion, bounded charge, deterministic tick/reset | `tests/world/test_sim.py` |
| Cruise vs hotel load, fractional drain, real-agent return protections | `tests/world/test_energy.py`, `tests/world/test_current.py` |
| Current reversal boundary, measured-current return rule, SENTINEL correction | `tests/world/test_current.py` |
| Directed loss, delayed bytes, peer fallback, isolation/rejoin, stale reports | `tests/world/test_agent_integration.py`, `tests/world/test_link_identity.py`, radio cases in `test_sim.py` |
| Seeded placement, no invented history, reset and hash-seed independence | `tests/world/test_phase.py` |
| Off/restore: same boat and node, no teleport/recharge; depleted stays depleted | `tests/world/test_restore.py` |
| Combined off/restore, link cut/restore, battery injection and reset replay | `tests/world/test_event_replay.py` |
| Actual bridge off/restore, cleared alert, delivered report and log replay (#70) | `tests/server/test_bridge.py::test_boat_restore_brings_the_same_boat_back_and_replays` |
| Logged command replay and changed-command detection | `tests/server/test_replay.py` |
| Demo contact/card, repair, relay loss/rejoin beats on the real scene | `tests/server/test_demo.py::test_demo_beats_still_happen`, `tests/story/test_story.py` |
| Approve / decline / stop actually reach the real-world watcher over radio | New `tests/world/test_contact_handoff.py` |
| Missing scorecard is supported; available scorecard is truth-only | `tests/server/test_bridge.py::test_scorecard_is_read_from_eval_output_on_truth_only` |

The new contact tests start at the real seed-1 demo's 8060 s checkpoint, require a
**delivered shore contact and pending cards**, and test each answer independently.
Shore acceptance must not mutate the watcher in that tick. The tests then require a
reported delivery and the corresponding watcher state, with no battery increase.
Declining the closer look leaves the standing watch; Stop vetoes it and expires the
close proposal. Their 180 s test budget is not a deployment-latency promise. Test-only
deep copies are not a new supported checkpoint/warm-start API. Receipt does not prove
that a 500 m look or an observation has completed.

No B-owned implementation defect was exposed by these checks. Passing them is not
permission to replace D's baseline acceptance with integration figures.

## Clean cached checkout / local browser check

A detached clean worktree of the tested revision was used, separate from the working
console and any untracked local notes. Equivalent commands (substitute temporary paths):

```bash
git worktree add --detach /tmp/edth-72-rc 86806cb9904584be56e18f1b2596a238f55374b2
cd /tmp/edth-72-rc
UV_PROJECT_ENVIRONMENT=/tmp/edth-72-python-clean uv sync --locked --offline
UV_PROJECT_ENVIRONMENT=/tmp/edth-72-python-clean uv run --offline pytest -q tests/smoke
npx --offline pnpm --dir web install --frozen-lockfile --offline
npx --offline pnpm --dir web build
npx --offline pnpm --dir web test
```

- Fresh Python environment from this laptop's cache: passed; **3 smoke tests passed**.
- Clean frontend install from cache: passed, no package downloads; production build passed.
- **C-owned blocker:** the final `web test` command fails on this revision. Vitest
  discovers `template/tests/console.spec.ts`, whose separate Playwright runner is not a
  root dependency. It reports **1 failed suite, 2 passed suites / 13 passed tests**.
  Installing the template runner is not the solution; restrict live Vitest discovery.
  Reported on [#73](https://github.com/elysassecret/EDTH_07/issues/73#issuecomment-6705840712).
  The scoped config in #76 addresses discovery, but that PR also needs reconciliation
  with #70's restore button and the recording flow before acceptance.

The cached check requires already cached tools/packages. It is not evidence that a fresh
laptop can download dependencies without internet. Prepare both machines online first.

The built **real** `--demo --no-log` server was then run from that clean worktree on
127.0.0.1:18872. Headless Chromium at 1280×720 blocked all non-local HTTP requests:

- Paused scenario clock **12:10:00Z**, local map canvas, and actual Run/Pause worked.
- `?operator` exposed only `/shore`; no truth/evaluator connection was opened.
- Switch-back-on control was enabled; absent satellite control was disabled.
- Stopping that test server produced FEED LOST; restarting it resumed the paused
  picture without reloading the page.
- No external HTTP requests or page exceptions were observed.

This was **one laptop with browser interception, not physical Wi-Fi-off**. No full
console cold-start, N5 timing bound, frame-rate, video, or second-machine certification
is claimed. Local inspection artifacts (not release deliverables):
`/tmp/edth-72-browser.cjs`, `/tmp/edth-72-browser-result.json`,
`/tmp/edth-72-rc-console.png`, `/tmp/edth-72-tests.xml` and `/tmp/edth-72-tests.log`.

## D handoff: scene and physical inputs (#19 / #74)

Reproduce geometry directly from `world.routes.load_scene` and `LineString(task.pts)`;
never hard-code six segments or weight the last interval as a full 100 m.

| Cable task | Rounded-polyline length (m, rounded here) | Samples |
|---|---:|---:|
| `seg:G:0` | 3426.579 | 35 |
| `seg:G:1` | 3425.799 | 35 |
| `seg:G:2` | 3426.798 | 35 |
| `seg:H:0` | 3340.385 | 34 |
| `seg:H:1` | 3340.385 | 34 |
| `seg:H:2` | 3341.010 | 34 |
| `seg:M:0` | 3302.633 | 34 |

Total: **23603.588758560138 m**, **241 samples**, all seven cable tasks below the
configured 5000 m maximum. These are public approximate scene geometries, not surveyed
navigation/land-clearance guarantees. Offsets are 0, 100, … with the endpoint excluded;
weight each interval by `min(100, length - offset)` using the unrounded length.

Chosen model inputs, not hull or forecast measurements:

- Speed 2.3 m/s, sensitivity 3.0; cruise-equivalent endurance 25200 s; reserve 1800 s.
- Verification radius 500 m; no-AIS stand-off 1852 m, authorized floor 500 m.
- Uniform current 0.5 m/s **toward** 345°, reversed once at sim 9000 s; hotel/cruise
  load ratio 100/1000 and return factor 1.2. Disabled boats do not drain in this model.
- Boat radio 8000 m (sensitivity 4000), shore 14000 m; delay 0.25–1.0 s, loss 0.05,
  max hops 4. Counter-keyed loss/delay is not by itself final cross-mode fairness proof.
- Lane half-width 750 m is a chosen constant band. R1–R3 acceptance belongs to D;
  absent boat-visible AIS cannot be reported as an actual AIS-reception R3 pass.

Input fingerprint (`world.check.config_hash`, sorted names + NUL + bytes + NUL over
its `CONFIG_FILES`, not a code/replay hash):

```text
config_sha256  5e40fd4e386aa4475b4f7939b016c5b5ae4101843a16c06d2407ea218e4cd4d3
uv.lock        dea05d888178102c1590b9f5fe326ed172a544a385a52fb740f4cb87ae14bca9
server/demo.toml a4a1b08191a31d4c09c954f62d6ddd106af13b2a068bf4df7cdf9a35c92187a7
```

```bash
uv run python -c 'from pathlib import Path; from world.check import config_hash; print(config_hash(Path(".")))'
```

### Cold placement versus D's warm-up

- `World(..., vary_start_phase=True)` is cold deterministic spatial placement. Seed 1
  retains the reference demo. Batteries start full; visit history starts unknown.
- D's current `eval.warm.build_world` / `warm_up` owns the 10800 s warm-up. It runs the
  off policy with bidding disabled, places followers using seeded phases, maintains
  full charge during warm-up, and shifts the tape, tide and repair cut-off together.
  Those are explicit experiment choices, not a field-recorded past or World default.
- `eval.warm.place_boats` overrides positions/follower indices after World's initial
  placement. World's `initial_phase` describes B's startup placement; **do not use it
  as a record of D's overwritten or warmed positions**. Record D's actual phases and
  the resulting warm state. If replacing B placement, choose the phase-control flag
  explicitly rather than assuming two independent phase algorithms are equivalent.
- `sample_visit_ms` aligns with `scene.samples`; None means never visited. Truth segment
  ages are worst-sample **ms**, nullable. Shore picture uses delivered data in **s**;
  never fill missing shore ages/contacts/positions from truth. Shore age equal to elapsed
  time is ambiguous missing history, not proof of a visit at mission start.
- `state_hash()` covers physical/queue state, **not complete agent replay**. Use the
  integrated replay checks for protocol/shore evidence. F1–F4 regression passes do not
  sign off D's five-seed, both-speed, median/range results or static definition.

## Human gates / coordination record

| Item | Status and next owner |
|---|---|
| B world integration, restoration and actual contact answers | Local evidence above; no benchmark claim |
| C clean web test command | Fails on tested main; C action linked above |
| Actual two-laptop offline rehearsal | **NOT RUN**. C/D asked to confirm machines/OS and availability on [#72](https://github.com/elysassecret/EDTH_07/issues/72#issuecomment-6705827977). Use `server/DEMO.md` rehearsal steps on both clean clones; record revision, OS, Python/Node/pnpm, startup timing, feed loss/reconnect and missing assets. B's machine details above are local only. |
| Offline vectors | Land and infrastructure GeoJSON present; clean browser map rendered |
| Satellite | `web/public/geo/s2_box.png` and `s2_box.json` absent; keep optional toggle disabled; D #9 |
| Private AIS handoff | No CSV locally. D asked to agree transfer privately; do not attach CSV/private URLs to public issues or commits. Completion is not claimed. Core runs without it. |
| Full core video | No accepted complete video link supplied to this handoff; C #73 / D #74 must provide revision and signed-out-accessible recording |
| #52 / triage gate | **BLOCKED** pending D's features 1–25 acceptance on selected main **and** full video evidence. No replay, range filtering or triage started. |
| Cross-OS determinism / final evaluation | D/team acceptance still required; one-Mac tests cannot certify it |

Keep #72 open for the remaining human handoffs. Gazebo, independent runtimes, advanced
energy management and calibrated hull physics remain roadmap, not new release scope.
