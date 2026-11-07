# eval/ — owner: D

Metrics, three-mode baseline runner, scorecard. Never imported by `agent/`.

Rule: only D edits files here. Others open an issue or ask in chat.

| File | Feature | What |
|---|---|---|
| `warm.py` | 12 | 3 h warm-up: seed-drawn place on each sweeper's tour loop, battery held full, bidding off, tape and tide shifted. Same warm hash in every mode. Each run card records `warm_state`: the seeded phases, every boat's position, follower index and charge at mission time 0, and that `place_boats` overwrote World's cold placement (#72) |
| `metrics.py` | 3 | Truth: sample ages, km overdue from real interval lengths, km never visited, ownership, claims, contact timeline |
| `ais_observer.py` | 12 | Real cargo and tanker crossings of the patrolled cables after T, in view or not. Reads the private clip; agents never see it |
| `report.py` | 12 | Scorecard, median and range over seeds; fairness F1-F5 |
| `run_batch.py` | 12 | `static`, `off`, `elysa` x seeds; one JSONL per run plus `scorecard.md` |
| `repeat.py` | 4 | D1: same digest in fresh processes with different `PYTHONHASHSEED`. D2: reset mid-run equals a fresh run |
| `gap.py` | 11 | The console may show a segment older than truth, never fresher (60 s slack for heartbeat timing) |

```bash
uv run python -m eval.run_batch                    # 15 runs, about 2 min with 8 jobs
uv run python -m eval.run_batch --speed 3000
uv run python -m eval.run_batch --radio 4000
uv run python -m eval.repeat --seeds 1             # slow: three processes per mode
uv run pytest -q tests/eval                        # includes the slow fairness runs
```

Definitions:

- **Truth:** every number here is the evaluator's. Shore-reported numbers are a different thing and are labelled so.
- **Mission time:** 0 is the end of warm-up, the clock the tape is written in. The sim clock stays ahead by the warm-up, because boats hold leases and timers against it.
- **Coverage is a sensor visit only:** an enabled, charged boat within `r_verify_m` of a sample (`World._credit_visits`). A boat heading home still counts as it passes. Owning a task counts for nothing (S5).
- **km overdue:** cable length whose newest visit is older than `revisit_target_s` at `evaluate_s`, using each sample's real interval length. Sums to 23.6 km, not 24.1.
- **Never visited** is None, reported as its own km and never inside km overdue. `Overdue plus never visited` is the sum.
- **Mean km overdue after T:** km overdue every 60 s from the first failure to `evaluate_s`, averaged.
- **Reserve violation** (#109): an enabled boat more than 50 m from the Korsør station with less than `reserve_s` of charge. Boat-seconds over the mission; `stranded_boats` lists any at 0 away from the station. A switched-off boat is an injected failure and is not counted.
- **Unserved task-seconds** (#109): from T to evaluation, seconds in which a fixed task (segment, picket, relay) has no live owner, summed and split by kind. Contact tasks are covered by the contact rows.
- **Recovery outcome** (#109) at evaluation: `all tasks`, `cables only` (a picket or the relay has no live owner) or `not recovered` (a segment has none). `unowned_at_end` names them.
- **`scorecard.json`**: per mode, median, range and reached-in-k-of-n for every table row, the recovery outcome count and the outcome by seed, with `source`, `seeds` and `preliminary`.
- **Modes** differ in `policy` only (F4). `static` means fixed stations forever: no sweeping, no bids, no shadowing. A static boat that sees a candidate still detects and reports it (the shore gets the contact) but never leaves its station, so `static` can be "in view" of a contact by luck of geometry only. Agreed with A in #19; locked by `tests/agent/test_contact.py::test_static_boats_report_the_contact_but_never_leave_station` and `tests/agent/test_protocol.py::test_policy_static_parks_every_boat`. `off` stops bidding at T.

`run_batch` exits 1 and prints `PRELIMINARY` until every fairness and gap check passes. Do not put its numbers on a slide before that.
