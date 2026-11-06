# Real scene and AIS measurement: Great Belt box, one day of traffic (3 Nov 2026)

Everything labelled "Measured" comes from one file, one Tuesday in November. It is one sample, not a rate. Everything labelled "Estimate" is a rough model with stated assumptions. All traffic figures are aggregates; no vessel is identified and nothing here suggests any vessel did anything wrong.

Short answer for tonight: the idea passes the go/no-go count. A major cable sees 73 to 80 crossings a day, about 3 an hour, which is neither too few nor too many. But almost all are routine ships in one narrow lane, the AIS-dark cue fired zero times, and simply parking boats on the lane beat a fixed patrol by a factor of about six. Pitch "pickets plus filtered cues", not "patrol the routes".

## Which real 25 x 10 km box best matches the scenario?

### Takeaway
Use the Great Belt, in a rotated box from just south of the Great Belt Bridge to just north of the HVDC link. Centre 55.405 N, 10.965 E; long axis on bearing 165 deg. Corners (WGS84): NE 55.52523 N 10.99022 E; NW 55.50195 N 10.83742 E; SW 55.28477 N 10.93978 E; SE 55.30805 N 11.09258 E. No real box has exactly two power cables, one data cable and a lane. This one has one major power cable, one minor power cable, three data lines and the lane.

