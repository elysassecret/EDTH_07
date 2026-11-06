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
4. **Panels** — `src/App.tsx`: top bar (UTC clock in Z, sim time, warp, SHORE/TRUTH switch,
   satellite toggle). `src/ui/`: one card per USV and one per contact. Click a card or a symbol
   on the chart to highlight it.

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
| Link cut | red dashed line, red ✕ and "LINK CUT" (grey dashed = link down) |
| Cables | magenta (power) / violet (data); scenario cables thicker |
| Shipping lane | grey dashed (measured from one day of AIS) |
| Box | white dotted |
| Korsør shore station | grey square |

## Files that come from someone else

- `public/geo/land.geojson` — **placeholder, empty on purpose.** Franco's `tools/` should write
  the clipped OSM land polygons here (credit: © OpenStreetMap contributors).
- `public/geo/s2_box.png` + `public/geo/s2_box.json` — Sentinel-2 image and
  `{"coordinates": [[lon,lat] top-left, top-right, bottom-right, bottom-left]}`. Until they exist
  the toggle reads "No satellite image yet".

## Folder map

```text
src/main.tsx        start the connection, render <App/>
src/App.tsx         layout, top bar, banners
src/ui/BoatCard.tsx     feature 18: USV cards (fleet panel)
src/ui/ContactList.tsx  feature 19: contact list (type, seen by, age)
src/store.ts        WebSocket + Zustand store + feed-lost watchdog
src/types.ts        contract types + console extras
src/contract.ts     GENERATED from contract/schema.json
src/format.ts       UTC "Z" time, mm:ss, "2 h 10 min", degrees
src/map/Chart.tsx   MapLibre base + deck.gl layers
src/map/scene.ts    static geometry from data/scene-coordinates.json
src/map/comms.ts    feature 21: comms overlay (toggle "Comms" in the top bar)
src/map/theme.ts    colours (NATO-style: friend blue, neutral green, unknown yellow)
```
