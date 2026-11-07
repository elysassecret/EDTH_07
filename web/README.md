# web/ — shore operator console (owner: C, Alexandru)

What the watch officer sees. A browser page that reads snapshots from the Python server over a
WebSocket and draws them on an offline chart. Only C edits files here.

## Run it (two terminals, from the repo root)

```bash
uv run python -m server.mock_feed      # fake feed on ws://localhost:8765/shore and /truth
pnpm --dir web install && pnpm --dir web dev   # console on http://localhost:5173
```

`?feed=ws://host:port` in the URL points the console at another server.
`pnpm --dir web build` type-checks and writes `web/dist/` (gitignored).

## The 60-second explanation

1. **Data in** — `src/store.ts` opens the WebSocket, keeps the latest snapshot in a Zustand
   store and reconnects by itself (N6). If no snapshot arrives for 2 s it flips to `lost`, and
   the red **FEED LOST — display frozen at hh:mm:ssZ** banner appears (N5). Old data is never
   shown as live.
2. **Types** — `src/contract.ts` is generated from `contract/schema.json` (`pnpm gen:contract`);
   never edit it. `src/types.ts` adds the "console extras" the mock sends that the contract
   does not have yet (heading, trails, decision buttons, …).
3. **Chart** — `src/map/Chart.tsx`. MapLibre draws the static layers (sea, land, 25×10 km box,
   cables, shipping lane) from `data/scene-coordinates.json`, bundled at build time. deck.gl draws
   everything that moves (boats, contacts, trails) and **all text**, so the map style has no
   font or tile URLs: it works with Wi-Fi off (N1).
4. **Panels** — `src/App.tsx`: top bar (UTC clock in Z, sim time, warp with Auto/Pause/1×–240×
   and "slowing for event", SHORE/TRUTH switch, Exercise controls, satellite toggle), then the
   banners (FEED LOST, TRUTH, EXERCISE) and the alert strip. `src/ui/`: decisions, alerts, one
   card per USV and one per contact. Click a card or a symbol on the chart to highlight it.
6. **Evaluator view** (judges and team, off by default) — **Evaluator ON** opens a second socket
   to `/truth` and shows, in purple, where each boat really is next to where the shore last
   heard it, true contacts the shore doesn't have, links where truth and belief differ, and true
   vs shore revisit age (`src/ui/EvalPanel.tsx`, `src/map/evaluator.ts`). Add `?operator` to the
   URL for the watch officer's screen: no evaluator or truth switches.
5. **Over the chart** — the coverage box (oldest cable visit, gap line, all segments) top left,
   the event log bottom left, the exercise injection panel top right.

## Map symbols (colour always paired with shape or words)

| Thing | Look |
|---|---|
| Own USV | blue circle + heading line, number label; grey when stale |
| AIS vessel | green square, name label |
| AIS vessel also on a USV camera | green square + thin yellow ring, "AIS+CAM" |
| Camera-only contact | yellow quatrefoil (four lobes), "NO AIS" label, lines to the USVs that see it |
| Stale contact | grey, at its last known position, "LAST SEEN mm:ss AGO" |
| Course vector | line to where the contact will be in 6 minutes |
| Radio link up | thin blue line between two boats, or boat and Korsør |
| Route to shore | thicker bright blue line from each boat to its next hop (`via`) |
| Decision route | dashed white line to where an open decision would send the boat; brighter while the mouse is on its card |
| Link cut | red dashed line, red ✕ and both ends named, e.g. "USV 01–USV 04 CUT" or "USV 04–shore CUT" (grey dashed = link down) |
| Docked USV | hollow ring and "NN DOCKED" next to Korsør (UNAVAILABLE inside the agents' home radius); card chip DOCKED |
| Cables | magenta (power) / violet (data); scenario cables thicker |
| Shipping lane | grey dashed (measured from one day of AIS) |
| Box | white dotted |
| Korsør shore station | grey square |
| Cable segment age | wide band under the cable: teal within half the target, yellow due, orange (thicker) over target, grey dashed no visit reported; the age is written next to it |
| Alarm / warning / caution | red triangle / orange circle / yellow square, with the word; an alarm flashes until acknowledged |
| EXERCISE | striped yellow banner and EXERCISE tags in the event log and alerts |

## Files that come from someone else

- `public/geo/land.geojson` — **placeholder, empty on purpose.** Franco's `tools/` should write
  the clipped OSM land polygons here (issue #9). Until then the chart says "No coastline file
  yet (issue #9)" in the bottom-right corner.
- Optional, same rules (EPSG:4326 `[lon, lat]`, < ~1 MB): `public/geo/infra.geojson` (lines with
  `{"kind": "bridge" | "ferry" | "pier", "name"}`) and `public/geo/depth.geojson` (lines with
  `{"depth_m"}`). Each file is drawn as soon as it exists; nothing to change in the code.
  A file may carry a top-level `"attribution"` string, shown in the corner; land and infra
  default to "© OpenStreetMap contributors". Loading and checks: `src/map/geo.ts`.
- `public/geo/s2_box.png` + `public/geo/s2_box.json` — Sentinel-2 image and
  `{"coordinates": [[lon,lat] top-left, top-right, bottom-right, bottom-left]}`. Until they exist
  the toggle reads "No satellite image yet".

## Tests

```bash
pnpm --dir web test     # Vitest: src/*.test.ts (e.g. the 5-second UNDO for answers)
```

## Folder map

```text
src/main.tsx        start the connection, render <App/>
src/App.tsx         layout, top bar, banners
src/ui/BoatCard.tsx     feature 18: USV cards (fleet panel)
src/ui/ContactList.tsx  feature 19: contact list (type, seen by, age)
src/ui/DecisionPanel.tsx feature 22: decision cards (Confirm/Stop, Approve/Decline, keys C S A D)
src/ui/AlertPanel.tsx   feature 23: alert list + strip, Acknowledge
src/ui/Coverage.tsx     feature 24: headline number (oldest cable visit, gap open)
src/ui/Demo.tsx         feature 25: warp control, EXERCISE banner, event log, failure injection
src/coverage.ts     segment ages and bands against the revisit target
src/roles.ts        plain role words from task IDs (Cable sweep, Lane picket N, Relay)
src/store.ts        WebSocket + Zustand store + feed-lost watchdog
src/types.ts        contract types + console extras
src/contract.ts     GENERATED from contract/schema.json
src/format.ts       UTC "Z" time, mm:ss, "2 h 10 min", degrees
src/map/Chart.tsx   MapLibre base + deck.gl layers
src/map/scene.ts    static geometry from data/scene-coordinates.json
src/map/comms.ts    feature 21: comms overlay (toggle "Comms" in the top bar)
src/map/theme.ts    colours (NATO-style: friend blue, neutral green, unknown yellow)
```
