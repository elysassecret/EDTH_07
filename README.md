# EDTH_07
Swarm Coordination for Collaborative Missions | Challenge 7 · EDTH Copenhagen 2026 · team Elysa's Secret

A swarm brain for five patrol USVs over Great Belt cables, plus the shore operator's console.

**Start here: [docs/PLAN.md](docs/PLAN.md)** for roles, what to do right now, and the branch rules. Everything else to read: [docs/README.md](docs/README.md).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q tests/smoke
```

| Folder | Owner | What |
|---|---|---|
| `contract/` | A (+B, C review) | Shared messages, tasks, snapshot shape. Frozen Fri 21:00 |
| `agent/` | A | Swarm brain on each boat |
| `world/`, `ais/`, `scenarios/` | B | Simulator, radio, AIS replay, event tape |
| `triage/` | B | Challenge 02 module (gated) |
| `server/`, `web/`, `evidence/` | C | Operator console and bridge |
| `eval/`, `tools/`, `deck/` | D | Metrics, baseline, scorecard, pitch |

`data/` holds the scene and the AIS clip. **The AIS CSV is gitignored. Never commit it.**
