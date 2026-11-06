# Architecture, languages and requirements

Decided in the team interview on 6 Nov 2026:
- **Python** for the brain, simulator, server and evaluation.
- **TypeScript + React + MapLibre** for the console.
- **WebSocket + JSON** between them.
- **Offline vector map**, with a **Sentinel-2 satellite image** as a toggleable layer.
- **Two laptops** set up for the demo.
- **Rust is roadmap only.**

---

## 1. Who writes which language

| Person | Role | Languages this weekend | Main libraries |
|---|---|---|---|
| **Javier (A)** | Swarm brain, contract | Python | stdlib, `numpy`, `pydantic` (contract views only), `pytest`, `hypothesis` |
| **Simeone (B)** | Simulator, AIS, triage | Python | `numpy`, `shapely`, `pyproj`, `pandas`, `pytest` |
| **Alexandru (C)** | Console, bridge, evidence | **TypeScript** (web) + Python (server, evidence) | React, Vite, MapLibre GL JS, deck.gl, Zustand · `websockets`, `cryptography` |
| **Franco (D)** | Metrics, baseline, tests, pitch | Python + YAML (CI) | `pandas`, `numpy`, `matplotlib`, `pytest` |

**Rust:** listed on the slides as roadmap, "Rust edge runtime for the boat computer". There's no speed problem to solve this weekend: 5 boats, a 1 s tick and 14,400 sim-seconds run in seconds in Python.

**Using Claude:** everyone codes with Claude Code. The root `CLAUDE.md` holds the rules every teammate's Claude must follow: stay in your folders, the contract freeze, determinism. **Each person must still be able to explain their part in 60 seconds.** The jury will ask.

---

## 2. Components

```text
┌──────────────────────── one Python process (server/) ────────────────────────┐
│                                                                               │
│  world/ (B)  sim clock ─► motion · battery+current · sensors · radio channel   │
│      │                         ▲ inbox bytes only          │ outbox bytes     │
│      ▼                         │                           ▼                  │
│  agent/ (A) × 5 boats    each boat: own sensors + radio inbox ─► decisions     │
│      │                                                                        │
│  ais/ (B) replay of real AIS, per-boat reception range                         │
│  eval/ (D) metrics read from the run log (never imported by agent/)            │
│      │                                                                        │
│  server/ (C)  snapshot builder ─► WebSocket /shore (delivered data only)       │
│                                 ─► WebSocket /truth (evaluator panel)          │
│               ◄─ commands: confirm/stop/approve/decline/inject                  │
│               JSONL run log ─► runs/  ·  replay from seed + injection list     │
└───────────────────────────────────────────────────────────────────────────────┘
                 │ ws://localhost:8765   JSON, 5–10 Hz
                 ▼
        web/ (C)  React + MapLibre console in the browser (served from web/dist)
```

| Component | Owner | Language | Uses | Inputs → outputs |
|---|---|---|---|---|
| `contract/` | Javier (+Simeone, Alexandru review) | Python | dataclasses (`Rec`, envelope), **pydantic v2** for the snapshot and commands, exported to **JSON Schema**, then **TypeScript types** in `web/src/contract.ts` | The single source of truth for every message |
| `agent/` | Javier | Python | stdlib, `numpy`. **No I/O, no clock, no randomness of its own** | `(t, own sensors, inbox)` → `outbox`, task records |
| `world/` | Simeone | Python | `numpy`, `shapely` (lines, buffers), `pyproj` (lat/lon ↔ metres) | Scene, event tape, seed → boat states, radio delivery, sensor views |
| `ais/` | Simeone | Python | `pandas` | `data/ais-clip-box.csv` → pings within each boat's range |
| `triage/` (gated) | Simeone | Python | `pandas`, `numpy` | AIS vessel-days → explainable score and ranked queue |
| `server/` | Alexandru | Python | `asyncio`, `websockets` | Runs the sim, broadcasts snapshots, applies commands, writes and replays JSONL |
| `web/` | Alexandru | TypeScript | **Vite, React, MapLibre GL JS, deck.gl, Zustand**, Vitest | Snapshots → chart, cards, tracks, decisions, alerts, coverage |
| `evidence/` (P1) | Alexandru | Python | `hashlib`, `cryptography` (Ed25519) | Events → per-boat hash chain, incident report |
| `eval/` | Franco | Python | `pandas`, `numpy`, `matplotlib` | Run logs → metrics, three-mode baseline, scorecard, charts for the deck |
| `tools/` | Franco | Python | `shapely`, `pyproj` | Scene checks; coastline and satellite preparation |
| `deck/` | Franco | Slides → PDF | Google Slides or PowerPoint | `NN_ProjectName.pdf` + video link |

---

## 3. The map: offline vectors plus a satellite layer

