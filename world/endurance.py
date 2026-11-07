"""Back-to-back endurance runs: battery, cable coverage, cable hazards, land. Owner: B (with A).

    uv run python -m world.endurance --runs 30 --hours 12 [--first-seed 1] [--out FILE.md]

Each run is a fresh World(launch=True) with the real agents and shore node: the boats start
docked at Korsør, launch, patrol, come home on the battery rule, get a battery swap and go back
out. Seeds first_seed .. first_seed+runs-1, one after the other. Measured per run:

- battery: the lowest battery any boat had while at sea; a boat that reaches 0 at sea fails it.
- coverage: every cable sample (100 m apart) visited at least once, and the longest gap between
  two visits of any sample after its first visit, against the revisit target (config/run.toml).
- cable hazards: the tape's contact without AIS near a cable (C-07): when a boat first saw it,
  and whether a boat kept it in view.
- land: boat positions on the map's real land (web/public/geo/land.geojson), including the quay.
- time on water per boat (away from the dock), the number of battery swaps, and the length of
  each sortie (leaving the dock to docking again).

Every number in the report comes from these runs; nothing is filled in by hand.
"""

import argparse
import json
import tomllib
from pathlib import Path
from statistics import mean

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

from agent.core import Agent
from agent.shore import ShoreNode
from contract.geo import dist, to_xy
from world.sim import World

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_EVERY_MS = 10_000  # land and on-water samples


def _land():
    feats = json.loads((ROOT / "web/public/geo/land.geojson").read_text(encoding="utf-8"))["features"]
    return prep(unary_union([Polygon([to_xy(lat, lon) for lon, lat in f["geometry"]["coordinates"][0]])
                             for f in feats]))


