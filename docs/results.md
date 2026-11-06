# Results (measured, 6 Nov 2026, commit on branch `claude/core`)

All numbers come from `python -m eval.run_batch`: 5 seeds (warm-up phase and channel tape vary by seed), identical warm state, event tape and channel tape across modes per seed, evaluation at t = 14,000 s, revisit target 12,000 s, 23.6 km of cable in 241 samples. Median (min to max). These replace every scratch figure in the plan. Re-run on Sunday morning before the deck.

## Main run, 2.3 m/s, 8 km boat radio, 14 km shore link

| Metric | static | off | elysa |
|---|---|---|---|
| Cable km overdue at end (headline) | 20.1 (19.7 to 20.7) | 7.7 (4.7 to 8.0) | **3.0 (1.5 to 5.5)** |
| Lane crossings in view after T (cost) | 14 (13 to 14) | 13 (11 to 13) | 16 (15 to 16) |
| Lane crossings after T (total, real AIS) | 17 | 17 | 17 |
| Worst revisit age at end (s) | 24800 | 17273 (16250 to 17285) | 17273 (12753 to 17285) |
| Event to all cable segments owned (s) | n/a | n/a | 60 |
| Operator actions | 0 | 0 | 0 |
| Repair claims after T | 0 | 0 | 16 (16 to 20) |
| Loiter start to detection, C-07 (s) | never | 193 (180 to 206), 2 of 5 seeds | 193 (180 to 206), 2 of 5 seeds |
| Loiter start to shadow boat in view (s) | n/a | 426 (414 to 437) | 426 (414 to 437) |

Read it honestly:
- The headline separates the modes: reassignment cuts cable overdue from 7.7 to 3.0 km, and static pickets leave 20 km unwatched from the start.
- Worst revisit age barely moves between off and elysa (the pre-event cycle sets it), exactly as the research predicted. Do not headline it.
- In this geometry the repair does **not** cost lane coverage (16 vs 13 in view) because boat 4 sweeps Great Belt 1 past the lane crossing. The plan's "gap moves to the lane" story holds for the pickets (both end uncovered), not for crossings in view. Say what was measured.
- Detection of the synthetic dark contact depends on the scout's phase: the loiter window (7,320 to 9,200 s) is 1,880 s of an 8,700 s sweep cycle, so it is caught in 2 of 5 seeds (33% over 30 seeds scanned). Report that as a distribution. Seed 1 is the demo seed (detect 7,525 s, boat 3 in view 7,757 s, cannot hold 9,200 s).
- Operator actions are 0 because watching is pre-approved and the fixed tape has no held action; the dashboard counts Confirm/Stop/Approve/Decline when a person uses them.

## Sensitivity: 3.0 m/s

| Metric | off | elysa |
|---|---|---|
| Cable km overdue at end | 3.3 (1.4 to 4.3) | 1.3 (0.0 to 3.4) |
| Lane crossings in view after T | 13 (13 to 14) | 14 (11 to 15) |
| Detection, C-07 | 180 s, 2 of 5 seeds | 180 s, 2 of 5 seeds |

## Sensitivity: 4 km boat-to-boat radio

| Metric | static | off | elysa |
|---|---|---|---|
| Cable km overdue at end | 20.8 (19.7 to 21.8) | 7.7 (4.7 to 8.0) | 5.1 (2.3 to 9.3) |
| Lane crossings in view after T | 14 | 10 (9 to 12) | 6 (5 to 8) |
| Detection, C-07 | never | 192 s, 2 of 5 seeds | 621 s, 1 of 5 seeds |

At 4 km the north is cut off from shore most of the time; leases expire across partitions, pickets get pulled into relay and cable work, and repair still helps on cable but costs the lane watch. Show it as isolation, which is what it is.

## Other checks

- Determinism: replay of `elysa_s1.jsonl` matched all 240 logged state hashes; same seed in two processes with different `PYTHONHASHSEED` gives identical hashes.
- Fairness: tape hash equal across modes; segment ages at T−1 byte-identical between off and elysa; off makes zero repair claims after T; adjacent modes differ by exactly one config key.
- Evidence: every boat's hash chain verifies; editing one line names the first bad sequence (boat 3, seq 13 in that run).
- Runtime: about 5.5 s per 14,400 s run with AIS replay (plus 10,800 s warm-up) on this laptop.
- Scene: HVDC is 10.02 km inside the box, so it splits into 3 segments at 5 km max (plan said 2); 7 segments total.