**Base layer, always offline:**
- **Coastline:** OSM land polygons (osmdata.openstreetmap.de), clipped once to the box by `tools/` into `web/public/geo/land.geojson`, small enough to commit. Credit: © OpenStreetMap contributors.
- **Cables, lane, box, Korsør, pickets, relay station:** drawn from `data/scene-coordinates.json`.
- **No online fonts.** A MapLibre style normally downloads its fonts, so labels are drawn with deck.gl `TextLayer` instead. Nothing in the style may point to a URL.

**Satellite layer (toggle):**
- **Source:** Copernicus **Sentinel-2 L2A**, 10 m, free, from the Copernicus Data Space browser. Needs one free account.
- **How:**
  1. Pick a cloud-free date and export a true-colour image clipped to the box.
  2. `tools/prepare_satellite.py` reprojects it and writes `web/public/geo/s2_box.png` plus its four corner coordinates.
  3. MapLibre shows it as an `image` source under the vector layers.
- **Credit:** "Contains modified Copernicus Sentinel data [year]".
- **Later (roadmap):** a live high-resolution toggle using Danish orthophotos from Dataforsyningen (free token), when Wi-Fi works.

---

## 4. Requirements

### Functional
Features **1–25** in [FEATURE_PRIORITIES.md](FEATURE_PRIORITIES.md) are the functional requirements. The build steps and acceptance tests (D1–D6, F1–F5, P1–P8, S1–S6, R1–R3) are in [BUILD_PLAN.md](BUILD_PLAN.md).

### Non-functional

| # | Requirement | How we check it |
|---|---|---|
| N1 | **Runs fully offline** (no internet at the venue or on stage) | Demo laptop with Wi-Fi off |
| N2 | **Deterministic:** same seed gives the same run on Mac, Windows and Linux | Hashes equal across two machines (D1) |
| N3 | **One command starts the demo** | `uv run python -m server --serve-web` opens the console |
| N4 | Console updates at 5–10 Hz with ≥200 AIS tracks without stutter | Watch the FPS counter at 240× warp |
| N5 | The console **never shows old data as live** | Kill the server: a "FEED LOST" banner appears within 2 s |
| N6 | Auto-reconnect after a feed drop | Restart the server: the console resumes without a reload |
| N7 | Works on **macOS, Windows and Linux** | CI runs on all three; each person runs smoke locally |
| N8 | Cold start under 30 s on the demo laptop | Stopwatch |
| N9 | **No secrets or AIS CSV in git** | `.gitignore`, PR checklist |
| N10 | Agents can't cheat: they see only their own sensors and radio inbox | D6 import test, bytes-only radio |
| N11 | Two laptops can each run the full demo from a clean clone | Tested Sun 09:00 |

---

## 5. Toolchain (same on every laptop)

| Tool | Version | Why |
|---|---|---|
| **uv** | latest | Installs Python itself and locks dependencies identically on Mac, Windows and Linux |
| **Python** | **3.12** (pinned in `.python-version`) | Every dependency has wheels for it |
| **ruff** | via uv | One lint/format tool. Run `uv run ruff check . && uv run ruff format .` |
| **pytest + hypothesis** | via uv | Tests and property tests |
| **Node.js** | current LTS (pin in `web/.nvmrc` at setup) | Console build |
| **pnpm** | via `corepack enable` | Fast, locked JS installs |
| **TypeScript** | strict mode | Catches contract mistakes at build time |
| **Git** | `.gitattributes` forces LF | Stops Windows/Mac line-ending noise in diffs |

**Setup, once per laptop:**
```bash
# install uv: https://docs.astral.sh/uv/  (Mac/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh)
uv sync                  # creates .venv with Python 3.12 and all deps
uv run pytest -q tests/smoke
corepack enable && cd web && pnpm install   # Alexandru's machine and the demo laptops
```

---

## 6. Contract flow (Python ↔ TypeScript)

1. Javier defines the snapshot and commands as pydantic models in `contract/views.py`.
2. `uv run python -m contract.export` writes `contract/schema.json`.
3. `pnpm gen:contract` in `web/` turns that into `web/src/contract.ts` (json-schema-to-typescript).
4. If either side drifts from the schema, the TypeScript build or a smoke test fails. **Sign-off Fri 20:30, freeze 21:00.**

Until the real sim exists, Alexandru's `server/mock_feed.py` sends the same JSON, so the console never waits for Javier and Simeone.

---

## 7. Open items

- **Satellite image:** someone makes the Copernicus account and downloads the image before Saturday noon. Suggested owner: Franco (`tools/`).
- **Node LTS version:** pin on Friday in `web/.nvmrc`.
- **The two demo laptops:** name them on Friday. One should be Alexandru's Mac, since the console is built there.
