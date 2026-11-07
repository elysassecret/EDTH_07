# evidence/ — owner: C

Feature 28 / BUILD_PLAN step 30: a tamper-evident log of what the shore received and decided.

Rule: only C edits files here. Others open an issue or ask in chat.

## Use it

```bash
uv run python -m server --serve-web                        # the run log goes to runs/*.jsonl
uv run python -m evidence.build runs/<run>.jsonl           # writes runs/<run>.evidence.jsonl
uv run python -m evidence.verify runs/<run>.evidence.jsonl # "chain OK" or the first bad record
```

Demo: open the evidence file, change one number in one line, run verify again. It names the
chain and record, e.g. `usv-02: record 5 was changed after it was written (hash differs)`.

One-click incident report (console button **Evidence**, or the command line):

```bash
uv run python -m evidence.report runs/<run>.jsonl --from 7000 --to 9600   # writes <run>.report.md
```

The console's Evidence panel downloads the report for the last 30 sim-minutes or the whole run
(`/api/report.md`), and runs the tamper demo (`/api/tamper-demo`): it changes one character of
one record in a copy, and the check names that record.

## How it works (60 seconds)

- Each record holds the hash of the record before it and its own SHA-256 over all its fields
  (`chain.py`). Change a record and its hash no longer matches; fix that hash and the next
  record's link breaks.
- The last hash of each chain (the head) is signed with Ed25519 (`keys.py`). Rewriting the whole
  chain needs the private key, which lives in `runs/evidence-key.pem` (gitignored, owner-only;
  never commit it). Verify with `--key-id` to check it was signed by the key you expect.
- Chains: `usv-01`..`usv-05` (each report as received at shore, with position, mode, battery,
  link) and `shore` (exercise failure events, watch-officer commands, decision changes, alerts,
  contact observations). Built from `/shore` data only, never truth (`build.py`).
- Each record keeps observation time (`t_obs`) and logged time (`t_log`) apart, names its time
  source (here the sim clock; the sim has no GNSS model) and carries zone labels: patrol box,
  lane band (`lane_half_m`), cable visit range (`r_verify_m`), from the scene config.

## What it does not do (say this on stage)

- It shows if a record was changed after it was written. It does not show the sensor was right.
  No claim on admissibility; never say "court-ready", "tamper-proof" or "blockchain".
- The boats don't sign their own records yet. That needs chain heads in heartbeats (`agent/`,
  Javier, issue #37). Today the shore signs what it received.
- Records from the shore picture are sampled every run-log snapshot (10 sim-s), so not every
  heartbeat appears.
- Boat-side signing is issue #37 (Javier).
