# eval/ — owner: D

Metrics, three-mode baseline runner, scorecard. Never imported by `agent/`.

Rule: only D edits files here. Others open an issue or ask in chat.

| File | Feature | What |
|---|---|---|
| `metrics.py` | 3 | Revisit age per 100 m sample and per segment, cable km overdue, km never visited |
| `repeat.py` | 4 | D1: same digest in fresh processes with different `PYTHONHASHSEED`. D2: reset mid-run equals a fresh run |
| `gap.py` | 11 | The console may show a segment older than truth, never fresher (60 s slack for heartbeat timing) |
| `run_batch.py` | 12 | `static`, `off`, `elysa` × seeds; headline km overdue as median and range; F1–F5 |

```bash
uv run python -m eval.run_batch --jobs 8 --out runs/batch.json   # about 1 min with 8 jobs
uv run python -m eval.repeat --seeds 1 --horizon-s 3000          # full default takes long
uv run pytest -q tests/eval
```

Definitions:

- **Coverage is a sensor visit only:** a boat within `r_verify_m` of a sample. Owning a task counts for nothing (S5).
- **Cold start:** a sample never visited is aged from t = 0. No warm state yet.
- **km overdue:** samples older than `revisit_target_s` at `evaluate_s`, × `sample_step_m`. The short end of a segment is not a sample and is not counted.
- **Mean km overdue after T:** km overdue every 60 s from the first scripted failure to `evaluate_s`, averaged.
- **Modes** differ in the `policy` key only (F4). F2 compares `off` and `elysa`; `static` holds station from t = 0, so its early ages differ by design.

`run_batch` exits 1 and prints `PRELIMINARY` until every fairness and gap check passes. Do not put its numbers on a slide before that.
