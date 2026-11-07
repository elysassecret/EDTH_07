# Measured results on the team world

**Status: preliminary, not for slides yet.** The console gap check fails (#29), so `run_batch` prints PRELIMINARY and exits 1. Re-run on the frozen `final` tag on Sunday morning and replace these numbers. Every number below is **truth** (evaluator), not shore-reported. Measured on `d/eval-warm`, world and agents as of `main` at `d5040a2`.

## Setup

- Great Belt scene: 7 cable segments, 23.6 km, 241 samples. Revisit target 12,000 s, scored at mission time 14,000 s.
- 3 h warm-up with the battery held full and bidding off. Each sweeper starts at a seed-drawn place on its tour loop. Warm hash identical in all modes.
- Failure T = 7,200 s (boat 1 returns), then a one-way link cut, a dark contact at 7,320 s that departs at 9,200 s, link back at 10,800 s.
- Modes differ in `policy` only. `static`: no sweeping, no bids. `off`: bidding stops at T. `elysa`: repair stays on.

## Headline: 30 paired seeds, same warm state per seed

| Truth | off | elysa | Paired, seed by seed |
|---|---|---|---|
| Cable km overdue at end | 6.5 (2.1 to 10.5) | 3.3 (0.0 to 6.7) | elysa better 22, equal 8, worse 0. Median gain 2.6 km |
| Mean km overdue, T to end | 2.3 (0.5 to 4.4) | 1.9 (0.0 to 3.2) | elysa better 21, equal 9, worse 0. Median gain 0.3 km |
| Worst sample age at end (s) | 16,558 (14,375 to 17,870) | 16,558 (10,335 to 17,870) | elysa better 6, equal 24, worse 0 |

```bash
uv run python -m eval.run_batch --modes off,elysa --seeds 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30 --out runs/paired30
```

## Five seeds, all three modes

Median (min to max). The batch the build plan names.

| Truth | static | off | elysa |
|---|---|---|---|
| Cable km overdue at end | 15.2 (14.6 to 15.2) | 3.3 (2.3 to 7.5) | 3.3 (0.0 to 6.4) |
| Cable km never visited | 0.0 (0.0 to 0.5) | 0.0 | 0.0 |
| Mean km overdue, T to end | 10.7 (10.2 to 12.2) | 1.0 (0.5 to 2.8) | 0.9 (0.0 to 2.7) |
| Worst sample age at end (s) | 24,329 (22,670 to 24,794) | 16,251 (14,703 to 17,025) | 14,703 (11,108 to 17,025) |
| Real cargo and tanker crossings in view after T | 9 of 9 | 9 of 9 | 9 of 9 |
| T to all segments owned by a live boat (s) | not reached | not reached | 60 (60 to 60) |
| Segments with no live owner at end | 4 | 4 (4 to 7) | 0 |
| Claims after T | 0 | 0 | 4 (4 to 9) |

Five seeds show a tie at the median that 30 paired seeds do not. **Quote the 30-seed comparison, not this table, for off against elysa.**

```bash
uv run python -m eval.run_batch --out runs/main
```

## Sensitivities, five seeds

| Truth | static | off | elysa |
|---|---|---|---|
| km overdue, 3.0 m/s | 15.2 (15.1 to 15.2) | 4.1 (2.6 to 6.8) | 0.4 (0.0 to 6.6) |
| km overdue, 4 km boat radio | 15.2 (14.6 to 15.2) | 7.4 (0.0 to 14.8) | 3.2 (0.0 to 9.1) |

```bash
uv run python -m eval.run_batch --speed 3000 --out runs/speed3000
uv run python -m eval.run_batch --radio 4000 --out runs/radio4000
```

## Honest readings

**What repair did.** After boat 1 goes home, every segment has a live owner again 60 s after T in all 30 seeds. Without repair, 4 or more segments stay unowned. Overdue cable at the end drops in 22 of 30 seeds and never rises.

**What repair did not do.**
- The worst sample age matches `off` in 24 of 30 seeds: repair gives work to a boat that still has to sail there, and assignment alone closes nothing.
- The gain over the whole period is small, 0.3 km in the median. Both modes show 0.0 km overdue at 9,000 s, so they only part late: 3.3 vs 3.0 km at 12,000 s, then 6.5 vs 3.3 km at 14,000 s. The result depends on when the run is scored, and this tape ends 6,800 s after the failure.
- Lane crossings in view do not improve: `off` keeps 9 of 9 in all 30 seeds, because every one of the 9 falls within 1.8 km of a picket and the pickets stay put. `elysa` keeps 9 of 9 in 27 seeds, 8 in 2 and 7 in 1. Repair can only cost here.
- Fewer boats cannot close the gap. The four-segment loop a repair hands to one boat is 25.4 km, 11,043 s at 2.3 m/s before any current, close to the 12,000 s target.

**Detection is a distribution, and mostly a miss.** With `elysa`, a boat saw the dark contact in 10 of 30 seeds, 0 to 1,691 s after it appeared. In 20 of 30 no boat came within camera range before it left. A watcher had it in view in 8 of 30 seeds, 192 to 1,809 s after it appeared. Detection depends on where the sweeper is in its loop. It was identical in `off` and `elysa` in all 30 seeds: repair does not change who finds the contact, only who takes it afterwards.

**Static detects for a poor reason.** `static` sees the contact in 5 of 5 seeds only because boat 2's station is about 1.1 km from it. That is a coincidence of the scenario, not coverage. Static also means no sweeping and no reassignment, not "never moves": a boat that sees a candidate still holds it.

**Never visited.** Zero in `off` and `elysa` after warm-up. The "seg:M:0 never visited" in the cold-start batch of #27 and #22 was a start-up effect. It does not mean coverage is good: worst ages still pass 16,000 s.

**4 km radio.** No boat detected the contact in any of 5 seeds with `off` or `elysa`. Cause not established yet.

**Crossings do not separate the modes.** This metric shows no gain from repair in this geometry and should not be presented as one.

## Checks

| Check | Result |
|---|---|
| F1 warm hash equal across modes | pass, every seed |
| F2 ages and physical hash equal at T-1, off vs elysa | pass, every seed |
| F3 off makes 0 claims after T | pass, every seed |
| F4 modes differ by `policy` only | pass, every seed |
| F5 at least 5 seeds, more than one outcome per mode | pass |
| Repeat run gives byte-identical `scorecards.json` | pass, 15-run batch run twice |
| Console never fresher than truth (#29) | **fail**: up to 15,315 s in elysa, 16,247 s in off, 22,667 s in static |

## What is byte-identical, and what is not

- Identical across modes at the same seed: physical state at the end of warm-up, including queued radio bytes. Between `off` and `elysa`, also physical state and sample visits at T-1.
- `static` gets its policy at the end of warm-up, so it shares the warm state and then differs.
- Not covered: internal agent state is not in the physical hash. `eval/repeat.py` covers it across processes.
- The sim clock stays ahead of mission time by 10,800 s. Tape, tide flip and `repair_off_after_ms` are shifted with it.
- Visit credit follows `World._credit_visits`: a boat on its way home counts as it passes.
