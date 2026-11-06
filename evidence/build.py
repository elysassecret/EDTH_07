"""Build the evidence log from a run log. Owner: C. BUILD_PLAN step 30 (feature 28).

    uv run python -m evidence.build runs/<run>.jsonl      # writes runs/<run>.evidence.jsonl

Uses only what the shore had: the /shore snapshots, the failure events the console scripted
or injected, and the watch officer's commands. Never the truth view.

Chains:
- usv-01 .. usv-05: each report the shore received from that boat (sampled from the shore
  picture every snapshot interval), with its position, mode, battery and link;
- shore: exercise failure events, watch-officer commands, decision state changes, alerts
  raised, contact observations.

Every record keeps observation time and logged time apart, names its time source and carries
zone labels (patrol box, lane band, cable visit range) from the scene geometry.
Limit, stated plainly: the boats do not sign their own records yet. That needs chain heads in
heartbeats (agent/, Javier). Here the shore signs what it received.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon

from evidence.chain import Chain
from evidence.keys import key_id, load_or_create, pub_hex
from server.feed import ROOT
from server.runlog import read

TIME_SOURCE = "sim clock (simulation; no GNSS model)"
FAILURES = ("battery_low", "boat_off", "link_off", "link_on")
OPERATOR = "watch officer (no named login in this demo)"
NOTE = ("Shows whether a record was changed after it was written. "
        "Does not show that a sensor or report was right. No claim on admissibility.")


class Zones:
    """Zone labels from the scene: inside the patrol box, in the lane band, near a cable."""

    def __init__(self, root: Path = ROOT):
        from contract.mission import load_params
        from world.routes import load_scene

        scene = load_scene(root)
        m = scene.mission
        self.box = Polygon(scene.boundary)
        self.lane = LineString(m.lane)
        self.lane_half_m = m.lane_half_m
        self.r_verify_m = load_params(root).r_verify_m
        self.segs = {t.id: LineString(t.pts) for t in m.tasks if t.id.startswith("seg:")}

    def label(self, x: float, y: float) -> list[str]:
        p = Point(x, y)
        out = ["inside patrol box" if self.box.covers(p) else "outside patrol box"]
        if self.lane.distance(p) <= self.lane_half_m:
            out.append(f"lane band (within {self.lane_half_m} m of centreline)")
        out += [f"{k} visit range (within {self.r_verify_m} m)"
                for k, line in sorted(self.segs.items()) if line.distance(p) <= self.r_verify_m]
        return out


def build(run_log: Path, key_path: Path, out: Path | None = None) -> Path:
    lines = read(run_log)
    if not lines or lines[0].get("type") != "header":
        raise ValueError(f"{run_log}: not a run log")
    key = load_or_create(key_path)
    zones = Zones()
    chains: dict[str, Chain] = {}

    def chain(name: str) -> Chain:
        return chains.setdefault(name, Chain(name))

    last_heard: dict[int, int] = {}
    seen_dec: set[tuple[str, str]] = set()
    seen_alert: set[tuple[str, str]] = set()
    seen_contact: dict[str, int] = {}

    for rec in lines[1:]:
        kind = rec["type"]
        if kind == "event" and rec["event"].get("kind") in FAILURES:
            e = rec["event"]
            chain("shore").append("event", e["t_ms"] // 1000, rec["t_ms"] // 1000, TIME_SOURCE,
                                  f"console ({e.get('origin', 'scripted')})", [], e)
        elif kind == "cmd":
            chain("shore").append("command", None, rec["t_ms"] // 1000, TIME_SOURCE, OPERATOR, [],
                                  {"msg": rec["msg"], "ok": rec["ok"]})
        elif kind == "snapshot":
            snap = rec["shore"]
            t = snap["t"]
            for b in snap["boats"]:
                if last_heard.get(b["id"]) == b["last_heard"]:
                    continue
                last_heard[b["id"]] = b["last_heard"]
                data = {k: b.get(k) for k in ("x", "y", "lon", "lat", "mode", "batt", "endurance_s",
                                              "link", "via", "roles")}
                chain(f"usv-{b['id']:02d}").append(
                    "report", b["last_heard"], t, TIME_SOURCE,
                    f"USV {b['id']:02d} heartbeat as received at shore", zones.label(b["x"], b["y"]),
                    data)
            for d in snap["decisions"]:
                if (d["id"], d["state"]) not in seen_dec:
                    seen_dec.add((d["id"], d["state"]))
                    chain("shore").append("decision", d["t"], t, TIME_SOURCE, "shore station", [], d)
            for a in snap["alerts"]:
                if (a["id"], a["level"]) not in seen_alert:
                    seen_alert.add((a["id"], a["level"]))
                    chain("shore").append("alert", a["t"], t, TIME_SOURCE, "console alerts", [], a)
            for c in snap["contacts"]:
                if seen_contact.get(c["id"]) != c["last_seen"]:
                    seen_contact[c["id"]] = c["last_seen"]
                    chain("shore").append("observation", c["last_seen"], t, TIME_SOURCE,
                                          f"seen by {c.get('seen_by', [])}",
                                          zones.label(c["x"], c["y"]), c)

    out = out or run_log.with_name(run_log.stem + ".evidence.jsonl")
    pub = pub_hex(key)
    header = {
        "type": "header", "run_log": run_log.name,
        "run_log_sha256": hashlib.sha256(run_log.read_bytes()).hexdigest(),
        "seed": lines[0].get("seed"), "git_commit": lines[0].get("git_commit"),
        "pub": pub, "key_id": key_id(pub),
        "built_utc": datetime.now(UTC).isoformat(timespec="seconds"), "note": NOTE,
    }
    with out.open("w", encoding="utf-8") as f:
        f.write(json.dumps(header, sort_keys=True) + "\n")
        for name in sorted(chains):
            for r in chains[name].records:
                f.write(json.dumps({"type": "record", **r}, sort_keys=True) + "\n")
        for name in sorted(chains):
            f.write(json.dumps({"type": "head", **chains[name].sign_head(key)}, sort_keys=True)
                    + "\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Build runs/<run>.evidence.jsonl from a run log.")
    ap.add_argument("run_log", type=Path)
    ap.add_argument("--key", type=Path, default=ROOT / "runs" / "evidence-key.pem",
                    help="Ed25519 private key (created if missing; never commit it)")
    args = ap.parse_args()
    out = build(args.run_log, args.key)
    head = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    print(f"wrote {out} · key id {head['key_id']}")


if __name__ == "__main__":
    main()
