# Runbook: Sunday, cut order, the hard fallback rule

Milestones are in `docs/PLAN.md` section 4. This page is the commands.

| When | Exit check | Command |
|---|---|---|
| Sat 23:00 | Feature freeze; a full video exists | `uv run pytest -q tests/story` |
| Sun 09:00 | Final batch replaces every placeholder | see below |
| Sun 10:00 | Code freeze, tag `final` | `uv run pytest -q` on a clean clone |
| Sun 10:30 | Video uploaded, link tested signed out | |
| Sun 11:30 | Deck submitted, filename starts with the team number | |
| Sun 12:00 | Hard deadline | |

```bash
git checkout main && git pull
uv run python -m eval.run_batch --out runs/main
uv run python -m eval.run_batch --speed 3000 --out runs/speed3000
uv run python -m eval.run_batch --radio 4000 --out runs/radio4000
uv run python -m eval.run_batch --modes off,elysa --seeds 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30 --out runs/paired30
uv run python -m tools.scene_check
uv run python -m eval.repeat --seeds 1
```

The AIS clip must be in `data/`, or the crossing rows say "AIS clip not present". If `run_batch` still prints PRELIMINARY, read why before any number goes on a slide.

## Cut order, first to go

Evidence report (keep the chain); deputy; manual-operator run; extra scorecard rows; retry queue; peer sharing down to a single-hop relay.

**Never cut:** reset, the three-mode baseline, the video, the seven-criteria deck, gaps shown openly.

## Hard fallback rule

Any milestone more than 60 minutes late triggers the next cut immediately, with no debate. If `main` fails smoke or the batch at Sun 09:30, revert to the last green tag and disclose the reduced scope on the deck. Do not debug after 10:00.

## Offline copy

Clone to two laptops, `uv sync` on venue Wi-Fi, copy `data/ais-clip-box.csv` by USB, run `uv run pytest -q tests/smoke` with Wi-Fi off. If `uv python install` fails on Windows, set `UV_PYTHON_INSTALL_DIR` to a folder under `%LOCALAPPDATA%` (#51).
