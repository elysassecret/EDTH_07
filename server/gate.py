"""Release gate: one command that says PASS or FAIL for the whole product. Owner: C.

    uv run python -m server.gate            # everything (about 15 min)
    uv run python -m server.gate --fast     # skip the browser suite and the long checks
    uv run python -m server.gate --pw-config web/playwright.local.config.ts

Runs, in order, and stops nothing early (every layer is reported):
  lint (ruff), python tests (pytest), web types (tsc), web unit tests (vitest), web build,
  browser tests (Playwright, real server), and the long simulator checks (marked slow).
Exit code 0 only if every layer passed. GitHub Actions is blocked by billing, so this is the gate:
run it before every PR, merge, demo and recording.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def layers(fast: bool, pw_config: str | None) -> list[tuple[str, list[str], Path]]:
    web = ROOT / "web"
    out = [
        ("lint (ruff)", ["uv", "run", "ruff", "check", "."], ROOT),
        ("python tests", ["uv", "run", "pytest", "-q", "-p", "no:cacheprovider", "tests",
                          *(["-m", "not slow"] if fast else [])], ROOT),
        ("web types (tsc)", ["npx", "tsc", "--noEmit", "-p", "."], web),
        ("web unit tests", ["pnpm", "test"], web),
        ("web build", ["pnpm", "build"], web),
    ]
    if not fast:
        cfg = ["--config", pw_config] if pw_config else []
        out.append(("browser tests (Playwright)", ["pnpm", "exec", "playwright", "test", *cfg], web))
    return out


def run(name: str, cmd: list[str], cwd: Path) -> tuple[bool, float, str]:
    t0 = time.monotonic()  # wall clock for the report only, never sim data
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-15:])
    return p.returncode == 0, time.monotonic() - t0, tail


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fast", action="store_true", help="skip the browser suite and slow tests")
    ap.add_argument("--pw-config", default=None, help="Playwright config (e.g. a local one)")
    a = ap.parse_args()
    rows = []
    for name, cmd, cwd in layers(a.fast, a.pw_config):
        print(f"... {name}", flush=True)
        ok, secs, tail = run(name, cmd, cwd)
        rows.append((name, ok, secs))
        if not ok:
            print(f"--- {name} FAILED, last lines:\n{tail}\n", flush=True)
    print("\nRelease gate")
    for name, ok, secs in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {name:28s} {secs:6.0f} s")
    passed = all(ok for _, ok, _ in rows)
    print(f"\n{'PASS: ready to merge, demo or record' if passed else 'FAIL: do not merge, demo or record'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
