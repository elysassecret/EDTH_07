# Legend text: written once, rendered by C

Owner: D (#89). C renders these rows in `web/src/map/Legend.tsx` (`LEGEND_ROWS`, PR #93). The **Row text** column is the exact string on screen; change it here first, then in `LEGEND_ROWS`. The **Meaning** column is for `deck/OPERATOR_GUIDE.md` and the help overlay, not for the chart.

## On the chart now (PR #93, copied verbatim)

| Key | Row text | Meaning |
|---|---|---|
| `power` | Power cable (ECDIS magenta) | A power cable the boats sweep. Magenta because ECDIS charts draw cables magenta |
| `data` | Data cable | A fibre cable the boats sweep |
| `lane` | Shipping lane | The traffic lane, measured from one real AIS day. No station sits inside 750 m of it |
| `box` | Patrol box | The 25 x 10 km area the five boats guard |
| `usv` | USV, line shows heading | One of our five boats, as last reported to shore |
| `stale` | USV not heard: last known place | Shore has not heard this boat recently. The dot is where it was, not where it is |
| `ais` | Contact with AIS | A ship that broadcasts its identity |
| `dark` | Contact, NO AIS: a cue for a look | A camera contact with no AIS match. A reason to look, nothing more |
| `link` | Radio link · thick: route to shore | Thin: two radios can hear each other. Thick: the path reports take to Korsør |
| `cut` | Link cut | A link that is down. It stays crossed until it comes back |
| `band` | Cable visited: recent · due · over target | Recent: within half the revisit target. Due: past half. Over: past the target (12,000 s, 3 h 20 min) |
| `none` | Cable segment: no visit confirmed | Shore has no confirmed visit for this segment |
| `ghost` | Route a waiting decision proposes | Where a boat would go if you approve the card |

## Proposed rows (not in `LEGEND_ROWS` yet; C decides)

| Key | Row text | Meaning | Source |
|---|---|---|---|
| `depth` | Depth: 0–10 · 10–20 · 20–30 · over 30 m | Shading only, for orientation. The boats do not route by depth | `web/public/geo/depth_bands.geojson` (#89) |
| `detect` | Camera range for a ship by day (5 km) | Inside this ring a boat can see a ship in daylight | `config/boat.toml` `r_detect_m.ship_day`, rings PR #94 |
| `keep` | Keep-in-view range (2 km) | A watching boat must stay this close to hold a contact | `keep_in_view_m` |
| `standoff` | Stand-off ring, 1 nm | Boats stay outside this ring of a NO AIS contact unless you approve a closer look | `standoff_m` |

Ring and depth rows read their numbers from config at render time (PR #94 does this for the rings). If the config changes, the words in brackets must change with it.

## Wording rules

- Say "cue for a look". Never "suspicious", "hostile" or "threat".
- Never "coverage restored". Say how old the oldest visit is.
- Colour is never the only cue: every coloured mark also has a shape, a dash or a word.