### Cited Findings
- Measured, box contents: HVDC Storebaelt I 10.0 km inside the box, 60 kV Sprogo-Funen 3.3 km, Great Belt 1 fibre 10.3 km, Great Belt 2 fibre 10.4 km, GC3 fibre 10.4 km, lane 26.0 km — [OSM cables](https://www.openstreetmap.org/way/207775098), [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip)
- Measured, raw distinct identifiers per roughly 25 x 10 km rectangle, all mobile types, same method: Fehmarn Belt at Rodby 152; Oresund at Drogden 106; Oresund at Helsingor 104; chosen Great Belt box 88 (85 vessels after cleaning); Langeland Belt 73; western Smalandsfarvandet 17; one Kattegat rectangle 16 — [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip)
- The Kattegat rectangle was a rough placement and probably missed the lane, so its 16 should be discarded rather than quoted. Its position was chosen before the lane was mapped, and the lane leaves the working region trending north-east — [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip)
- Fehmarn Belt: a submerged tunnel project with working areas affects Route T traffic there, expected to end in 2029 — [DMA Navigation through Danish Waters](https://cdn2.gopublic.dk/soefartsstyrelsen/Media/638743469510433298/Navigation%20through%20Danish%20Water%20version%2016.0%202025.pdf). Fehmarn is also German, so it is not between Danish islands.
- Oresund: multiple data cables exist, but they run Denmark to Sweden, not between Danish islands — [TeleGeography cable geometry](https://www.submarinecablemap.com/api/v3/cable/cable-geo.json)
- Smalandsfarvandet: a real 132 kV cable pair exists, but with only 17 identifiers that day it is too quiet — [OSM way 197799527](https://www.openstreetmap.org/way/197799527)
- The box is wholly inside the mandatory BELTREP reporting area, sector 2 (south of 55 deg 35 min N) — [BELTREP order](https://cdn2.gopublic.dk/soefartsstyrelsen/Media/637787223374336711/Order%20on%20the%20ship%20reporting%20system%20BELTREP%20and%20on%20navigation%20under%20the%20East%20Bridge%20and%20the%20West%20Bridge%20in%20the%20Great%20Belt.pdf)
- Great Belt VTS already uses radar, AIS, infrared cameras and TV cameras in the area — [DMA Navigation through Danish Waters](https://cdn2.gopublic.dk/soefartsstyrelsen/Media/638743469510433298/Navigation%20through%20Danish%20Water%20version%2016.0%202025.pdf)

### Inferences
- An axis-aligned box does not work. The lane runs diagonally, and a 10 km wide north-south box cannot hold it from the bridge to the HVDC crossing. The top automatic score put the lane about 200 m from the box edge at the bridge, so I rejected it and hand-set this box. The lane now stays at least 1.6 km inside the long edges.
- The real geometry differs from the plan's schematic. There the cables run along the long axis with the lane. Here they cut across it, so each cable meets the lane at one point.
- Route length is shorter than the plan's 83 km: 49.6 km for the lane plus three scenario cables (HVDC, 60 kV, Great Belt 1), or 70.4 km with all five lines.
- Expect a judge to know that a VTS watches this water. The defensible angle is close-up visual confirmation near infrastructure, not replacing the VTS.

### Gaps
- Coastline was not fetched because Overpass kept failing, so no water mask exists. The box looks almost all water apart from Sprogo, but the share of land is unmeasured.
- Power cables at Oresund, Kattegat and Fehmarn were not checked for the same reason. The comparison above is a traffic comparison, not a full infrastructure comparison.

## What are the real cable routes in the box?

### Takeaway
All routes are approximate public lines with a few vertices, not surveyed routes. Coordinates are in scene-coordinates.json. Call them "public approximate routes" in front of the jury, and never "actual cable routes".

### Cited Findings
- HVDC Storebaelt I, 400 kV, 600 MW, Energinet: (55.41806, 10.70822), (55.42086, 10.7187), (55.49007, 11.0763), (55.49518, 11.17435), (55.49527, 11.17643). 5 vertices, 31.0 km — [OSM way 207775098](https://www.openstreetmap.org/way/207775098)
- The link has a 32 km sea cable, which agrees with the 31.0 km OSM line — [Wikipedia](https://en.wikipedia.org/wiki/Great_Belt_power_link)
- 60 kV cable, operator tagged Vores Elnet: (55.32901, 10.96396), (55.3285, 10.96373), (55.32173, 10.96095), (55.29434, 10.88527), (55.29304, 10.85484). 8.4 km — [OSM way 991202806](https://www.openstreetmap.org/way/991202806)
- Great Belt 1 fibre, operator tagged Arelion: (55.32495, 10.81591), (55.33775, 10.8773), (55.35249, 10.92027), (55.35559, 11.08874). 18.0 km — [OSM way 1355358824](https://www.openstreetmap.org/way/1355358824)
- Great Belt 2 fibre, operator tagged Telia Denmark: (55.40016, 10.75043), (55.45744, 10.89503), (55.48218, 10.9305), (55.64957, 11.03691). 34.5 km — [OSM way 1355358827](https://www.openstreetmap.org/way/1355358827)
- GlobalConnect 3 fibre, Korsor to Nyborg, 19 km, in service 2006. Schematic 3-point line: (55.32605, 11.14939), (55.33458, 11.02507), (55.32442, 10.79958) — [TeleGeography record](https://www.submarinecablemap.com/api/v3/cable/globalconnect-3-gc3.json)
- Sprogo wind farm, in production since 2009, lies around 55.34 N in the box, with 10 kV cables mapped beside it — [EMODnet wind farms layer](https://ows.emodnet-humanactivities.eu/wfs), [OSM way 210601787](https://www.openstreetmap.org/way/210601787)
- EMODnet's pipeline layer holds an unnamed active line across the Belt at about 55.39 to 55.44 N, drawn as a closed outline, with no name or medium — [EMODnet WFS](https://ows.emodnet-humanactivities.eu/wfs)
- EMODnet cable layers returned no feature in the Great Belt in my query; their features in the wider query area lie further south and east — [EMODnet WFS](https://ows.emodnet-humanactivities.eu/wfs)
- The fibre ways above carry OSM seamark tags, the tagging OpenSeaMap draws on, so OpenSeaMap is not an independent check — [OSM way 1355358824](https://www.openstreetmap.org/way/1355358824)
- Reuse: OSM is ODbL, needing attribution, and share-alike if a derived database is distributed — [OSM copyright](https://www.openstreetmap.org/copyright)

### Inferences
- Plain accuracy statement: no source publishes one. With 5 vertices over 31 km, assume errors of hundreds of metres to about 1 km. That figure is my judgement, not a measurement.
- Great Belt 1 and GC3 both run Nyborg to Korsor. They may be separate cables or may share a corridor; I could not tell. Do not present them as two proven cables.
- The two fibre ways were each created once, on 30 Jan 2025, and I saw no source tag on them, so their provenance is unknown. The HVDC way has 7 versions since 2013.
- For the second "power cable", the honest line is that it is a minor 60 kV cable. It had zero crossings inside the box that day.

### Gaps
- Danish charts, Energinet route maps and the Danish maritime plan were not consulted. The web search budget for this session ran out, so the team can request a follow-up if those are needed.
- The unnamed EMODnet pipeline is unconfirmed. It may be the natural gas line, but I found no source saying so.
- TeleGeography's reuse terms are unverified because the repository link returned 404. Use GC3 as a cross-check only until someone confirms them.

## Where is the lane, and where should the shore station go?

### Takeaway
Measured lane centreline runs from about 55.508 N 10.880 E to 55.301 N 11.048 E, through the East Bridge at about 11.037 E. Use Korsor Naval Station as the real shore site. It sits about 3 km outside the box's east edge, not south-centre, and the plan's one relay at 8 km per hop cannot reach the HVDC crossing from there.

### Cited Findings
- Measured: lane width (P5 to P95 of cargo and tanker vessels) is 0.85 to 1.44 km through most of the box, narrowest at about 0.85 km at the bridge. Lane points are in scene-coordinates.json — [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip)
- Lane meets HVDC at about 55.46213 N, 10.93052 E, and meets Great Belt 1 at about 55.35473 N, 11.03718 E (measured lane, public cable lines) — [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip), [OSM](https://www.openstreetmap.org/way/207775098)
- A traffic separation scheme runs between East Bridge towers 16 and 17, with 65 m free height at mean water level. Ships of 20 m or more must use it, and fishing is banned in its traffic routes — [BELTREP order](https://cdn2.gopublic.dk/soefartsstyrelsen/Media/637787223374336711/Order%20on%20the%20ship%20reporting%20system%20BELTREP%20and%20on%20navigation%20under%20the%20East%20Bridge%20and%20the%20West%20Bridge%20in%20the%20Great%20Belt.pdf)
- West Bridge is limited to ships below 1,000 dwt and below 18 m air draught. Anchoring under both bridges needs a VTS permit — [BELTREP order](https://cdn2.gopublic.dk/soefartsstyrelsen/Media/637787223374336711/Order%20on%20the%20ship%20reporting%20system%20BELTREP%20and%20on%20navigation%20under%20the%20East%20Bridge%20and%20the%20West%20Bridge%20in%20the%20Great%20Belt.pdf)
- Maximum obtainable depth in most of Route T is 17 m — [DMA Navigation through Danish Waters](https://cdn2.gopublic.dk/soefartsstyrelsen/Media/638743469510433298/Navigation%20through%20Danish%20Water%20version%2016.0%202025.pdf)
- Korsor naval base is mapped at about 55.3316 N, 11.1303 E, with a naval harbour beside it — [OSM way 29224838](https://www.openstreetmap.org/way/29224838)
- Radio geometry, calculated at the plan's 8 km per hop (Estimate; Sprogo position is my approximation):

| Shore site | Box within 8 km | With 1 relay (16 km) | With 2 relays (24 km) | Farthest box point | To HVDC x lane | To Great Belt 1 x lane |
|---|---|---|---|---|---|---|
| Korsor naval base | 14.7% | 61.2% | 96.4% | 26.5 km | 19.2 km | 6.4 km |
| Plan's south-centre, placed mid short edge | 29.8% | 62.7% | 94.7% | 25.5 km | 19.2 km | 6.6 km |
| Sprogo, inside box | 48.1% | 81.8% | 100% | 21.2 km | 14.3 km | 4.9 km |

### Inferences
- The south-centre fix does not carry over. It is not a real site here: the point appears to be open water (no coastline data was loaded), and the real long axis runs roughly north-south. Korsor gives almost the same reach.
- From Korsor, the HVDC crossing at 19.2 km needs two relays at 8 km per hop. The plan has one. Options: use Sprogo as a relay mast (subject to access), allow a longer radio range, or keep the northern boats out of shore contact and make that part of the story. That last option fits the scenario's lost-link event.
- The lane bends near 55.37 N, just north of the bridge. Straight-line prediction fails there, which matters for cueing (see the viability section).

### Gaps
- I did not confirm where Great Belt VTS is physically staffed. The order names the Danish VTS authority as operator but gives no site.
- Whether Sprogo can host a station is unknown.

## What does the day's traffic look like in the box?

### Takeaway
Measured: 85 vessels, 321 crossings across all lines, and 73 on the HVDC. Median crossing speed is 11.7 kn, about twice the boats' speed. Only 5 crossings were under 3 kn, none under 1 kn, and 29 were off-lane. There were zero AIS gaps and zero anchored vessels.

### Cited Findings
All figures are measured from the [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip), 3 Nov 2026, after cleaning.

- Vessels entering the box: 85 (84 Class A, 1 Class B). By AIS type: Cargo 36, Tanker 27, Dredging 4, Tug 4, Undefined 4, Passenger 3, Military 2, Other 2, Diving 1, HSC 1, Pilot 1.
- Crossing method: a track segment between fixes at most 30 min apart intersects the public cable line. Same vessel and cable within 15 min counts once (354 raw intersections became 344 events, 321 inside the box).

| Cable | Crossings | Vessels | Speed P5 / P50 / P95 (kn) | Under 3 kn | Under 1 kn | Off-lane over 1 km | Busiest clock hour |
|---|---|---|---|---|---|---|---|
| HVDC Storebaelt I | 73 | 69 | 8.0 / 12.0 / 18.4 | 0 | 0 | 6 | 6 |
| Great Belt 2 fibre | 73 | 69 | 8.0 / 12.1 / 18.4 | 0 | 0 | 6 | 6 |
| Great Belt 1 fibre | 80 | 73 | 3.9 / 11.6 / 18.0 | 2 | 0 | 1 | 11 |
| GC3 fibre (schematic) | 95 | 78 | 4.1 / 11.1 / 18.4 | 3 | 0 | 16 | 10 |
| 60 kV Sprogo-Funen | 0 | 0 | none | 0 | 0 | 0 | 0 |
| All lines | 321 | 80 | 6.0 / 11.7 / 18.4 | 5 | 0 | 29 | 24 |
| Three scenario cables | 153 | 74 | 6.9 / 11.9 / 18.3 | 2 | 0 | 7 | 15 |

- Speed histogram, all crossings: 0 to 1 kn: 0; 1 to 3: 5; 3 to 5: 7; 5 to 8: 26; 8 to 12: 138; 12 to 16: 101; 16 and over: 44.
- Peak: 30 crossings in the busiest 60-minute window, all lines; 24 in the busiest clock hour (hour 13 file time). Quietest clock hour: 5.
- By type: Cargo 150, Tanker 96, Passenger 20, Tug 14, Undefined 12, Other 8, Military 7, Dredging 7, HSC 5, Diving 2. Cargo and tankers are 76.6%.
- Under 3 kn: 5 crossings by 3 vessels, types Tug 3 and Other 2.
- Off-lane: more than 1.0 km from the measured centreline. The cargo and tanker P95 offset is 0.856 km, so 1.0 km is just outside normal lane spread. 29 crossings by 15 vessels (9.0%). Sensitivity: 17.1% over 0.75 km, 2.8% over 1.5 km, 1.2% over 2.0 km.
- AIS gaps over 10 min, previously moving, starting or ending in the box or near a cable: 0. In fact 0 gaps of any kind over 10 min across 61,497 consecutive position pairs touching the box. Longest silence 6.0 min; longest while moving 3.5 min; 2 pairs over 5 min.
- Tracks that start or end inside the box mid-day: 0. Only 1 minute of the day had no rows in the box, so no receiver outage.
- For comparison, the wider region had 357 gaps over 10 min: 151 within 5 km of the box, but only 1 of those moving, and 7 moving within 10 km.
- Stopped or loitering within 500 m of a cable (under 1 kn, at least 10 min): 2 episodes, 2 vessels, 7.6 vessel-hours. Neither was a cargo ship or tanker, and both also lasted over 30 min. AIS gives no reason for a stop, so nothing should be inferred about either vessel.
- Stopped anywhere in the box: 23 episodes, 8 vessels, 38.9 vessel-hours. Episodes by type: Tug 8, Other 5, Dredging 4, HSC 3, Undefined 2, Diving 1. No cargo or tanker.
- Anchored: 0 rows with status At anchor in the box. In the wider region, 4 vessels, none within 500 m of a cable, 2 within 2 km.
- Stopped positions are not concentrated on cables: 6.6% of stopped rows lie within 500 m of a cable, while 16.7% of the box area does.

### Inferences
- The 321 total counts lines, not ships. Most lane ships cross four lines in one passage. About 73 to 80 passages a day is the better number to quote. HVDC and Great Belt 2 have the same count because their lines meet right beside the lane.
- Extrapolating one day to a year gives about 26,600 passages (Estimate, from one sample). An [unverified trading-guide site](https://ballast-markets-seo.pages.dev/chokepoints/danish-straits) says 20,000+ a year, the same order but a weak source. The official source publishes yearly figures only as charts I could not read — [DMA transit routes](https://www.dma.dk/safety-at-sea/navigational-information/ais-data/transit-routes)
- Are anchored vessels near cables normal? On this day, no: none in the box. That makes anchoring near a cable a meaningful flag, but one day cannot prove it. The VTS allocates anchorages shown on charts, so a useful rule is anchoring outside those anchorages — [BELTREP order](https://cdn2.gopublic.dk/soefartsstyrelsen/Media/637787223374336711/Order%20on%20the%20ship%20reporting%20system%20BELTREP%20and%20on%20navigation%20under%20the%20East%20Bridge%20and%20the%20West%20Bridge%20in%20the%20Great%20Belt.pdf)
- Zero gaps does not mean dark vessels are absent. A vessel with no AIS produces no rows at all, so AIS cannot count it. It does mean the demo's dark event must stay synthetic, as the plan already says.
- GC3's 16 off-lane crossings cluster in the East Channel near the bridge, between 8.4 and 9.5 km along the box, on both sides of the lane centreline. Since that line is schematic, treat its count as the least reliable.

### Gaps
- One Tuesday in November. Pleasure craft are near their yearly low (1 Class B vessel in the box), so summer counts of slow and off-lane crossings could be much higher. Run another day or a summer day before quoting a rate.
- Weather that day is unknown, and it may drive anchoring.
- Small boats without AIS are invisible in all of these counts.

## Is "patrol the ships" viable for five boats at 3 m/s?

### Takeaway
Yes, as pickets plus filtered cues. Estimate: fixed route patrol saw about 11% of crossings, parked lane pickets 65%, and cueing on every crossing 95%. Cueing only the filtered list kept 71% of all crossings and caught 8 of 9 filtered ones with 22 tasks a day and a 10-minute lead. Longer lead made this worse.

### Cited Findings
ESTIMATE, not a measurement or a validated model. Real crossings of 3 Nov 2026 from the [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip). "Seen" means a boat is within 500 m of the crossing point at the crossing instant.

Assumptions: 3 m/s; 500 m camera; 30 s time step; straight lines ignoring land, bridge, wind, current and collision avoidance; no battery limit over 24 h although real boats last 6 to 8 h; boats share cues instantly; 4 responding boats plus 1 relay parked at box centre; AIS reception 15 km per boat; prediction is constant course and speed from pings up to time t only; cue valid for 180 s; nearest feasible boat is assigned; a boat that cannot arrive in time is not sent; free boats return to home points where the lane meets each cable. Those home points use the lane measured on the same day, so "no hindsight" below means no knowledge of individual crossings, not no knowledge of the lane.

Three scenario cables: 153 crossings, 9 filtered (slow under 3 kn or off-lane over 1 km).

| Method | All crossings seen | Filtered seen | Tasks a day | km per responder | Busy share |
|---|---|---|---|---|---|
| (a) Fixed route patrol, mean of 200 random starts | 11.1% (P5 to P95: 6.5 to 15.7%) | 9.3% mean (0 to 33%) | none | 259 (always moving, arithmetic) | n/a |
| Parked at 2 lane points, no hindsight | 64.7% | 0 of 9 | none | 0 | n/a |
| Parked at 4 best points, using that same day (hindsight limit) | 92.8% | 6 of 9 | none | 0 | n/a |
| (b) Cue every crossing, 20 min lead | 94.8% | 7 of 9 | 155 | 60.7 | 40.8% |
| (b) Cue filtered, 10 min lead | 71.2% | 8 of 9 | 22 | 8.7 | 2.0% |
| (b) Cue filtered, 20 min lead | 62.1% | 9 of 9 | 93 | 42.3 | 11.9% |
| (b) Cue filtered, 30 min lead | 57.5% | 9 of 9 | 128 | 68.3 | 22.9% |

All five lines: 321 crossings, 33 filtered.

| Method | All crossings seen | Filtered seen | Tasks a day | km per responder | Busy share |
|---|---|---|---|---|---|
| (a) Fixed route patrol | 7.2% (4.7 to 9.7%) | 2.5% mean (0 to 9.1%) | none | 259 (always moving, arithmetic) | n/a |
| Parked at lane points, no hindsight | 61.4% | 0 of 33 | none | 0 | n/a |
| Parked at 4 best points (hindsight limit) | 66.0% | 0 of 33 | none | 0 | n/a |
| (b) Cue every crossing, 20 min lead | 81.9% | 18 of 33 | 293 | 121.8 | 65.9% |
| (b) Cue filtered, 10 min lead | 66.7% | 20 of 33 | 58 | 21.6 | 4.9% |
| (b) Cue filtered, 20 min lead | 46.7% | 22 of 33 | 195 | 91.4 | 25.1% |
| (b) Cue filtered, 30 min lead | 32.4% | 23 of 33 | 254 | 139.3 | 45.6% |

- Reception range barely matters: 8, 15 and 25 km at 20 min lead gave 62.1%, 62.1%, 62.1% (scenario, filtered mode) and 47 to 48% on all lines.
- Five 500 m camera circles cover 1.57% of the 250 square km box, which is why open-water patrol sees so little.
- Plain arithmetic (Estimate): four boats at 3 m/s sweep 49.6 km in about 69 min with no transit, against about 115 min for the plan's 83 km.

### Inferences
- The go/no-go test passes. Traffic is enough to show a result and does not overwhelm five boats, because it concentrates in a corridor about 1 km wide.
- A fixed route patrol is the weakest option by a wide margin. If the demo shows only route revisit, a sharp judge can point out that two parked boats do far better for watching crossings. Use "parked at lane points" as a third baseline.
- Boats cannot chase. Median ship speed of 11.7 kn is about 6 m/s, twice the boats' speed. They must be ahead of a ship, which is why prediction is the core of this idea.
- Lead time is a real trade-off. Tasks grow from 22 to 93 as lead goes from 10 to 20 min, against 9 real events, and coverage of ordinary crossings falls. Straight-line prediction around the lane bend creates false off-lane cues. Following the lane instead of a straight line is a sensible, testable improvement. I did not test it.
- Filtered results rest on 9 and 33 events, so differences of one or two events mean nothing.
- Do not present these as probabilities of catching a bad actor. No malicious behaviour is in this data.

### Gaps
- No land or bridge avoidance, no battery swaps, no radio limits in the cue path, and only one day. The cue-share assumption conflicts with the radio findings above for northern boats.
- Parked pickets only stay parked in calm conditions. Station-keeping in Great Belt currents is unmodelled.

## Does the cue list need narrowing, and to what?

### Takeaway
Yes. Use: predicted crossing at under 3 kn, or more than 1 km off the lane centreline, or stopped within 500 m of a cable for 10 minutes or more, or AIS lost near a cable, or a cable-owner alarm. That gives 9 crossings a day on the three scenario cables and 33 on all five lines, plus 2 stop events.

### Cited Findings
All measured from the [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip).

| Filter | Crossings a day | Vessels |
|---|---|---|
| All lines, no filter | 321 | 80 |
| Under 3 kn | 5 | 3 |
| Under 1 kn | 0 | 0 |
| Off-lane over 1 km | 29 | 15 |
| Under 3 kn or off-lane (recommended) | 33 | 15 |
| Same, excluding pleasure, sailing, SAR, pilot, law enforcement and military | 29 | 13 |
| Recommended filter, three scenario cables only | 9 | 9 |

- Recommended filter by line: GC3 18, HVDC 6, Great Belt 2 6, Great Belt 1 3, 60 kV 0.
- Recommended filter by type: Tug 10, Cargo 4, Military 4, HSC 3, Dredging 3, Other 3, Diving 2, Passenger 2, Tanker 2.
- Busiest clock hour for the recommended filter: 7 on all lines.
- AIS lost near a cable: 0. Stopped within 500 m of a cable: 2 episodes.

### Inferences
- 33 a day averages 1.4 an hour and 9 a day averages 0.4 an hour (arithmetic). Both are workable for one operator.
- Real task load is higher than the event count: 22 tasks at 10 min lead for 9 events (Estimate), because of false starts. Quote both numbers.
- 27 of the 33 filtered crossings are by types other than cargo and tanker, so expect many benign alerts. The value is a boat confirming visually and an operator clearing it, not an accusation. Use the wording "cue for a look", not "suspicious".
- An "under 1 kn" crossing rule alone would have fired zero times. It is too strict to demonstrate with this data.
- Use a 10-minute lead as the default.

### Gaps
- Thresholds were set from this same day, so they are not validated on other data.
- Cable-owner fault alarms cannot be tested from AIS.

## What does the AIS file contain, and how fast does it parse?

### Takeaway
A single 3.36 GB CSV of 18,616,857 rows. Full streaming took about 7 minutes here, but tonight the team needs only the 6.9 MB clip, which loaded in 0.08 s with pandas. If you touch the raw file, deduplicate first: 44% of rows are exact duplicates.

### Cited Findings
- 26 columns: # Timestamp, Type of mobile, MMSI, Latitude, Longitude, Navigational status, ROT, SOG, COG, Heading, IMO, Callsign, Name, Ship type, Cargo type, Width, Length, Type of position fixing device, Draught, Destination, ETA, Data source type, A, B, C, D — [AIS README](http://aisdata.ais.dk.s3.eu-central-1.amazonaws.com/!_README_information_CSV_files.txt)
- The README's timestamp comes from the AIS base station, formatted 31/12/2015 23:59:59, and it states no time zone — [AIS README](http://aisdata.ais.dk.s3.eu-central-1.amazonaws.com/!_README_information_CSV_files.txt)
- Measured: zip 624,618,400 bytes, CSV 3,358,665,270 bytes. Timestamps 03/11/2026 00:00:00 to 23:59:58, in order. Rows per clock hour 636,260 to 897,986 — [AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip)
- Measured, rows and distinct MMSI by type of mobile: Class A 16,176,533 / 2,501; Base Station 1,306,823 / 64; Class B 605,690 / 1,489; AtoN 518,429 / 209; SAR Airborne 9,340 / 14; SAR Transponder 27 / 4; Emergency PIRB 15 / 5. Total distinct 3,806. Data source type is always AIS.
- Measured quality: exact duplicates 8,182,559 (44.0%); bad positions 34,874; rows without a 9-digit MMSI 1,409,347. Blank SOG 10.2%, COG 14.9%, Heading 22.3%, ROT 31.9%, dimensions 12.2%, Draught 28.1%. These shares include base stations and AtoN.
- Measured: ship type Undefined 12.5%; navigational status Unknown value 17.9%. Some statuses have raw labels such as "Reserved for future amendment [HSC]".
- Measured, working region (55.00 to 55.95 N, 10.45 to 11.45 E): 1,490,617 rows. Class A and B 1,371,970, falling to 522,634 after exact dedupe (61.9% removed), then 520,843 by vessel and timestamp. One 4-digit MMSI (9,080 rows) and 10 position jumps over 60 kn were removed. 240 vessels; none had conflicting ship types. Cleaned rows: SOG blank 0.08%, COG blank 8.85%.
- Measured, reporting interval while moving at 2 kn or more: Class A median 9 s, P99 21 s; Class B median 30 s, P99 155 s.
- Measured timings, this laptop (12 logical CPUs, Python 3.14.3, pandas 3.0.5): download 433 s; full stream with all counters 423.2 s (about 44,000 rows/s); regional clean 10.4 s; crossings, gaps and loiter 1.6 s; clip 1.2 s; estimate 12.6 s.
- Terms: the data may not be combined with other data so that persons become identifiable, and correctness is not guaranteed. The policy page states no attribution requirement — [DMA AIS policy](https://www.dma.dk/safety-at-sea/navigational-information/ais-data/ais-data-management-policy)
- AIS only shows AIS-equipped ships and can hold errors from ships' own instruments — [DMA AIS page](https://www.dma.dk/safety-at-sea/navigational-information/ais-data)

Clip for replay, ais-clip-box.csv:
- Date 2026-11-03. Rows inside the rotated box only. 61,408 rows, 85 vessels, 6,947,226 bytes. Sorted by time.
- Columns: ts_file, vessel_hash, lat, lon, sog_kn, cog_deg, heading_deg, nav_status, ship_type, ais_class, length_band_m.
- Time zone: ts_file is the file's timestamp, reformatted to ISO. The zone is not stated by the source. Treat it as UTC, unverified (CET would shift hour labels by one, not counts).
- Thinning: none needed, as it is under 20 MB. Duplicates are removed, so reporting intervals are the real ones.
- Privacy: MMSI is the first 12 hex characters of a salted SHA-256; the random salt was discarded after the run and never saved. No name, call sign, IMO, destination or draught. Length is floored to 25 m bands.
- Keep the clip inside the team. Rare type and length combinations could still narrow a vessel down.

Raw data status: after these outputs were saved, the ais-data directory (the zip, belt_region.csv, belt_clean.pkl, crossings.pkl and profile files, 866 MB) was moved out of the scratchpad to the Windows Recycle Bin. It was not permanently deleted, because the assistant's safety rules forbid hard-deleting files even on request. Emptying the Recycle Bin finishes the deletion and needs to be done by Franciszek. Until then, the raw file with vessel identifiers stays recoverable on this laptop.

### Inferences
- Any new parser must drop base stations and AtoN, deduplicate, then sort by vessel and time. Skipping dedupe would nearly double row counts and break any speed derived from fixes.
- Feed the clip to boats only within modelled reception range, as the plan requires.
- The team does not need the 625 MB file tonight.

### Gaps
- Time zone remains unverified. The README is silent, and I found no direct test in the time available.
- Other days were not downloaded, by design. The bucket lists 1, 2 and 3 Nov 2026 for this month.
- Search and data limits: the session's web search budget ran out midway, and Overpass was overloaded, so OSM seamark traffic routes, anchorage areas and coastline were not retrieved. The lane therefore comes from AIS plus the BELTREP order, not from charted routes.
