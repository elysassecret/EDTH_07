"""Load config/default.toml and hash it. Every run log carries the hash."""
from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(path: str | Path | None = None, overrides: dict | None = None) -> dict:
    p = Path(path) if path else ROOT / "config" / "default.toml"
    with open(p, "rb") as f:
        cfg = tomllib.load(f)
    for k, v in (overrides or {}).items():
        sect, key = k.split(".", 1)
        cfg.setdefault(sect, {})[key] = v
    cfg["_hash"] = config_hash(cfg)
    return cfg


def config_hash(cfg: dict) -> str:
    c = {k: v for k, v in cfg.items() if not k.startswith("_")}
    return hashlib.sha256(json.dumps(c, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def load_scenario(path: str | Path | None = None) -> list[dict]:
    p = Path(path) if path else ROOT / "scenarios" / "fixed.toml"
    with open(p, "rb") as f:
        return sorted(tomllib.load(f)["event"], key=lambda e: (e["t"], e["kind"]))


MODES = {
    "static": {"agent.sweep": False, "agent.repair": False},
    "off": {"agent.sweep": True, "agent.repair": False},
    "elysa": {"agent.sweep": True, "agent.repair": True},
}
