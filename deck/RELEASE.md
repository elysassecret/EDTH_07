# Release checklist (owner: D)

Status board for the `final` tag. Every line is a check someone ran, with the evidence next to it. Nothing here is assumed from a merge. Source of truth for ownership and gates: `docs/PLAN.md`.

## Gate: AIS replay (#52) and Challenge 02

**Opens only when both hold:** features 1–25 green on `main` (per `deck/FEATURE_CHECKLIST.md`) **and** a full real-console video exists (C records it, #73). Until then the gate is **BLOCKED** and the decision is posted on #75.

## Clean-start verification

| Check | Command | Evidence |
|---|---|---|
| Clean clone builds | `gh repo clone elysassecret/EDTH_07 edth-clean && cd edth-clean && uv sync` | revision + date + machine |
| Smoke | `uv run ruff check . && uv run pytest -q tests/smoke` | output line |
| Full suite | `uv run pytest -q` | pass/fail counts |
| Scene re-measure | `uv run python -m tools.scene_check` | 7 segments, 23.6 km, 241 samples |
| Batch is not PRELIMINARY | `uv run python -m eval.run_batch --out runs/main` | exit 0, no PRELIMINARY in `runs/main/scorecard.md` |
| Seeded repeat across processes | `uv run python -m eval.repeat --seeds 1` | same digest |
| Console starts offline | `uv run python -m server --seed 1` with Wi-Fi off | map renders, no FEED LOST |

## Two-laptop offline proof (with B)

1. Clone on both laptops on venue Wi-Fi, `uv sync`, then switch Wi-Fi off.
2. Copy `data/ais-clip-box.csv` by USB. Never into git.
3. On each: `uv run pytest -q tests/smoke`, then `uv run python -m eval.run_batch --modes elysa --seeds 1 --out runs/offline`.
4. Compare the `warm_hash` and final `state_hash` of `runs/offline/elysa_s1.jsonl` between the two machines. They must be byte-identical.
5. Record both hashes, both OS names and the revision here.

## CI

GitHub Actions is **blocked by billing**: every run since 2026-11-07 08:39 UTC has zero executed steps with the message "The job was not started because recent account payments have failed or your spending limit needs to be increased." Escalated to the org billing owner on #74. Local evidence replaces CI until it is restored and is labelled as local, never as green CI. The matrix is cut to one runner so the first minutes after restoration go to real checks.

## Final numbers

Run the batch block in `deck/runbook.md` on the `final` tag, Sunday 09:00. Paste the revision into `eval/results.md` and the deck. Quote the 30-seed paired table for `off` vs `elysa`. Keep `runs/` out of git.

## Deck and video

| Item | Owner | Done when |
|---|---|---|
| `deck/DECK.md` numbers replaced from the final batch | D | no `[from Sun 09:00 batch]` left |
| Trade-off slide text (#68) | D | states km overdue and crossings in view side by side |
| Full video | C | link in #73 |
| Link tested signed out | D | opened in a private window, plays |
| PDF named `<team number>_ElysasSecret.pdf` | D | uploaded by Sun 11:30 |

## Tag

```bash
git checkout main && git pull --ff-only
uv run pytest -q
git tag -a final -m "final" && git push origin final
```
