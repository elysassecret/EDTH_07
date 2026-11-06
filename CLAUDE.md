# Rules for Claude in this repo (EDTH_07)

Read docs/PLAN.md and docs/ARCHITECTURE.md before writing code.

- **Stay in the owner's folders.** Javier (A): agent/, contract/. Simeone (B): world/, ais/, triage/, scenarios/. Alexandru (C): web/, server/, evidence/. Franco (D): eval/, tools/, deck/, tests/smoke, .github/. Ask before touching any other folder.
- **contract/ is frozen after Fri 21:00.** Changes need a PR approved by A, B and C.
- **Languages:** Python 3.12 (uv, ruff, pytest) everywhere except web/, which is TypeScript strict + React + Vite + MapLibre + deck.gl + Zustand (pnpm).
- **Determinism:** agent/ never calls time.time(), never uses the global random module, never iterates a set without sorted(). Time comes in as an argument (integer sim ms).
- **Agents see only their own sensors and radio inbox.** agent/ never imports world/, eval/ or server/.
- **Offline:** no runtime network calls, no online fonts or tiles in the map style.
- **Never commit** data/*.csv (AIS), .venv, runs/, secrets.
- **Honesty:** no invented numbers in code comments, logs or UI text. Say "cue for a look", never "suspicious" or "hostile".
- **No Claude attribution:** do not add Co-Authored-By or "Generated with Claude Code" lines to commits or PRs.
- Before every PR: `uv run ruff check . && uv run pytest -q tests/smoke`.