def run(seed: int, hours: float, land=None) -> dict:
    w = World(ROOT, seed=seed, agent_factory=Agent, shore_factory=ShoreNode, launch=True)
    target_ms = int(tomllib.loads((ROOT / "config/run.toml").read_text())["revisit_target_s"]) * 1000
    end = round(hours * 3_600_000)
    land = land or _land()
    shore = w.mission.shore
    boats = sorted(w.boats)
    water_ms = dict.fromkeys(boats, 0)
    min_batt = dict.fromkeys(boats, 1000)
    ran_out: list[tuple[int, int]] = []
    away_since: dict[int, int | None] = dict.fromkeys(boats)
    sorties: dict[int, list[int]] = {b: [] for b in boats}
    last_visit = list(w.sample_visit_ms)
    worst_gap = [0] * len(last_visit)
    on_land: list[tuple[int, int]] = []
    hazard = {"track": None, "start_s": None, "seen_s": None, "kept_in_view": False}
    for e in w.script:
        if e.get("kind") == "contact_start" and not e.get("ais", True):
            hazard.update(track=e["id"], start_s=int(e["t"]))
            break
    while w.t < end:
        w.step()
        t = w.t
        # coverage: gaps between visits of every sample
        for i, v in enumerate(w.sample_visit_ms):
            if v is not None and v != last_visit[i]:
                if last_visit[i] is not None:
                    worst_gap[i] = max(worst_gap[i], v - last_visit[i])
                last_visit[i] = v
        # cable hazard: first sight and keep-in-view by any boat
        tr = hazard["track"]
        if tr is not None and hazard["start_s"] is not None and t >= hazard["start_s"] * 1000:
            for _, node in sorted(w.nodes.items()):
                first = node.contacts.first.get(tr)
                if first is not None and (hazard["seen_s"] is None or first // 1000 < hazard["seen_s"]):
                    hazard["seen_s"] = first // 1000
                if node.contacts.holding == f"contact:{tr}" or node.contacts.watching() == f"contact:{tr}":
                    hazard["kept_in_view"] = True
        for b in boats:
            st = w.boats[b]
            if not st.enabled:
                continue
            away = dist(st.point, shore) > w.dock_m
            batt = st.charge_ms * 1000 // st.endurance_ms
            if away:
                min_batt[b] = min(min_batt[b], batt)
                if st.charge_ms == 0 and (not ran_out or ran_out[-1][0] != b):
                    ran_out.append((b, t // 1000))
            if away and away_since[b] is None:
                away_since[b] = t
            elif not away and away_since[b] is not None:
                sorties[b].append(t - away_since[b])
                away_since[b] = None
            if t % SAMPLE_EVERY_MS == 0:
                if away:
                    water_ms[b] += SAMPLE_EVERY_MS
                p = Point(*st.point)
                if land.contains(p):
                    on_land.append((b, t // 1000))
    swaps = {b: sum(1 for e in w.events if e["kind"] == "battery_swap" and e.get("boat") == b)
             for b in boats}
    visited = sum(v is not None for v in last_visit)
    # a sample's final age counts as a gap too: it has been waiting that long at the end
    final_age = [end - v if v is not None else end for v in last_visit]
    longest = max(max(g, a) for g, a in zip(worst_gap, final_age, strict=True))
    return {
        "seed": seed,
        "hours": hours,
        "min_batt_permille": min(min_batt.values()),
        "ran_out": ran_out,
        "samples": len(last_visit),
        "visited": visited,
        "longest_gap_s": longest // 1000,
        "target_s": target_ms // 1000,
        "over_target": sum(1 for g, a in zip(worst_gap, final_age, strict=True) if max(g, a) > target_ms),
        "hazard": hazard,
        "on_land": len(on_land),
        "water_s": {b: water_ms[b] // 1000 for b in boats},
        "swaps": swaps,
        "sorties_s": {b: [s // 1000 for s in sorties[b]] for b in boats},
    }


def hm(s: float) -> str:
    s = int(s)
    return f"{s // 3600} h {s % 3600 // 60:02d} m"


def report(results: list[dict]) -> str:
    boats = sorted(results[0]["water_s"])
    lines = [
        f"# Endurance: {len(results)} back-to-back runs, {results[0]['hours']:g} h each, shore launch",
        "",
        (f"Seeds {results[0]['seed']}–{results[-1]['seed']}. Real agents and shore node, `World(launch=True)`, "
        "battery swap at Korsør (config/energy.toml). Generated by `python -m world.endurance`; "
        "model values (simulated boats, battery, current), not sea trials."),
        "",
        "## Checks",
        "",
        "| Seed | Lowest battery at sea | Ran out | Samples visited | Longest gap (target) | Samples over target | Dark contact seen after | Kept in view | On land | Swaps |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        hz = r["hazard"]
        seen = "not seen" if hz["seen_s"] is None else f"{(hz['seen_s'] - hz['start_s']) // 60} min"
        lines.append(
            f"| {r['seed']} | {r['min_batt_permille'] / 10:.1f} % | {'**yes**' if r['ran_out'] else 'no'} | "
            f"{r['visited']}/{r['samples']} | {hm(r['longest_gap_s'])} ({hm(r['target_s'])}) | "
            f"{r['over_target']} | {seen} | {'yes' if hz['kept_in_view'] else 'no'} | {r['on_land']} | "
            f"{sum(r['swaps'].values())} |")
    lines += ["", "## Time on water", "", "| Boat | Total on water, all runs | Mean per run | Sorties | Mean sortie (dock to dock) | Swaps |",
              "|---|---|---|---|---|---|"]
    for b in boats:
        tot = sum(r["water_s"][b] for r in results)
        sorties = [s for r in results for s in r["sorties_s"][b]]
        lines.append(f"| USV {b:02d} | {hm(tot)} | {hm(tot / len(results))} | {len(sorties)} | "
                     f"{hm(mean(sorties)) if sorties else 'none finished'} | "
                     f"{sum(r['swaps'][b] for r in results)} |")
    all_sorties = [s for r in results for b in boats for s in r["sorties_s"][b]]
    fails = [r["seed"] for r in results if r["ran_out"] or r["on_land"] or r["visited"] < r["samples"]]
    lines += [
        "",
        (f"All boats, all runs: mean time on water before going home for a swap: "
        f"**{hm(mean(all_sorties)) if all_sorties else 'n/a'}** over {len(all_sorties)} finished sorties."),
        "",
        "## Summary",
        "",
        (f"- Battery ran out at sea: {sum(bool(r['ran_out']) for r in results)} of {len(results)} runs. "
        f"Lowest battery at sea in any run: {min(r['min_batt_permille'] for r in results) / 10:.1f} %."),
        (f"- Every cable sample visited: {sum(r['visited'] == r['samples'] for r in results)} of {len(results)} runs. "
        f"Runs with a sample left longer than the revisit target: {sum(bool(r['over_target']) for r in results)}."),
        (f"- Dark contact near the cable seen: {sum(r['hazard']['seen_s'] is not None for r in results)} of "
        f"{len(results)}; kept in view: {sum(r['hazard']['kept_in_view'] for r in results)} of {len(results)}."),
        f"- Boat positions on land (including the quay): {sum(r['on_land'] for r in results)} samples in all runs.",
        f"- Runs failing battery, full coverage or land: {fails or 'none'}.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--hours", type=float, default=12.0)
    ap.add_argument("--first-seed", type=int, default=1)
    ap.add_argument("--out", type=Path, default=None, help="write the Markdown report here")
    ap.add_argument("--json", type=Path, default=None, help="write the raw results here")
    a = ap.parse_args()
    land = _land()
    results = []
    for seed in range(a.first_seed, a.first_seed + a.runs):
        r = run(seed, a.hours, land)
        results.append(r)
        print(f"seed {seed}: min batt {r['min_batt_permille']}‰, ran out {r['ran_out']}, "
              f"visited {r['visited']}/{r['samples']}, over target {r['over_target']}, "
              f"hazard seen {r['hazard']['seen_s']}, on land {r['on_land']}, swaps {sum(r['swaps'].values())}",
              flush=True)
    text = report(results)
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    if a.json:
        a.json.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
