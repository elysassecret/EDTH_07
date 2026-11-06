"""Print the story timeline of one run: python -m tools.timeline [mode] [seed] [until_s]"""
import sys
from eval.run_batch import run_one

mode = sys.argv[1] if len(sys.argv) > 1 else "elysa"
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
until = int(sys.argv[3]) if len(sys.argv) > 3 else None
sim, m = run_one(mode, seed, until_s=until, use_ais="--no-ais" not in sys.argv)
rows = []
for b, a in sim.agents.items():
    for t, k, body in a.events:
        if t >= -1 and k not in ("bid",):
            rows.append((t, b, k, body))
for e in sim.shore.events:
    rows.append((e["t"], 0, "shore:" + e["kind"], e["text"]))
for r in sorted(rows, key=lambda r: (r[0], r[1])):
    print(f"{r[0]//1000:6d}s  b{r[1]}  {r[2]:18s} {r[3]}")
print("scorecard:", {k: v for k, v in m.evaluated.items() if k not in ('seg_age_s', 'boat_km', 'radio')})
print("seg ages:", m.evaluated["seg_age_s"])
