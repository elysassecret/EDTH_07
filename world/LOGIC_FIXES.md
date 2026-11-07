# Logic-repair progress

Branch: `b/viewer-launch-swap`, main baseline `0435058`.
Audit: [LOGIC_AUDIT.md](LOGIC_AUDIT.md). This is not a completed repair/release.

## Started

1. Added `tests/world/test_logic_regressions.py`: ten cross-layer invariant cases for the
   confirmed safety-filter, return/off auction closure, shore AIS provenance, shifted tide,
   qualifying dwell, incomplete headline, stale proposal and cancelled-swap failures.
2. Verified the red baseline with `--runxfail`: nonzero exit as expected. The cases are currently
   **strict xfails**, not passing behaviour. Unexpected passes fail the suite, requiring the
   marker to be removed as each repair lands. Red-baseline output is kept in
   `runs/local/audit/regression-red-baseline.txt`.
3. Fixed the approved viewer portion of M9: a shared 1,500 ms stale deadline and 200 ms watchdog
   poll leave headroom inside the plan's two-second bound. Command dispatch uses the same
   expiry rule; an observation at performance-clock zero is distinct from no observation.
4. Tightened the open-socket stalled-feed browser test to require the banner within two seconds.
   Added deadline boundary/headroom/clock-zero unit cases. The main dashboard's separate
   watchdog is unchanged, so M9 is only partially repaired.

## Latest executed checks

- New test module: Ruff passes.
- World regression/harbour/smoke selection: **11 passed, 10 xfailed**.
- Frontend unit suite: **79 passed**.
- Strict TypeScript + production build: passed.
- Viewer browser suite: **3 passed**, including the tightened feed-loss deadline check.
- `git diff --check`: passed.

These checks do not establish a hard deadline while the browser's main thread is blocked or
on untested phone hardware. No live simulation reset, private data change, contract edit,
commit or PR was performed in this repair step.

## Next, subject to folder-owner permission

Permission was requested before editing A-owned `agent/`, C-owned `server/`, D-owned `eval/`
and their tests. Those implementations are unchanged in this step. The frozen `contract/`
remains out of scope without its required approval.

Repair order after approval: H1/H2 safety and allocation invariants; H3 delivered-data-only
shore picture; H6/M1/M2/M4 contact and dock/proposal lifecycle; H4/H5/M5 evaluation semantics;
then return estimates, provenance, generated types and full dashboard watchdog integration.
Remove the corresponding strict xfail marker only when the invariant passes, then rerun
full suites and matched seeded evaluations. Do not count the known failures as acceptance.
