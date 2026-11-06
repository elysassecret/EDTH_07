# Runbook: milestones, cut order, the hard fallback rule

## Milestones (exit checks)

| Milestone | Exit check | How to check |
|---|---|---|
| Fri 21:00 | Contract, owners, default policies frozen; mentor decision written | `contract/` unchanged after this; docs/mentor_log.md one-pager filled |
| Sat 00:00 | Five boats on the real scene, freshness on map, deterministic reset | `pytest -q tests/smoke tests/determinism` |
| Sat 12:00 | `core-fallback` tagged, baseline runner works, first gap measured, any boat removable | `git tag core-fallback`; `python -m eval.run_batch --seeds 1`; kill any boat in the dashboard |
| Sat 18:00 | Link loss, split and rejoin, relay takeover; deck v0 with business slides | `pytest -q tests/protocol`; S4, S6 |
| Sat 23:00 | Contact and approval; feature freeze; first full video exists | `pytest -q tests/story`; a complete recording exists |
| Sun 09:00 | Final batch, real numbers replace all scratch figures | `python -m eval.run_batch` and the 3.0 m/s sensitivity: `--speed 3.0` |
| Sun 10:00 | Code freeze, tag `final` | `pytest -q` green on a clean clone |
| Sun 10:30 | Video uploaded, link tested signed out | |
| Sun 11:30 | Deck submitted, filename starts with team number | |
| Sun 12:00 | Hard deadline | |

## Cut order, first to go

spoofed boat; evidence-log report (keep the chain); deputy; cue tasks down to one replayed cue; manual-operator run; extra scorecard rows; notification and retry queue; fallback branch variations; peer sharing down to a single-hop relay.

**Never cut:** reset, the three-mode baseline, the video, the seven-criteria deck, gaps shown openly.

## Hard fallback rule

Any milestone more than 60 minutes late triggers the next cut immediately, with no debate. If `core-fallback` does not run end to end at Sat 12:00, all P1 work stops until it does. If the first ON/OFF run shows no visible gap between modes, D stops feature work with A and fixes tasks or geometry first. If `main` fails smoke or the batch at Sun 09:30, revert to the last green tag and disclose the reduced scope on the deck. Do not debug after 10:00.

## Demo keys (dashboard)

Space pause/resume · 1–5 kill/restore boat · r cut/restore the relay link (5–shore) · buttons for any directed link, battery low, dark contact at a click · warp 5× / 60× / 240× / auto.

## Offline copy

Clone to two laptops, `pip install -r requirements.txt` on venue Wi-Fi, copy `data/ais-clip-box.csv` by USB, run `pytest -q tests/smoke` with Wi-Fi off.
