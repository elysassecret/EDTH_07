# web/ — shore operator console (owner: C, Alexandru)

What the watch officer sees. A browser page that reads snapshots from the Python server over a
WebSocket and draws them on an offline chart. Only C edits files here.

## Run the integrated console (from the repo root)

```bash
pnpm --dir web install --frozen-lockfile
pnpm --dir web build
uv run python -m server --serve-web    # real simulation and console: http://localhost:8765/
```

A live run lasts 4 h of sim time (`config/run.toml`, ends 14:15Z). For a longer one add
`--hours 7` (at most one full battery: the world has no charging yet, #116).

For development, run `uv run python -m server` and `pnpm --dir web dev` in separate
terminals. The latter serves the console on http://localhost:5173. If pnpm is not
installed, use `npx --yes pnpm` in its place.

`web/template/` remains the standalone design prototype. Its scenarios and synthetic
model are **not imported** by the live application. The integrated layout uses the
same local shadcn components, neutral theme, and bundled Inter fonts, but reads only
the existing store and server protocol. No runtime font, tile, or CDN request is added.

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
4. **Panels** — `src/App.tsx`: fleet / chart / attention layout. `LivePanels.tsx`
   shows delivered boat reports, contacts, dynamic segment ages, selected-object context,
   evaluator comparison and the event timeline. On narrower screens, fleet and attention
   move into sheets so the chart retains its space. Top-bar controls retain pause/warp,
   SHORE/TRUTH and exercise operations; view settings hold comms, display and satellite.
5. **Decisions** — `LiveDecisions.tsx` reviews the actual decision and task revision before
   authorization. Approve/Decline/Stop remain locally undoable for five seconds; Confirm
   sends immediately after review. Feed loss, reset or view changes cancel queued answers.
   Before transmission, the queue rechecks the task revision. A server acknowledgment is
   not a boat delivery or completed observation. Unconfirmed sends are never auto-retried.
6. **Evaluator view** (judges and team, off by default) — **View settings → Evaluator
   comparison** opens a separate `/truth` socket. Purple annotations compare actual and
   delivered positions, contacts, links and revisit ages (`src/map/evaluator.ts`). The
   watch officer's screen is the default (no evaluator or truth switches); add `?evaluator` to
   the URL for the truth view and the comparison, which then starts on.
7. **Tools** — `LiveTools.tsx` retains alerts/acknowledgment, inactivity digest, exercise
   injection, reviewed reset, incident-report downloads and server tamper checks. **Switch
   back on** uses #70's `boat_restore`: same boat and agent, no reset/teleport/recharge.
   A depleted boat stays depleted; new shore reports still require radio delivery.

## Recording the integrated UI (#70 / #76)

Use the existing scenario and narration beats in `server/DEMO.md`, but use the controls
below for this UI. The legacy instruction **A → sending** is no longer the interaction:
review must precede authorization. Restart the Python server after updating code; a
previously running process does not pick up the new restore handler just because the
frontend was rebuilt. This section is an operator runbook, not evidence
that a complete video or a physical two-laptop rehearsal has been recorded.

```bash
pnpm --dir web build
uv run python -m server --serve-web --demo
```

1. Open `http://localhost:8765/`. The real seed-1 demo starts paused at sim
   6900 s / 12:10:00Z. Use **Run** to start; keep Auto for the recording.
2. After the delivered C-07 contact and held close proposal appear, use **Review &
   approve**, or focus that decision card itself and press **A**. On a laptop, open
   **Attention** first. A opens review; it does not send. Esc/Back cancels review.
   You may pause at this beat to allow review time; the network feed remains live.
3. Read the actual boat/task/action. Choose **Authorize & send**. Approve/Decline/Stop
   queue for five real seconds; **Undo queued answer** (or Esc outside a dialog) cancels
   before transmission. Confirm is immediate only after review. A changed task or lost
   feed prevents sending; unconfirmed sends are never retried automatically.
4. Narrate the receipt accurately: server acceptance → **Approved by operator; boat
   delivery not yet confirmed** → **Boat acknowledgment delivered; execution is not
   implied**. If paused, resume after acceptance so the radio can deliver the command.
   Only delivered observations change coverage; receipt is not a completed
   look. Do not narrate a camera image that is not supplied.
5. For a separate restore take, use **Exercise → Exercise boat → Switch off / Switch
   back on**. Resume if paused: injections apply at the next simulation tick. Show the
   labelled event and a newly delivered boat report, not an instant truth-derived card.
   A reviewed simulation reset is a different action, not a restore shortcut.
6. Show remaining gaps and the relay-loss stale-data/reconnect beat; do not cut these
   from the full video. View settings holds comms/display/satellite/evidence. For a
   separate evaluator shot use a non-operator window and enable **Evaluator comparison**;
   scorecards appear only there, with source/seeds and an explicit PRELIMINARY warning
   when supplied. Missing scorecards show a waiting state, never substitute numbers.

Re-time the final full take after choosing the accepted revision. C owns the canonical
`server/DEMO.md` shot list; D verifies feature/video evidence and the release gate.

## Map symbols (colour always paired with shape or words)

| Thing | Look |
|---|---|
| Own USV | blue circle + heading line, number label; grey when stale |
| AIS vessel | green square, name label |
| AIS vessel also on a USV camera | green square + thin yellow ring, "AIS+CAM" |
| Camera-only contact | yellow quatrefoil (four lobes), "NO AIS" label, lines to the USVs that see it |
| Stale contact | grey, at its last known position, "LAST SEEN mm:ss AGO" |
| Could be within | grey dashed circle around a stale boat or moving contact: age × speed since its last report, labelled "USV 02, 03 could be within 2.3 km". Boats use the model cruise speed (`config/boat.toml`, current not included); contacts their last reported speed. Never drawn from truth (`src/uncertainty.ts`) |
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
| Alarm / warning / caution | Explicit severity word and acknowledgment state; alarm uses the destructive alert variant |
| EXERCISE | Explicit EXERCISE banner and event tags, never presented as an observed real incident |

## Files that come from someone else

- `public/geo/land.geojson` — clipped OSM land polygons supplied by Franco's `tools/`.
  If unavailable or empty, the chart reports "No coastline file yet (issue #9)" instead
  of fetching an online basemap.
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
pnpm --dir web test                         # live selectors, queue and transport regressions
pnpm --dir web exec playwright install chromium
pnpm --dir web test:e2e                     # production build + browser checks
```

Browser checks start a separate real `--demo` server on port 18870, paused at 6900 s,
with logging disabled.
Most cases intercept only the WebSocket with explicit protocol fixtures to exercise
review/undo, expiry, feed loss/recovery, provenance, operator mode, responsive sheets
and automated accessibility checks, restore command routing, missing/preliminary evaluator
scorecards, and unconfirmed-answer isolation. Separate cases use the real simulator
handshake and an actual reset/contact/keyboard-review/authorization/delivery/off/restore
flow without protocol interception. The latter uses manual 60× speed for a bounded
regression, not the Auto recording timing or proof of a full video. Tests and Tailwind scanning exclude
`template/`; that prototype keeps its own tests and build.

Coverage remains conservative: the shore protocol encodes missing sample history as
age equal to elapsed simulation time. The UI treats that ambiguous value as unknown,
including at t=0; it cannot distinguish a genuine t=0 visit without a richer report.
Truth data never fills a missing shore age.

## Folder map

```text
src/main.tsx        start the connection, render <App/>
src/App.tsx         layout, top bar, banners
src/components/ui/     shadcn primitives copied from template (not its synthetic model)
src/ui/LivePanels.tsx   fleet, contacts, coverage, selection, evaluator, timeline
src/ui/LiveDecisions.tsx reviewed authorization, undo, command/receipt status
src/ui/LiveTools.tsx    alerts, digest, exercise/reset, reports, connection context
src/console-model.ts   live-data selectors shared by panels and transport guards
src/ui/*.tsx           prior console panels retained for reference; App uses Live*
src/coverage.ts     segment ages and bands against the revisit target
src/uncertainty.ts  "could be within" circles for stale reports (age × speed)
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
