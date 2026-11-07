# Measured results on the team world

**Status: accepted runs on `main` at `86806cb` (merge of #70), 2026-11-07.** `run_batch` exits 0 on every batch below: fairness F1–F5 and the console gap check pass, no PRELIMINARY. Re-run on the frozen `final` tag on Sunday morning and replace the revision. Every number is **truth** (evaluator), not shore-reported.

## Setup

- Great Belt scene: 7 cable segments, 23.6 km, 241 samples (`tools.scene_check`). Revisit target 12,000 s, scored at mission time 14,000 s.
- 3 h warm-up with the battery held full and bidding off. Each sweeper starts at a seed-drawn place on its tour loop. Warm hash identical in all modes (F1).
- Failure T = 7,200 s (boat 1 returns), then a one-way link cut, a dark contact at 7,320 s that departs at 9,200 s, link back at 10,800 s.
- Modes differ in `policy` only (F4). `static`: fixed stations forever, no bids, no shadowing. `off`: bidding stops at T. `elysa`: repair stays on, with #55 (oldest segment first after a takeover).
- Private AIS clip present on the evaluator only. Boats never receive AIS.

## Headline: 30 paired seeds, same warm state per seed

| Truth | off | elysa | Paired, seed by seed |
|---|---|---|---|
| Cable km overdue at end | 6.7 (2.1 to 11.8) | **1.4** (0.0 to 5.6) | elysa better 30, equal 0, worse 0. Median gain 4.8 km |
| Mean km overdue, T to end | 2.3 (0.5 to 4.6) | **0.2** (0.0 to 2.5) | elysa better 30, equal 0, worse 0. Median gain 1.5 km |
| Worst sample age at end (s) | 16,558 (14,375 to 17,871) | **12,798** (9,499 to 17,860) | elysa better 24, equal 6, worse 0 |
| Real cargo and tanker crossings in view after T (of 9) | **9** (9 to 9) | 5 (3 to 9) | elysa worse 20, equal 10, better 0 |
| T to all segments owned by a live boat (s) | not reached | 60 (60 to 60) | |
| Segments with no live owner at end | 4 (4 to 7) | 0 | |

```bash
uv run python -m eval.run_batch --modes off,elysa --seeds 1,...,30 --jobs 8 --out runs/paired30
```

**The trade-off (#68), stated plainly.** After boat 1 goes home, repair sends boat 4 off its south lane picket to the cables, oldest segment first. The cables stay fresh: 1.4 km overdue instead of 6.7 km, better in every one of 30 seeds. The south picket is empty in both modes, but `off` keeps its 9 of 9 crossings in view because boat 4 never moves and the four crossings near picket S happen to be within camera range. With repair, boat 4 is on the far cable when those ships cross, so 20 of 30 seeds drop to 5 of 9. Decision: keep #55 and show both numbers on the slide. "Crossings in view" is the evaluator's reading of the private AIS clip; it says a live boat was within camera range, nothing more. The boats never see AIS.

## Five seeds, all three modes

Median (min to max). The batch the build plan names.

| Truth | static | off | elysa |
|---|---|---|---|
| Cable km overdue at end | 15.2 (14.6 to 15.2) | 3.3 (2.3 to 7.5) | 0.0 (0.0 to 1.7) |
| Cable km never visited | 0.0 (0.0 to 0.5) | 0.0 | 0.0 |
| Mean km overdue, T to end | 10.7 (10.2 to 12.2) | 1.0 (0.5 to 2.8) | 0.0 (0.0 to 0.4) |
| Worst sample age at end (s) | 24,328 (22,670 to 24,794) | 16,249 (14,703 to 17,027) | 11,106 (9,579 to 15,317) |
| Real cargo and tanker crossings in view after T | 9 of 9 | 9 of 9 | 5 (5 to 9) of 9 |
| T to all segments owned by a live boat (s) | not reached | not reached | 60 (60 to 60) |
| Segments with no live owner at end | 4 | 4 (4 to 7) | 0 |
| Claims after T | 0 | 0 | 4 (4 to 9) |
| Console shows a segment fresher than truth, up to (s) | 1 | 2 | 2 |

Paired on these 5 seeds: elysa better 5 of 5 on km overdue (median gain 3.3 km). **Quote the 30-seed table, not this one, for off against elysa.**

```bash
uv run python -m eval.run_batch --out runs/main
```

## Sensitivities, five seeds

| Truth | static | off | elysa | Paired, elysa vs off |
|---|---|---|---|---|
| km overdue, 3.0 m/s | 15.2 (15.1 to 15.2) | 4.0 (2.6 to 7.5) | 0.1 (0.0 to 3.0) | better 5 of 5, gain 3.8 km |
| crossings in view, 3.0 m/s | 9 | 9 | 7 (5 to 7) | worse 5 of 5 |
| km overdue, 4 km boat radio | 15.2 (14.6 to 15.2) | 4.9 (2.8 to 12.3) | 2.6 (0.0 to 7.1) | better 4, equal 1, gain 2.8 km |
| crossings in view, 4 km boat radio | 9 | 8 (4 to 9) | 3 (0 to 6) | worse 5 of 5 |
| Watcher in view of C-07, 4 km radio | not reached | not reached | **not reached** | |

**Radio range limits, disclosed.** At 4 km boat radio the gain shrinks (2.6 vs 4.9 km) and the contact is never handed to a watcher in any of 5 seeds: the claim cannot be heard by the boats that could take it. Crossings in view also fall to 3 of 9. With 4 km radios the scout at picket N has no shore path at all (`tools.scene_check`: boat 3 unreachable), so the relay matters more and reassignment is slower (10 claims after T, up to 17). The console showed a segment up to 37 s fresher than truth in that batch, inside the 60 s heartbeat slack.

```bash
uv run python -m eval.run_batch --speed 3000 --out runs/speed3000
uv run python -m eval.run_batch --radio 4000 --out runs/radio4000
```

## The contact

Detected in 10 of 30 seeds at 2.3 m/s (same seeds in `off` and `elysa`: detection depends only on where the sweeper is in its loop, which the seed fixes before T). Handed to a watcher in 8 of 30 `elysa` seeds, 192 to 1,809 s after it appeared; never in `off` or `static`. At 3.0 m/s: detected 4 of 5, watched 4 of 5. `static` boats at the picket see C-07 in every seed by geometry alone (it sits near picket N) and never move.

## Honest readings

**What repair did.** After boat 1 goes home, every segment has a live owner again 60 s after T in all 30 seeds. Without repair, 4 or more segments stay unowned. Overdue cable at the end drops in 30 of 30 seeds and never rises.

**What repair did not do.** It does not keep the south lane picket. It does not detect the contact more often. At 4 km radio it does not get a watcher onto the contact at all.

**Test evidence for this revision.** `uv run pytest -q` on Windows 11, Python 3.12: 271 passed, 1 skipped, 1 failed. The failure is `tests/server/test_evidence.py::test_private_key_is_owner_only`, a POSIX file-mode check that cannot pass on NTFS; it is C's and passes on Linux. CI is blocked by org billing (see `deck/RELEASE.md`), so this is local evidence.
