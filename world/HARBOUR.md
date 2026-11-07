# Water-side launch and 3D harbour repair

Branch: `b/viewer-launch-swap`, based on main `0435058` (includes Alex's #134–136).
These changes are a local development candidate, not a merged release or field validation.

## Changes, in implementation order

1. Integrated the missing coastline routing and water-route battery-return fixes from main.
2. Measured the original spawn row against the bundled coastline: all five centres were on
   land. Replaced it with explicit water-side berths in `world/harbour.json`.
3. Added `world/harbour.py` startup validation: station/fleet match, dock radius, non-overlapping
   hull envelopes and a westbound water corridor. Invalid layouts fail explicitly.
4. Initialised boat headings westward. Kept the land-based radio station and agent home point
   unchanged, so the mission contract and agent's Great Belt routing gate do not change.
5. Modelled moorings: waiting boats cannot drift away from their berth before their first
   powered movement command. Enabled idle boats still draw hotel energy. A returned boat is
   moored during its swap and released by its next powered action. Mooring state is included
   in the physical hash; there are no render-only position offsets or teleports.
6. Shared the berth layout with Three.js; added schematic pontoons, a rising gangway and
   bollards. The harbour camera starts on the seaward side rather than behind the station.
7. Kept meshes life-sized within the harbour view's 500 m station zone. Offshore overview
   enlargement is capped by coastline and neighbour clearance, using a 4 m envelope around
   the illustrative USV mesh. Small crisp markers replace the previous large glow sprites.
8. Added display coastline tests. Where a straight interpolation chord would cross land or
   hull clearance, snap to the newest received truth position instead. Before coast loading,
   use received samples without interpolation. No display-side route or position is invented.
9. Removed the endurance checker's former 150 m quay exception. New checks include the quay.
   The older committed `world/ENDURANCE.md` describes its earlier implementation/run, not
   acceptance evidence for this candidate.

## Geometry assumptions

- The bundled OSM coast and integer-metre projection are approximate, not surveyed navigation
  data. Berths, pontoons, gangway, proxy hull dimensions and clearance are schematic model
  choices, not observations of Korsør's actual harbour infrastructure or a safety certificate.
- Twelve-metre berth spacing and the 4 m hull envelope are validated against the bundled
  proxy mesh/coast. The renderer must not enlarge docked hulls into their neighbours.
- `departure_check_m` validates a potential water-side corridor; it is **not** a new world
  autopilot or prescribed mission route. Actual departures still follow the agents' commands.
- Returning boats use the existing home-radius docking rule; exact berth reservations and
  a collision-avoidance harbour traffic controller are **not** implemented by this change.

## Executed checks

```bash
uv run ruff check world tests/world
uv run pytest -q tests/world tests/agent tests/server tests/smoke
npx --yes pnpm --dir web test
npx --yes pnpm --dir web build
npx --yes pnpm --dir web exec playwright test tests/viewer.spec.ts
uv run python -m world.endurance --runs 1 --hours 12 \
  --out runs/local/harbour-endurance-12h.md \
  --json runs/local/harbour-endurance-12h.json
```

- Targeted Python regression suite: **290 passed**.
- Frontend unit tests: **76 passed**; strict TypeScript + production build passed.
- Viewer browser suite: **3 passed** (live shared feed/offline assets, feed stall, replay of a
  real launch/return/swap/rejoin cycle).
- `tests/world/test_harbour.py` tests swept 4 m hull envelopes every tick through 30 simulated
  minutes for seeds **1, 3, 8**, without a quay exclusion. It checks boat-to-boat envelope
  clearance, mooring energy, startup validation, reset/hash and a real return/swap/rejoin.
- One **12 h, seed 1** run: **241/241** samples visited, **5** battery swaps, no depletion at sea,
  minimum battery at sea **11.2%**, **0** on-land sampled centres including the quay.
  The endurance report samples land every 10 sim-seconds; it is not continuous hull clearance.
  This is one diagnostic seed, not a replacement for the earlier 30-seed evaluation.
- Headless Chromium desktop/mobile-emulation screenshots and runtime checks are stored under
  `runs/local/`. No page exceptions occurred in the inspected launch/overview views. The browser
  lifecycle test also checks that the narrow-screen fleet panel stays below the measured header
  and that the page has no horizontal overflow; this is not real-phone certification.

## Still open: do not label the whole mission accepted

The seed-1 endurance check still has **228** samples whose measured worst gap/final age exceeds
its target; its longest gap is **8 h 47 min** against **3 h 20 min**. The scripted dark contact
was not seen or held. These are unresolved agent/task allocation/scenario acceptance questions,
not cosmetic viewer problems. No metric or scenario was modified to conceal them.

Next acceptance work: investigate the missed-contact timeline and revisit allocation with A;
add explicit dock/launch metadata with C if a per-boat launch queue or berth state is needed;
implement berth reservations/traffic separation if exact docking is required; rerun the
multi-seed batch and selected demo/video; review the candidate and merge it before claiming
that it is available from a clean GitHub checkout. Real-device GPU/mobile and physical offline
acceptance remain separate checks. Repository-wide lint currently reports 12 unrelated errors
in the existing `deck/video/` and `brag-output/work/` files; those files were not changed by this
repair. The scoped `world/` and `tests/world/` lint check passes.
