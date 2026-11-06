# Team plan: Challenge 07 (main), Challenge 02 (only if time)

**Product:** a swarm brain for five patrol USVs over Great Belt cables, plus the shore operator's console. Boats reassign work themselves when one fails, keep a dark contact in view, and show the operator the coverage gap that remains.
**Later, if time allows:** Challenge 02 "triage", which ranks ships near cables by anchor-drag behaviour and sends a boat to look at the top one.

Detail lives in this folder: [BUILD_PLAN.md](BUILD_PLAN.md) (algorithms, step numbers, tests) and [FEATURE_PRIORITIES.md](FEATURE_PRIORITIES.md) (features 1–41, energy modes, the 02 design). Briefs and research are in [briefs/](briefs/) and [research/](research/). This page is **who does what, and how we avoid merge conflicts.**

---

## 1. Roles

**A = Javier** (`emermelada`) · **B = Simone** · **C = Alexandru** (`zytzev`) · **D = Franco**. Simone and Franco: put your GitHub username in `.github/CODEOWNERS` (one of you is `FearedLynx`). Whoever is not in the `elysassecret` org yet needs an invite.

| Slot | Name | Owns (folders) | One-line job | Features | ~Hours |
|---|---|---|---|---|---|
| **A: Swarm brain** | **Javier** | `agent/`, `contract/`, `tests/agent/`, `config/agent.toml` | The logic on every boat: task table, merge, auction, relay, contact, energy modes | 5, 6 (reassign), 8, 9, 10, 14 (logic), 16 (bids) | ~23 |
| **B: World & data** | **Simone** | `world/`, `ais/`, `triage/`, `scenarios/`, `tests/world/`, `config/scene, boat, radio, energy` | The simulated sea: scene, motion, battery and current, sensors, radio; AIS replay; later the 02 score | 1, 2 (routes), 6 (battery), 7, 15, 16 (drift), 26 | ~22 |
| **C: Operator console** | **Alexandru** | `web/`, `server/`, `evidence/`, `tests/server/`, `config/ui.json` | What the watch officer sees and clicks; the WebSocket bridge; failure-injection controls; the video recording | 13 (UI), 17–25, 28 | ~23 |
| **D: Proof & pitch** | **Franco** | `eval/`, `tools/`, `deck/`, `tests/smoke, eval, story/`, `requirements.txt`, `config/run.toml`, `.github/workflows/` | Metrics, three-mode baseline, scorecard, tests; mentor log; the deck and business slides; repo admin | 3, 4, 11 (check), 12 | ~24 |

**Balance changes from the build plan:**
- Real-scene tests R1–R3 move from B to D.
- B's AIS cue tasks become the 02-lite triage (same hours, gated).
- Energy features 15–16 add about 1.5 h to B and 1 h to A.
- The manual-operator comparison run moves to secondary, which pays for that time.

---

## 2. What each person does RIGHT NOW (Friday)

**Everyone, 19:00–19:15**
1. Accept the org invite. Clone the repo:
   ```bash
   gh repo clone elysassecret/EDTH_07 && cd EDTH_07
   python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
   pytest -q tests/smoke
   ```
2. `data/scene-coordinates.json` is already in the repo. Get `ais-clip-box.csv` from Franco and put it in `data/`. It is gitignored; **never commit it**.
3. Simone and Franco: put your GitHub username in `.github/CODEOWNERS`.

**A, Javier: 19:15–21:00:** with B, finish and **freeze `contract/`** (constants, messages, tasks; views with C at 20:30). **21:00–24:00:** `agent/table.py` and `agent/core.py`: record store, merge, heartbeat, per-boat lease. Done when the merge tests pass (commutative, associative, idempotent).

**B, Simone: 19:15–21:00:** with A on `contract/`; check every number in `config/`. **21:00–24:00:** `world/routes.py` and `world/motion.py`: load the scene, local metres, ≤5 km segments, five boats moving at 2.3 m/s. Done when there are 6 segments, ~23.5 km, and the boats move.

**C, Alexandru: 19:15–21:00:**
- Do the mentor round with D. Show a paper sketch of the console and ask what a watch officer needs.
- **20:30:** review `contract/views.py` with A and B and sign off the snapshot JSON.

**C, Alexandru: 21:00–24:00:**
- `server/mock_feed.py`: fake snapshots in the agreed format, so you never wait for A and B.
- `web/`: offline chart with cables, lane, Korsør and the box, with mock boats moving on it.
- Done when the map renders with Wi-Fi off.

**D, Franco: 19:00–19:15:** set the repo rules (section 3). **19:15–21:00:** mentor round with C. Keep a mentor log: "assumed X, mentor said Y, changed Z". **21:00–23:00:** `eval/metrics.py` (segment ages, km overdue). **23:00–24:00:** `tools/scene_check.py`: worst age, return limit, radio graph. Start the deck skeleton with the business slides first.

**Milestone, Sat 00:00:** five boats on the real scene, revisit ages on the map, deterministic reset.

---

## 3. GitHub rules: how we never get merge conflicts

1. **One owner per folder.** You only edit your own folders (table above). `CODEOWNERS` enforces this through PR review. If you need a change in someone else's folder, message them.
2. **Config is split per owner,** one file each, so nobody fights over a shared settings file.
3. **`contract/` freezes Fri 21:00.** After that, changes only by a PR approved by A, B and C. This is the only shared file set.
4. **Branches:** short-lived, named `a/<thing>`, `b/<thing>`, `c/<thing>`, `d/<thing>`, e.g. `c/decision-cards`.
5. **Merge small and often:** a PR to `main` at least every 2–3 hours and at every milestone. Before opening a PR, update your branch:
   ```bash
   git fetch origin && git rebase origin/main
   pytest -q tests/smoke
   ```
6. **`main` is protected:** PR only, smoke tests must pass (GitHub Action), no force-push. D turns this on in the repo settings.
7. **Tags:** D tags `core-fallback` at Sat 12:00 and `final` at Sun 10:00. A tagged version must always run from a clean clone.
8. **Never commit:** AIS CSVs, `.venv`, `runs/`, API keys.

---

## 4. Timeline and milestones (from the build plan)

| When | Milestone | Exit check |
|---|---|---|
| Fri 21:00 | Contract frozen, owners set, mentor decision written | Snapshot JSON signed off by C |
| Sat 00:00 | Five boats, real scene, freshness on the map | Reset is deterministic |
| Sat 12:00 | `core-fallback` tagged; baseline runner works | Any boat can be removed; first gap measured |
| Sat 18:00 | Link loss, split/rejoin, relay takeover; deck v0 with business slides | Shore view goes stale correctly |
| Sat 23:00 | Contact and approval; **feature freeze**; first full video | Nothing new after this |
| Sun 09:00 | Final seeded batch: real numbers replace all scratch figures | Median and range for every number |
| Sun 10:00 | **Code freeze**, tag `final` | |
| Sun 10:30 | Video uploaded, link tested while signed out | |
| Sun 11:30 | Deck submitted, filename starting with the team number | |

**Hard rule:** a milestone more than 60 minutes late triggers the next cut immediately (cut order in the build plan). **Never cut:** reset, the baseline, the video, the seven-criteria deck, gaps shown openly.

---

## 5. Challenge 02 gate

Start `triage/` (B) and the triage queue tab (C) **only when** features 1–25 are green on `main` **and** a full video exists. Before that, 02 appears on the slides as "in development".
