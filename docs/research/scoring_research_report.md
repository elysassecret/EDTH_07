# Measure the gap, not the swarm

Elysa's Secret should stop selling coordination and sell one measured answer that no public source gives: when a boat dies or an alert pulls a boat away, how much cable goes unwatched, and where does the gap land? The plan scores about **34/70 today and about 50/70 with the changes below (estimate)**, and **9 of those 16 points come from the three business criteria** that the current pitch gives no time. Build on the real Great Belt box, because testing the plan there overturned three working assumptions: the 16,800 s run overruns the return limit, sweeping all 49.6 km brings the near-tie back (18,860 s vs 18,760 s), and the 64.7% "parked" figure only works with a boat sitting in the middle of a traffic lane. The fix is EDTH's own 2+2+1 read literally: two lane watchers hold pickets 1.5 km west of the lane, two scouts sweep 23.5 km of cable, and one boat relays. In a rough model that cuts cable overdue at end of run from **7.2 km to 0.5 km**, but it moves the gap rather than closing it, because lane crossings in camera view fall from 13 to 5 of 19, and that trade is the honest story to tell. The go/no-go test for idea 1 **passed on count**, in changed form: pickets plus filtered cues, not route patrol. Use 2.3 m/s, a Korsør mast with a 14 km link and one relay boat west of the lane, and cut the radios and the drone. The deck is due Sunday noon with the video linked inside it, so results land by 09:00, video by 10:30 and upload by 11:30.

**How to read the numbers.** [Measured] comes from the 3 November AIS file or a fetched document. [Estimate] is the earlier rough model in the AIS notes. [Scratch model] is a throwaway model run for this report on the real scene: instant auctions, no radio, no land, 20 random phases. It is not project code and not a result the team may quote as achieved. [Own calculation] is arithmetic from stated inputs. [Judgement] has no source. The scratch scripts are in `C:\Users\franc\AppData\Local\Temp\claude\472a0e765c674616\5a7ba5d4-21c3-47e6-850a-2271ddf60119\scratchpad\scene2\`. They reproduced the earlier cue result exactly (71.2%, 8 of 9, 22 tasks, 8.7 km) and the 153 crossings, so the comparisons below rest on the same base.

## The verdict: 34 today, 50 with the changes, and most of the gain is not code

Five to seven jurors each score seven criteria from 0 to 10, the sum guides a debate, and the highest total does not automatically win (Onboarding PDF p.4). Figures are a per-juror average out of 70. **All are my estimates.** No juror score sheet is public.

| Criterion | Today (plan as written) | P0 only | P0 + P1 | What moves it |
|---|---|---|---|---|
| Relevant problem | 7 | 8 | 9 | Undersea protection is a named 2026 track; a Helsinki court ruled on 5 Nov; Sweden contracted in October |
| Feasibility | 6 | 7 | 7 | Real scene, real AIS, a stated real-versus-modelled line. Capped by no hull and no radio |
| Originality | 4 | 6 | 7 | Failure scorecard, alert-to-boat last mile, AIS-on cue |
| Mass-manufacturability | 3 | 6 | 6 | Retrofit box on ArduPilot, EMS build. Deck work |
| Business opportunity | 4 | 6 | 7 | Named contracts, per-boat licence, a price tested on a mentor |
| Size of opportunity | 3 | 5 | 6 | USD 3.9bn frame, plus the admission that Baltic licensing alone is single-digit EUR millions |
| Pitch | 7 | 7 | 8 | Story, 50 seconds for the scored business material, ten rehearsals |
| **Total** | **34** | **45** | **50** | |

The handoff's 34 stands. Its 51 becomes **about 50 (45 if only P0 ships, plausible range 45 to 55)**, which is the same answer within any honest error, but the route to it changes. Mass-manufacturability, business and size supply +9 of the +16, and they need about six hours of owner D's time, not code. Saturday afternoon's deck draft is worth more points than any single module.

Three things cap the score. No simulated swarm has a direct EDTH podium precedent, although multi-agent software has placed three times, including third at Copenhagen 2024 for a DTU student team ([EDTH recap](https://eurodefense.tech/copenhagen-defense-tech-hackathon/)). Passive detection is listed first among this year's tracks ([EDTH event page](https://events.eurodefense.tech/copenhagen-2026)), and acoustic teams took first and second at Copenhagen 2025 ([EDTH recap](https://eurodefense.tech/copenhagen-defense-tech-hackathon-2025/)). And the size criterion asks about a multi-billion market, while a Baltic-only licence business comes out at single-digit EUR millions on the team's own bottom-up estimate.

## The sharpest honest claim is a number nobody publishes

**Say this:** "Detection is already sold. We measure what happens next. When a boat dies or an alert takes a boat off the cable, we show how many kilometres go unwatched, where the gap lands and who chose that, on real Great Belt traffic. In public sources we found, nobody publishes those numbers."

Two openings support it. The first is the last mile: Windward's cable pages offer alerts, satellite tasking and C2 integration, with no tasking of drones, USVs or crews ([Windward](https://windward.ai/solutions/maritime-infrastructure/)), and no source reviewed shows a cable-risk alert tasking an uncrewed boat. The second is failure in numbers: Shield AI's release does not address re-tasking after failure ([Shield AI](https://shield.ai/shield-ai-and-thunder-tiger-complete-hiveminds-first-multi-asset-autonomous-maritime-teaming-demonstration-in-taiwan/)), the Task Force X account omits failure rates and metrics ([NATO Innovation Network](https://natoinnovation.network/2026/03/11/task-force-x/)), and the REPMUS 2026 outcome is unpublished ([Brussels Times](https://www.brusselstimes.com/2354255/nato-maritime-exercise-tests-300-drones-in-push-for-uncrewed-supremacy)). The candid reporting that does exist comes from US sources and names integration, station-keeping and software failures rather than clever allocation ([DefenseScoop](https://defensescoop.com/2024/01/19/navy-usv-inappropriate-interactions/)).

The scratch model adds the insight the pitch was missing: **with fewer boats you cannot close the gap, only choose where it lands.** Repair returns about 6.7 km of cable and gives up 8 of 19 lane crossings in view. AIS still hears those 19 ships, and nothing else watches a dark vessel on the cable, so "cables before lane" is the right default. A watch officer approves that priority in the standing orders, so the fleet is not improvising a policy.

**Avoid these.** "One boat keeps the contact while the other resumes" is not new: Hivemind showed it with two boats on real water in 2026 ([Baird Maritime](https://www.bairdmaritime.com/security/naval/unmanned-naval-systems/shield-ai-kraken-usv-mission)). AIS anomaly detection is common hackathon work, some of it already with ESP32 mesh and LLM threat cards ([HORMUZ WATCH](https://maritimedefensecop.netlify.app), [ENSTA](https://ensta.fr/en/accueil/news/artificial-intelligence-service-sailors-spasea-hackathon)). Do not say "first", "we detect dark ships", "early warning from cable alarms", "they are centralised", "no radio traffic", "court-ready", "tamper-proof", "blockchain", "one operator can run five boats", "prevents", "hostile" or "suspicious". Do not say "sabotage" unless quoting a court, and then add "not final". Most Baltic outages since 2022 were reported as civilian anchor drags ([Reuters via Insurance Journal](https://www.insurancejournal.com/news/international/2025/02/24/813202.htm)), and a dragged anchor costs the same either way.

Make the honest turn yourself. The brief's dark loiterer is not the historic signature: the real pattern is a ship under way, usually with AIS on, slowing as an anchor drags, first noticed by the cable owner, with only one case of a reported AIS gap ([Wikipedia](https://en.wikipedia.org/wiki/2024_Baltic_Sea_submarine_cable_disruptions)). Say so, and show the AIS-on cue beside the synthetic dark event.

## What must change in the plan

### Eight conflicts, one decision each

**1. Scene: build on the real Great Belt box, and stop quoting every 83 km figure.** The schematic's 14,400 s near-tie (18,180 s vs 17,620 s), its corridor results and its 16,800 s recommendation all belong to a not-to-scale drawing with two parallel power cables 773 to 905 m apart. The real box has cables that cross the lane, a 60 kV cable that nothing crossed, and no parallel pair, so **the "corridor" merge has nothing to merge and is dropped**. The line lengths are lane 26.0 km, HVDC 10.0, Great Belt 1 10.3 and 60 kV 3.3, totalling 49.6 km ([real_scene_and_ais.md](../research_notes/Challenge%2007%20scoring%20research/real_scene_and_ais.md), [OSM](https://www.openstreetmap.org/way/207775098)). The cycle-time bid, rebalance rule and km-overdue metric survive because they do not depend on the old geometry.

| Real box numbers | 2.3 m/s | 3.0 m/s | Basis |
|---|---|---|---|
| One sweep of 49.6 km by 4 boats, no transit | 90 min | 69 min | [Own calculation] |
| Return rule fires for a boat at the far HVDC end (21.3 km from Korsør) | **14,140 s** | **16,300 s** | 25,200 − 1,800 − travel, [Own calculation] |
| All lines swept: worst age, repair off vs on, 14,400 s | 18,860 vs 18,760 (0.5%) | 15,720 vs 14,120 (10%) | [Scratch model] |
| All lines swept: km over 2 h, off vs on | 20.1 vs **28.4** | 14.2 vs **21.0** | [Scratch model] |
| Pickets plus cable sweep: worst age, off vs on, 14,400 s | 18,360 vs 15,440 (16%) | 15,260 vs 12,580 (18%) | [Scratch model] |
| Pickets plus cable sweep: cable km overdue at end, off vs on | 7.2 (3.5 to 9.2) vs 0.5 (0 to 3.1) | 3.9 (2.1 to 7.8) vs 0.0 (0 to 2.8) | Target 12,000 s, [Scratch model] |
| Pre-event worst age | 11,880 s | 9,100 s | Set by the Great Belt 1 plus 60 kV tour, [Scratch model] |

Three decisions follow. **Keep the handoff's 14,400 s with events at about 7,200 s**, and overturn the technical notes' 16,800 s: it overruns the return limit at both speeds and is no longer needed, because the modes separate at 14,400 s once the lane boats picket. Evaluate at 14,000 s so a late return cannot contaminate the comparison. **Do not sweep the lane**: two boats across 49 km do not close a gap, they spread it, and repair then looks worse than doing nothing on km overdue. **Set the revisit target at 12,000 s as a first value** (just above the pre-event worst, so nothing is overdue before the failures), then confirm it. Re-measure Friday night in step 9: pre-event worst age per boat, return limit per boat, the radio graph at the real stations, and a chart check that every station is water.

**2. Shore and radio: Korsør mast, 14 km link, one relay boat west of the lane, peers as extra hops.** South-centre is dropped: it appears to be open water and gives almost the same reach as Korsør. Korsør is a real site, with the naval base mapped at 55.3316 N, 11.1303 E ([OSM](https://www.openstreetmap.org/way/29224838)), and it closes a gap in the AIS notes because Great Belt VTS sits at Naval Base Korsør under the call sign BELT TRAFFIC ([Danish Defence](https://forsvaret.dk/da/organisation/soevaernet/civile-opgaver/beltrep)). Two 8 km hops miss the HVDC crossing at 19.2 km. The technical notes' 12 km link plus one 8 km hop reaches 20 km in a straight line, but the north picket sits 19.9 km from Korsør, and an east-side relay inside 12 km comes out 8.1 km from it, beyond boat range. Staying west of the lane also means no relay handover has to cross it.

So **raise the shore link to 14 km** and park the relay at about **55.405 N, 10.975 E**, 1.1 km west of the lane centreline. It sits 12.8 km from the mast, 7.2 km from the north picket, 6.1 km from the south picket, and 7.4 km from a boat holding the contact at stand-off [Own calculation]. In the same two-ray model the notes use, a 10 m mast to a 2 m boat at 14 km costs 139.9 dB, which is 4.2 dB easier than 8 km boat-to-boat (144.1 dB) and inside the 18.9 km horizon [Own calculation]. That is a modelled assumption, with no measured over-water range behind it. Label it "narrowband or licensed link, low data rate": it carries tracks and task records, not video. Boats beyond 8 km of the relay, such as the HVDC west end at 8.6 km or the far 60 kV end at 11.0 km, hop through a peer (four hops allowed) or store and forward, and the screen shows that as it is. Boats in the south have a real direct shore link, which finally gives the event something to cut: boat 04 at the south picket is 7.8 km from Korsør. The 4 km boat-hop sensitivity will cut the north off from shore; show that as isolation. Ask whether a Sprogø or bridge mast is possible, but do not plan on it.

**3. Baselines and headline: three modes, one gap metric, and retire "parked saw 64.7%".** A sharp juror will ask why patrol at all, and the answer starts with correcting our own number. The 64.7% came from boats parked **on the lane centreline**, inside a traffic separation route where ships of 20 m or more are required to run ([BELTREP order](https://cdn2.gopublic.dk/soefartsstyrelsen/Media/637787223374336711/Order%20on%20the%20ship%20reporting%20system%20BELTREP%20and%20on%20navigation%20under%20the%20East%20Bridge%20and%20the%20West%20Bridge%20in%20the%20Great%20Belt.pdf)). Nobody would station a 2 m boat there. Move the same pickets out and the figures change:

| Setup (3 scenario cables, 153 crossings, 9 filtered, one day) | Verification look ≤500 m, all | Filtered ≤500 m | In view ≤2 km, all | Filtered ≤2 km | Cue tasks a day | Basis |
|---|---|---|---|---|---|---|
| Fixed route patrol, 3 m/s | 11.1% | 9.3% mean | not computed | not computed | 0 | [Estimate] |
| Parked in the lane, no cues | 64.7% | 0 | 99.3% | 8 | 0 | [Estimate], [Scratch model] for ≤2 km |
| In the lane, 4 responders, cues, 3.0 m/s | 71.2% | 8 | 99.3% | 8 | 22 | [Estimate] reproduced |
| In the lane, 4 responders, cues, 2.3 m/s | 70.6% | 7 | 99.3% | 8 | 20 | [Scratch model] |
| **Two pickets 1.5 km west, parked** | 3.3% | 5 | 93.5% | 7 | 0 | [Scratch model] |
| **Two pickets 1.5 km west, cues, either speed** | 5.2% | 7 | 93.5% | 7 | 13 | [Scratch model] |
| Two pickets 1.5 km east, parked | 0.7% | 1 | 71.2% | 2 | 0 | [Scratch model] |
| Two pickets 1.5 km east, cues, 3.0 m/s | 1.3% | 2 | 71.2% | 2 | 13 | [Scratch model] |

Read this table carefully. West beats east because the off-lane ships that day went west, so the side was chosen with hindsight on the same day. Cues add 2 events over well-placed pickets (5 to 7 of 9), which is inside the noise on 9 events, so **do not headline cue gain**. The cue's value is that an alert becomes one boat's job with a measured patrol cost, not a statistical uplift. The lead-time result stands: 10 minutes gave 13 tasks and 7 looks, while 20 minutes gave 64 tasks and 6.

The honest reason to sweep is that AIS already names the ships in the lane: every one of the 153 crossings is in the file, and results did not change between 8 and 25 km reception. A parked boat adds a camera view of ships AIS has already named, and sees nothing on the 19.5 km of cable outside its circles. Sweeps exist for what AIS cannot name: the dark, the unlit and the off-lane. So read the brief literally: **lane watchers picket, cable scouts sweep, the relay relays.** Lane samples leave the revisit count, and the 23.5 km of cable stays in it.

Compare three modes on identical inputs:

| Mode | Cable km overdue at end (of 23.5, 2.3 m/s) | Worst revisit age | Lane crossings in view after first event (of 19) |
|---|---|---|---|
| Static pickets, no sweeps | 19.5 from the start [Own calculation] | Whole run | 15 |
| Sweep plus pickets, repair off | 7.2 (3.5 to 9.2) | 18,360 s | 13 |
| Elysa: repair, cables before lane | 0.5 (0 to 3.1) | 15,440 s | 5 |

All except the first row are [Scratch model] for the 10:15 to 14:15 AIS window. **Headline: cable kilometres overdue at end of run**, because it is EDTH's "keep the gap in coverage as small as possible" in one number and it separates modes where worst age barely moves. **Always show lane crossings in view beside it**, because a headline without its cost would be the dishonest version. Support with time from event to all cable segments owned, worst revisit age, time from loiter start to first detection, and watch-officer decisions per hour. Keep the manual-operator run as one labelled extra.

**4. Boat speed: 2.3 m/s as the build default, 3.0 m/s as the sensitivity run.** This overturns the technical notes' "keep 3 m/s". The brief gives no speed. The Otter's maker states 4.5 kn ([Maritime Robotics](https://www.maritimerobotics.com/otter)), one listing says 6 kn, and the 1.2 m BlueBoat claims 3 m/s unloaded ([Blue Robotics](https://bluerobotics.com/store/boat/blueboat/blueboat/)). Published range per charge is about 65 to 74 km at low speed, so 3 m/s for 7 h (75.6 km) is the optimistic edge, while 2.3 m/s (58 km) sits inside it. The change costs less than expected: sweeps take 30% longer, the return limit drops to 14,140 s, the ship-to-boat speed ratio goes from 2:1 to 2.6:1, "cannot hold" starts at 4.5 kn, and pre-event worst age rises from 9,100 s to 11,880 s. From legal pickets it changes cue results **not at all** on this day, because the ships come to the pickets. Neither speed can stay with a ship at the 7 to 7.6 kn seen in real drags, so keep the demo contact slow and say so.

**5. Detection: two radii, and the old crossing numbers get relabelled.** Keep `r_verify` = 500 m, the range at which a boat can read a name or check an anchor (pixel geometry gives 183 to 550 m). Add `r_detect` as a value per contact class: 5,000 m ship by day, 1,500 m small craft by day, 500 m unlit at night, all [Judgement]. **The fixed script uses 2,000 m**, a dusk low-contrast class that agrees with the operations notes' synthetic detect range, the 1,852 m stand-off and the 2,000 m keep-in-view radius. Visit credit uses only `r_verify`. Run the scorecard at 500, 2,000 and 5,000 m and show the curve.

The crossing estimates used 500 m, so **rename "seen" to "verification look"**. They never measured detection. That also answers the technical notes' worry that patrol vanishes at long range: by day at 5 km two pickets see 61.7% of the cable [Scratch model], but at night, or against small craft, they do not, and detection never reads a name.

**6. Named deputy: relay and contact tasks only, sold on a measured gap.** The second-lowest bidder is named at claim time. On lease expiry it takes over without a bid round, or declines and the task reopens after `DEPUTY_GRACE`. It stays off patrol segments, which have hours of slack and would inherit a whole sector. **Final wording: "The backup is agreed in advance, so takeover needs no new auction. We measure that gap against a re-auction." Never "no radio traffic"**, because heartbeats renew the lease and the takeover is published. Expect "that's ownership strength" ([RTI](https://community.rti.com/static/documentation/connext-dds/current/doc/manuals/connext_dds_professional/users_manual/users_manual/OWNERSHIP_QosPolicy.htm)). Answer: "Yes, an old idea applied to boats. We accept duplicates, never gaps." With a 60 s lease and 12 s slots the saving on a healthy link is about one or two slots [Own calculation], so its real value is when the failed link is what stops the bids. Report the number even if it is small.

**7. Real radios and the drone: cut both.** No same-day Copenhagen stock was verified, range cannot be shown indoors, heartbeats alone use 60% of a LoRa allowance, and an ESP32 mesh has already appeared at a maritime hackathon. The drone is fielded in combat, the brief's kit has none, a 2D sim cannot show launch or recovery, and no landing on a small USV was found. Neither returns as a stretch goal.

**8. Scope: P0, P1, cut, and the go/no-go.** The go/no-go for idea 1 **passed on count**: 73 to 80 crossings a day per major cable, about 3 an hour, neither too few nor too many ([AIS file](http://aisdata.ais.dk/aisdk-2026-11-03.zip)). It passed in changed form: pickets plus filtered cues, not route patrol. The dark cue fired zero times, so that event stays synthetic. The AIS data gate is already cleared because the clip exists and loads in under a second, so AIS drops from 8 h to **5.5 h** by removing the grid model, which needs a held-out day that one clip cannot supply.

| Tier | Contents | Hours |
|---|---|---|
| **P0** | M0 to M12 on the real scene, three-mode runner, scorecard output, seven-criteria deck, tiered operator policy | 66 |
| Overhead the 64 h estimate omits | Kickoff, mentors, Friday re-measure, first recording, clips, rehearsal, Sunday bug fixing | About 16 |
| **P1, in order, each gated on its owner's P0** | AIS replay and cue tasks (B, 5.5); named deputy (A, 2); evidence log with time source and zone labels (C, 3) | 10.5 |
| **P2, only if Saturday 18:00 is green** | Spoofed boat (3) | 3 |
| **Cut** | Radio boards, drone, grid model, power corridor, CBBA, VRX, ArduPilot, lane sweep | 0 |

The handoff compared 64 h against 84 h, but that omits the overhead. **P0 plus overhead is about 82 h of 84 focused hours**, so P1 is earned rather than planned. It fits only in the 12 h between focused and wall-clock time. Because each P1 item has a different owner, one person's slip does not kill the others.

### Handoff items kept and overturned

| Handoff item | Verdict | Reason |
|---|---|---|
| 34/70 today | Keep | Estimate unchanged |
| About 51/70 with changes | Adjust to about 50 | Same within error; 9 of 16 points are deck work |
| Role assignment cannot differentiate | Keep | First "possible solution" in `Task07EDTH.txt` |
| 14,400 s, events at about 7,200 s | Keep | Overturns the technical notes' 16,800 s |
| Set revisit target after measuring | Keep | First value 12,000 s, not 10,800 s |
| Scout holds until the shadow boat arrives | Keep | Add keep-in-view radius 2,000 m |
| 15 s stale as a label only | **Change to 60 s** | Slots are 12 s and observations piggyback on 5 s heartbeats |
| 1800 s shadow cap | Keep | A review point in standing orders, not doctrine |
| "Free" excludes returning boats, relay, last boat on a cable route | Keep | Add a contact-speed check |
| Shore at south-centre | **Overturn** | Korsør, 14 km mast, relay west of the lane |
| 60× live view | **Overturn** | Auto-warp 240× between events, 5× around them |
| Rename Acknowledge to Approve | **Overturn** | Acknowledge means "seen" in real alert systems. Use Confirm or Stop on watching, Approve or Decline on holds |
| Live break to be confirmed | Keep, with a branch | Allowed in principle, no precedent found, settle by Saturday midday |
| Sunday noon, seven criteria, wider deck | Keep | Confirmed by reading the PDF |
| Ranked ideas | **Reorder** | New first: failure scorecard. Then pickets plus cues, deputy, log. Spoofed boat P2. Radios and drone cut |

### The change list

| # | Item | Current value | New value | Reason | Owner |
|---|---|---|---|---|---|
| 1 | Scene | Schematic, about 83 km | Great Belt box, `scene-coordinates.json` | Real data exists; old figures do not transfer | B |
| 2 | Power cable corridor | Merge (technical notes) | Drop | No parallel cables in the box | A |
| 3 | Task set | Route segments, relay | 6 cable segments, 2 pickets, relay, contact, cue | 2+2+1 answers patrol versus park | A |
| 4 | Lane | Swept by two boats | Two pickets 1.5 km west: 55.4578 N 10.9081 E; 55.3543 N 11.0135 E | Sweeping spreads the gap; no boats in the lane | A, B |
| 5 | Priority | None | Relay, contact, cue, cable, picket | Tech notes: cables before lane | A |
| 6 | Speed | 3 m/s | 2.3 m/s, sensitivity 3.0 | Only verified hull | B |
| 7 | Radii | One 500 m | `r_verify` 500; `r_detect` per class; script 2,000 | Detection and verification differ | B |
| 8 | Keep-in-view, stand-off | Implicit 500 m | Keep-in-view 2,000 m; stand-off 1,852 m; floor 500 m | Only published shadow distance | A, C |
| 9 | Shore | South-centre | Korsør 55.3316 N 11.1303 E | Real site, VTS is there | B |
| 10 | Radio | 8 km every hop | Boat 8 km, shore 14 km; sensitivity 4 km | Geometry | B |
| 11 | Relay station | Preloaded waypoint | 55.405 N 10.975 E | Reaches both pickets | A, B |
| 12 | Run, evaluation | 1,800 s | 14,400 s; evaluate at 14,000 s | Return limit | D |
| 13 | Events | 600 / 720 / 900 s | 7,200 / 7,320 / 7,500 s | Halfway, same offsets | D |
| 14 | Revisit target | 600 s | 12,000 s, confirm Friday | Real tours | D |
| 15 | Heartbeat, peer stale | 2 s, 8 s | 5 s, 20 s | Narrowband budget | A |
| 16 | Lease | 20 s per task | 60 s per boat | Range flapping | A |
| 17 | Bid round | 6 s per task | 12 s slot on shared time | Undefined rounds | A |
| 18 | Bid cost | Queue append | Cycle after cheapest insertion + battery | Geometry-blind | A |
| 19 | Merge key | (version, boat ID) | (ver, state, −bid, owner) | Lost-bid bug | A |
| 20 | Expiry claim | Any boat | Live majority only | Isolated-boat bug | A |
| 21 | Idle boat | None | Rebalance every 300 s, one release | Idle-loser bug | A |
| 22 | Contact stale, cap | 15 s, 120 s | 60 s, 1,800 s; scout holds until relieved | Team fixes | A |
| 23 | Operator policy | "Never a permission gate" | Four tiers (below) | Brief says "approves decisions" | C, D |
| 24 | Buttons | Acknowledge, Veto | Confirm, Stop; Approve, Decline | Real alert language | C |
| 25 | Cue rule | Dark only | Add slow, off-lane, stopped, AIS lost, owner alarm | Real incidents were under way | B |
| 26 | Cue filter | None | Exclude military and state vessels: report only | Keep clear, no auto-follow | B |
| 27 | Live view | 60× | Auto-warp 240× / 5× | 60× hides repair | C |
| 28 | Headline | Worst revisit age | Cable km overdue, shown with lane crossings in view | Separates modes, shows the cost | D |
| 29 | Baselines | Repair off, manual | Static pickets, repair off, Elysa; manual once | Juror's first question | D |
| 30 | Criteria | Stand-in axes | Seven official | Onboarding PDF p.4 | D |
| 31 | Deadline | About 13:00 | Noon; upload 11:30 | Onboarding PDF p.2 | D |
| 32 | Pitch | Five beats | Adds 50 s of scored business material | 3 of 7 criteria | D |
| 33 | User word | Coastguard | Watch officer, Navy Command | Denmark has no separate coast guard | D |
| 34 | Cable wording | "Actual cable routes" risk | "Public approximate routes" | Few-vertex public lines | D |

**The operator policy replaces the plan's veto section.** Short form for judges: **"Watching is pre-approved. Everything beyond watching waits for a person."** The cases show why: first radio contact took 2 h 54 min in one and about 1 h 22 min in another ([LKOS on the appeal ruling](https://www.lkoslaw.fi/insights/params/post/5301548/anchor-cable-jurisdiction-the-eagle-s-appeal-and-unclos-article-97), [operations notes](../research_notes/Challenge%2007%20scoring%20research/operations_incidents_law.md)).

| Tier | Actions | Rule |
|---|---|---|
| Automatic safety | Avoid collision, stop and hold, return on reserve, leave the lane | Boat acts, then reports. Cannot be stopped |
| Delegated under standing order | Open a track, keep in view at stand-off, repair sectors, take over relay, log, alert | Starts at once. Confirm or Stop |
| Held for approval | Close inside stand-off, enter the lane, follow out of the area, ask Belt Traffic to hail, mark contact of interest, send a report, release evidence, take a second boat off the cables | No answer means no action. Boat keeps watching |
| Authority only | Order to stop or raise anchor, board, detain, direct to port, contact flag state, assign blame | System only supplies the record |

## The build plan, Friday 19:00 to Sunday 12:00

All hours are judgement estimates. Assign real names to slots A to D at kickoff; the notes hold no skill data, so this report does not. Sleep is assumed from 00:00 to 08:00.

### Before kickoff today

Log in to the EDTH platform and read `/challenges` and `/agenda`; both exist behind login and likely answer owner, mentors, hardware and start time. Confirm whether hacking starts at 18:00 ([Luma](https://luma.com/edth-2026-copenhagen)) or the plan's 19:00, and use any extra hour on the contract. Note the assigned team number, which starts the deck filename and is not the challenge number. Run the install below on every laptop, on venue Wi-Fi, with one Python minor version. Keep `ais-clip-box.csv` out of any public repository: EDTH treats shared material as non-confidential (Onboarding PDF p.1), and rare type and length combinations could narrow a vessel down. Copy `scene-coordinates.json` and the clip into `data/`, and list both on a "pre-existing work" slide: the Paris 2026 FAQ says only event work counts ([FAQ](https://events.eurodefense.tech/paris-2026/hackathon-faq)). Franciszek needs to empty the Recycle Bin to finish deleting the raw AIS data, as the notes record.

### Repo and install

```text
edth07/
  requirements.txt
  config/default.toml      every number, hashed into each run
  scenarios/fixed.toml     event tape
  data/                    scene-coordinates.json, ais-clip-box.csv (gitignored)
  contract/                frozen Fri 21:00; change needs A + B
    constants.py messages.py tasks.py views.py
  agent/      (A)          imports contract only
    core.py table.py auction.py tour.py relay.py contact.py deputy.py
  world/      (B)
    sim.py routes.py motion.py sensors.py radio.py channel.py
  eval/       (D)          never imported by agent/
    metrics.py run_batch.py report.py
  tools/      (D)          scene_check.py
  server/     (C)          bridge.py replay.py
  web/        (C)          index.html map.js panels.js
  ais/        (B)          replay.py cues.py
  evidence/   (C)          chain.py verify.py
  tests/      smoke/ protocol/ fairness/ story/
  runs/                    gitignored
```

Rules: each person stays in their folder, `contract/` changes by pull request only, `main` must always pass `pytest -q tests/smoke`, and a tagged `core-fallback` stays runnable.

`requirements.txt` (versions from PyPI metadata, not installed or tested here; if msgspec has no wheel for your Python, use dataclasses with stdlib json):

```text
numpy==2.5.4
shapely==2.2.0
websockets==17.4
msgspec==0.22.0
pytest==9.2.0
hypothesis==6.170.14
cryptography==50.0.2
rfc8785==0.1.4
pandas==3.0.5
pyproj==3.8.0
```

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "import numpy, shapely, websockets, msgspec, cryptography, rfc8785; print('ok')"
```

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Configuration: every number in one file

```toml
# config/default.toml  -- chosen test inputs, not measured capabilities
[scene]
file = "data/scene-coordinates.json"   # lines clipped to the 25 x 10 km box
scenario_lines = ["HVDC_Storebaelt_I", "MV_60kV_Sprogo_Funen", "Great_Belt_1_fibre"]
shore = [55.3316, 11.1303]             # Korsor
relay_station = [55.405, 10.975]
picket_n = [55.4578, 10.9081]          # on HVDC, 1.5 km west of lane
picket_s = [55.3543, 11.0135]          # on Great Belt 1, 1.5 km west of lane
segment_max_m = 5000
sample_step_m = 100

[boat]
speed_mps = 2.3            # sensitivity 3.0
endurance_s = 25200
reserve_s = 1800
r_verify_m = 500
r_detect_m = {dusk = 2000, ship_day = 5000, small_day = 1500, night_unlit = 500}
keep_in_view_m = 2000
standoff_m = 1852
standoff_floor_m = 500
ais_class_a_m = 20000
ais_class_b_m = 8000

[radio]
boat_m = 8000              # sensitivity 4000
shore_m = 14000
delay_s = [0.25, 1.0]
loss = 0.05
max_hops = 4

[run]
horizon_s = 14400
evaluate_s = 14000
revisit_target_s = 12000   # confirm Friday
tick_s = 1
seeds = [1, 2, 3, 4, 5]
```

### Contract: messages, tasks, constants

Time is integer milliseconds from the sim clock, passed as an argument. Agents never call `time.time()`. Messages cross the radio as encoded bytes, which blocks shared objects, the likeliest hidden leak.

```python
# contract/constants.py
HEARTBEAT=5_000; PEER_STALE=20_000; LEASE=60_000; SLOT=12_000
DEPUTY_GRACE=10_000; REBALANCE=300_000; SHORE_SILENCE=30_000
CONTACT_STALE=60_000; SHADOW_CAP=1_800_000; CUE_TTL=180_000
CYCLE_MAX=21_600_000   # 6 h
RELEASED, CLAIMED, VETOED = 0, 1, 2

# contract/messages.py   Envelope, every message
# msg_id, src, t_created, t_expire, kind, hops, payload
# kind in HB, BID, REC, OBS, CONTACT, VETO, ACK
# Expiry: HB and BID 12 s; REC, OBS, CONTACT 60 s; VETO 30 s. Retry every 5 s. Max 4 hops.
# Forwarding never refreshes t_created or an observation time.

# contract/tasks.py
@dataclass(frozen=True, slots=True)
class Rec: task:str; ver:int; state:int; bid:int; owner:int; deputy:int  # deputy 0 = none

def key(r): return (r.ver, r.state, -r.bid, r.owner)
def merge(a, b): return a if key(a) >= key(b) else b
```

| Task ID | Kind | Bid order | Created by | Notes |
|---|---|---|---|---|
| `relay` | relay | 1 | Mission file | Deputy allowed |
| `contact:C-07` | contact | 2 | Detecting boat | Deputy allowed; ID stable across boats |
| `cue:{track}:{cable}` | cue | 3 | Any boat hearing the ping | P1; expires after `CUE_TTL`; ID deterministic so records merge |
| `seg:H:0`, `seg:H:1`, `seg:G:0..2`, `seg:M:0` | seg | 4 | Mission file | HVDC, Great Belt 1, 60 kV |
| `pick:N`, `pick:S` | pick | 5 | Mission file | Lowest priority; a boat that wins any `seg` releases its `pick` |

Initial owners: 01 `seg:G:*` and `seg:M:0`; 02 `seg:H:*`; 03 `pick:N`; 04 `pick:S`; 05 `relay`.

```python
# agent/table.py  One lease per boat. Heartbeats renew all of a boat's tasks.
def lease_ok(b, t): return b == me or t <= last_hb[b] + LEASE

def is_open(task, t):
    r = table[task]
    if r.state == RELEASED: return True
    if r.state == VETOED or lease_ok(r.owner, t): return False
    if r.deputy and t < last_hb[r.owner] + LEASE + DEPUTY_GRACE: return False
    return True

def on_record(r):
    cur = table[r.task]; new = merge(cur, r)
    if new is cur: return
    table[r.task] = new; forward(new)
    if cur.owner == me and cur.state == CLAIMED and new.owner != me:
        drop_from_tour(r.task)

# agent/auction.py  Slotted rounds on shared time. No coordinator.
def on_slot(t):                     # fires when t % SLOT == 0
    e = t // SLOT
    close_round(e-1, t)
    for task in sorted(table, key=bid_order):
        if is_open(task, t) and can_bid(task, t):
            send(Bid(task, e, bid_cost(task), me)); break   # one bid per slot

def close_round(e, t):
    for task, bs in sorted(bids.pop(e, {}).items()):
        if not is_open(task, t): continue          # live claim arrived: cancel
        bs = sorted(bs, key=lambda b: (b.cost, -b.boat))
        if bs[0].boat == me:
            dep = bs[1].boat if len(bs) > 1 and kind(task) in ("relay", "contact") else 0
            publish(Rec(task, max_ver(task)+1, CLAIMED, bs[0].cost, me, dep))
            insert_into_tour(task)
            if kind(task) == "seg" and owns("pick"): release(my_pick())

def cycle_after(task):  return cheapest_insertion_length(tour, task) * 1000 // V_MM_S
def bid_cost(task):     return cycle_after(task) + 1_800_000 * (1000 - batt_permille) // 1000

def can_bid(task, t):
    if mode in (RETURNING, UNAVAILABLE): return False
    k = kind(task)
    if k == "seg":
        if mode == SHADOWING or i_am_relay(): return False
        r = table[task]
        if r.state == CLAIMED and 1 + live_peers(t) < n_active()//2 + 1:
            return False                       # expiry takeover needs a live majority
        cyc = cycle_after(task)
        return cyc <= CYCLE_MAX and energy_ok(cyc)
    if k == "pick":
        return mode == PATROL and not i_am_relay() and not owns("seg")
    if k == "relay":
        return shore_age(t) > SHORE_SILENCE and energy_ok_relay()
    if k == "contact":
        return (not i_am_relay() and not i_am_last_cable_owner()
                and energy_ok_contact() and contact_speed(task) <= V)
    if k == "cue":
        return (not i_am_relay() and not i_am_last_cable_owner()
                and eta_ok(task))     # (dist - R_VERIFY)/V <= t_cross - t - margin
# n_active drops boats that announced return, or have been silent 600 s.

def on_rebalance(t):                 # every REBALANCE, staggered by boat ID
    lo = min(available_peers(t), key=cycle)
    if my_cycle() > 1.25*lo.cycle and len(tour) >= 2 and not any_open(t):
        s = segment_whose_removal_lowers_max_cycle(lo)
        if estimated_cycle_after(lo, s) < my_cycle():
            publish(Rec(s, max_ver(s)+1, RELEASED, 0, me, 0))

# agent/deputy.py  P1. Relay and contact only.
def on_tick(t):
    for task, r in table.items():
        if r.deputy == me and r.state == CLAIMED and not lease_ok(r.owner, t):
            if can_bid(task, t):
                publish(Rec(task, r.ver+1, CLAIMED, bid_cost(task), me, 0))
            else:
                publish(Rec(task, r.ver+1, RELEASED, 0, me, 0))

# ais/cues.py  P1. Runs on each boat, only on pings inside its modelled reception range.
def on_ais(ping, t):
    hit = first_cable_hit(ping.x, ping.y, ping.sog, ping.cog, horizon_s=600)   # 10 min dead reckoning
    if not hit: return
    if (ping.sog_kn < 3 or lane_offset_m(hit.point) > 1000) and ping.ship_type not in EXCLUDE:
        open_task(f"cue:{ping.track}:{hit.cable}", hit.point, hit.t, expires=t+CUE_TTL)
# EXCLUDE = pleasure, sailing, SAR, pilot, law enforcement, military (report only).
```

Stop is a record: `Rec(contact_id, ver+1, VETOED, 0, 0, 0)`. Scout rule: the scout keeps the contact until another boat reports it in view within 2,000 m, and only then releases. Stale means no boat has observed it for 60 s. Offline rule: keep watching until reserve or the 1,800 s cap, never escalate, queue the report. Merge guarantee language: eventual convergence per connected group, given delivery. Name it correctly: fixed-order sequential single-item auction, per-task last-writer-wins register with a logical counter and replica-ID tie-break, and leases. It is not CBBA and not consensus, and it carries no SSI bounds.

Snapshot, sent over WebSocket at 5 to 10 Hz on two channels, `/shore` (delivered data only) and `/truth` (evaluator panel, labelled):

```json
{"t":0,"speed":240,"boats":[{"id":1,"x":0,"y":0,"mode":"PATROL","batt":1000,"link":"direct","tour":["seg:G:0"]}],
 "tasks":{"seg:G:0":{"v":1,"owner":1,"deputy":0,"state":1}},"seg_age":{},"contacts":[],"events":[]}
```

Run log is JSONL: line 1 holds seed, config hash, git commit and schema version; then events, snapshots every 10 sim-s, and a state hash every 60 sim-s. Replay re-runs from seed plus injection list and checks hashes.

### The fixed event script

`t = 0` maps to file clock **10:15** on 3 November 2026, treated as UTC (unverified). That window holds 33 crossings and 5 filtered ones. A boat's AIS receiver only gets pings inside its modelled range, never a global table.

```toml
# scenarios/fixed.toml
[[event]]
t = 0
kind = "reset"
warm = "warm_state.json"
ais_t0 = "2026-11-03T10:15:00"

[[event]]             # brief: "one USV runs low on battery and heads home"
t = 7200
kind = "battery_low"
boat = 1

[[event]]             # brief: "another loses its link to the control station"
t = 7320
kind = "link_off"
a = 4
b = "shore"

[[event]]             # synthetic; starts the 180 s dwell. Never a real vessel.
t = 7320
kind = "contact_start"
id = "C-07"
lat = 55.4505
lon = 10.8706
ais = false
sog_kn = 0.4
class = "dusk"

[[event]]
t = 9200
kind = "contact_depart"
id = "C-07"
sog_kn = 6.0
course = 255

[[event]]
t = 10800
kind = "link_on"
a = 4
b = "shore"

[[event]]
t = 14000
kind = "evaluate"
```

| Sim time | What happens | Screen |
|---|---|---|
| 0 to 3,700 | Warm start. 01 and 02 sweep, 03 and 04 picket, 05 relays | Roles, ages, links |
| About 3,770 | Replayed AIS cue: cargo track 3.3 km off lane at the HVDC (P1) | "Cue for a look", not "suspicious" |
| 7,200 | 01 low battery, heads to Korsør. Its cable tasks open | Caution. `seg:G:*` open |
| About 7,212 to 7,250 | 04 wins them, releases `pick:S` | "Lane picket S uncovered" stays visible |
| 7,320 | 04's direct shore link cut; traffic flows through 05. C-07 begins loitering | Crossed link; peer path shown |
| About 7,500 in the demo seed | 02 detects within 2,000 m; 180 s dwell met | Warning card; no AIS match |
| About 7,500 to 7,800 | 03 nearest free, moves to stand-off; 02 holds until 03 has it in view | "Keeping in view. Standing Order 2." `pick:N` open |
| Scripted | Confirm; then Approve "Close to 500 m, photograph both bows" | Name NOT READ, Anchor NOT SEEN until close |
| 9,200 | C-07 departs at 6 kn, above boat speed | "Cannot hold"; report queued; last course logged |
| After 9,200 | 03 returns to `pick:N`; no idle boat | Gap stays open at picket S |
| 10,800 | 04 link back; records merge | Reconciled ownership |
| About 12,570 | Military track off lane: no cue, report only | Keep clear |
| About 12,790, 13,330 to 13,360 | Replayed cues at Great Belt 1 during the degraded fleet: one tug; two slow tracks moving together | The cost of an alert, measured |
| 14,000 | Evaluate | Scorecard |

C-07 sits on the public HVDC line about 4 km west of the lane, 2.5 km from the north picket, so the picket cannot see it at 2,000 m and only a sweeping scout can. That is the "why patrol" case in one event. Detection time varies by seed because the scout's phase varies, so report it as a distribution. **Phase drives the spread in the scratch model (3.5 to 9.2 km), so the five batch seeds must vary warm-up phase as well as the radio tape.** Pick the demo seed where detection lands near 7,500 s. The time-warp must read this tape, slowing before each event, or the viewer misses the repair.

### Numbered steps

| # | When | Slot | Build | Depends on | Hours | Done test |
|---|---|---|---|---|---|---|
| 1 | Fri 19:00 | All | Assign names to slots. Confirm owner of 07 if known. Create repo, `pytest -q tests/smoke` empty pass | Pre-kickoff | 1 total | Names on the wall, repo cloned by four |
| 2 | 19:15 to 21:00 | A + B | M0 `contract/` as above, `config/default.toml`, `scenarios/fixed.toml`, fake radio timing test | 1 | 4 | Schema frozen; fake radio delivers a bid inside one slot |
| 3 | 19:15 to 21:00 | D + C | Mentor round (section below). Mentor log: "assumed X, mentor said Y, changed Z" | 1 | 3.5 | One-page decision: user, metric, policy, business line |
| 4 | 20:30 | C | Review `views.py` snapshot shape with A and B | 2 | 0.5 | C signs off the JSON |
| 5 | 21:00 to 24:00 | B | M1a `world/routes.py`: load JSON, equirectangular metres about 55.40 N 11.00 E, clip to box, split to ≤5 km, 100 m samples. `motion.py`: 2.3 m/s, 1 s tick | 2 | 3 | 6 segments, 23.5 km, 235 samples ±2; five boats move |
| 6 | 21:00 to 24:00 | A | M3 `table.py`, `core.py`: Rec store, merge, heartbeat, per-boat lease, `is_open`, `on_record` | 2 | 3 | D5 Hypothesis passes: merge commutative, associative, idempotent |
| 7 | 21:00 to 24:00 | C | `web/index.html`, `map.js`: Canvas in local metres, cables, lane, Korsør, boats, ages, from a fake snapshot. No tiles, no bundler | 4 | 3 | Map renders offline |
| 8 | 21:00 to 23:00 | D | M7a `eval/metrics.py`: sample ages, km overdue, worst age. Warm-up to `warm_state.json` | 5 | 2 | Ages seeded and identical across two runs |
| 9 | 23:00 to 24:00 | D | **Friday re-measure.** `tools/scene_check.py`: worst age per boat at 2.3 and 3.0 m/s, return limit per boat, radio graph at stations, chart check of all stations and C-07 by eye | 5 | 1 | Revisit target set; graph connected; no station on land |
| | **Sat 00:00** | | **Milestone: five boats, real scene, freshness on map** | 5, 7, 8 | | Reset deterministic |
| 10 | Sat 08:00 to 12:00 | A | M4a `auction.py`, `tour.py`: slots, bids, cheapest insertion, repair, pick release on seg win | 6 | 4 | P1, P2, P3, P6 pass; remove any boat and tasks reassign |
| 11 | 08:00 to 10:00 | B | M1b battery, return rule, `sensors.py` two radii, own-sensor views only | 5 | 2 | D6 import test passes; return rule fires at the computed time |
| 12 | 10:00 to 12:00 | B | M2a `radio.py` heap of (deliver_ms, seq, dst, msg), range check on send and deliver, `channel.py` pre-drawn drop and delay tape via `Generator.spawn` | 2 | 2 | Link-off drops packets; tape hash equal across modes |
| 13 | 08:00 to 11:00 | C | M8 `server/bridge.py`, `replay.py`; `/shore` and `/truth` | 7, 11 | 3 | D3 replay matches hashes |
| 14 | 11:00 to 12:00 | C | Failure controls: any boat, any directed link, logged | 13 | 1 | Works for IDs other than 01, 04, 05 |
| 15 | 08:00 to 11:00 | D | M7b `run_batch.py --modes static,off,elysa --seeds 1,2,3,4,5`, fairness tests | 8, 10 | 3 | F1 to F5 pass; config diff between modes is one key |
| 16 | 11:00 to 12:00 | D | First ON/OFF numbers. Apply the gate below. Tag `core-fallback` | 15 | 1 | Gap visible or the rule below fires |
| | **Sat 12:00** | | **Milestone: tagged fallback and baseline runner** | | | Fallback runs from a clean clone |
| 17 | 12:00 to 15:00 | A | M4b quorum, cycle cap, `on_rebalance`, priority order | 10 | 3 | P4, P5 pass |
| 18 | 15:00 to 18:00 | A | M5 `relay.py`, shore-age gossip, split and rejoin, plus integration | 12, 17 | 3 | P7, relay-loss test pass |
| 19 | 12:00 to 14:00 | B | M2b store-and-forward, retry, dedupe by `msg_id` | 12 | 2 | Stale shore data stays stale; observation time never refreshed |
| 20 | 14:00 to 16:30 | B | P1 `ais/replay.py`: load clip, feed pings by reception range, class A 20 km, class B 8 km | 16 green | 2.5 | No boat receives a ping outside range (test) |
| 21 | 16:30 to 18:00 | B | Integration on link loss with A | 18, 19 | 1.5 | Four-hop path works in the real geometry |
| 22 | 12:00 to 16:00 | C | `panels.js`: roles, link status, cable age, picket status, auto-warp from the tape | 13 | 4 | 240× between events, 5× for 120 sim-s around each |
| 23 | 16:00 to 18:00 | C | Decision cards, tiers, Confirm, Stop, Approve, Decline | 22 | 2 | Held action does nothing without an answer |
| 24 | 12:00 to 15:00 | D | M10 protocol tests in `tests/protocol/` | 10 | 3 | P1 to P6 in CI |
| 25 | 15:00 to 18:00 | D | **Deck v0: manufacture, business, market and team slides first** | 3 | 3 | A stranger reads the slides and names buyer, price, market |
| | **Sat 18:00** | | **Milestone: link loss** | | | Split, rejoin, relay loss pass; shore view stale correctly |
| 26 | 18:00 to 21:00 | A | M6 `contact.py`: contact task, scout holds, stand-off, keep-in-view, cannot-hold, Stop, last-scout guard | 18 | 3 | Story tests S1 to S4 pass |
| 27 | 21:00 to 23:00 | A | P1 M13 `deputy.py` | 26 on time | 2 | P8 passes; deputy gap logged against re-auction |
| 28 | 18:00 to 21:00 | B | P1 M16 `ais/cues.py`: dead reckoning, filter, cue task through the same auction, `eta_ok` | 20 | 3 | A replayed cue becomes one boat's task and the cost shows in km overdue |
| 29 | 21:00 to 23:00 | B | Real-scene tests R1 to R3, cross-boat integration | 28 | 2 | Green on three seeds |
| 30 | 18:00 to 21:00 | C | P1 M14 `evidence/chain.py`, `verify.py`: per-boat hash chain, Ed25519 on heads, heads in heartbeats, time source, zone label | 6 | 3 | Edit one line and the verifier names the first bad sequence |
| 31 | 21:00 to 23:00 | C | First full recording | 26 | 2 | A complete video exists on Saturday night |
| 32 | 18:00 to 21:00 | D | `eval/report.py` scorecard; story tests | 24 | 3 | One command prints the scorecard table |
| 33 | 21:00 to 23:00 | D | Deck v1, first timed rehearsal | 25, 32 | 2 | Under 3:00 with a stopwatch |
| | **Sat 23:00** | | **Milestone: contact and approval; feature freeze** | | | Nothing new after this |
| 34 | Sun 08:00 to 09:00 | D | Final batch, at least 5 seeds with varied phase, both speeds | Freeze | 1 | Median and range for every number |
| | **Sun 09:00** | | **Milestone: results** | | | Actual numbers replace all scratch figures |
| 35 | 08:00 to 10:00 | A | Bug fixes only | Freeze | 2 | Smoke and story green |
| 36 | 08:00 to 10:00 | B | Bug fixes; offline copy of everything on two laptops | Freeze | 2 | Runs with Wi-Fi off |
| 37 | 08:00 to 10:00 | C | 20 s clips for each failure choice, one keypress away | Freeze | 2 | Every boat, the relay, one link |
| | **Sun 10:00** | | **Milestone: code freeze** | | | Tag `final` |
| 38 | 10:00 to 10:30 | C + D | Final video; upload (unlisted); test the link signed out | 35 to 37 | 1 | **Video live by 10:30 at latest** |
| 39 | 09:00 to 11:30 | D | Final deck with real results and video link, `NN_ElysasSecret.pdf` | 34, 38 | 1.5 | **Submitted by 11:30**; reopened from the server |
| 40 | 10:30 to 12:00 | All | Timed rehearsals, three with a forced crash | 39 | 2 | Ten runs by pitch time across Saturday and Sunday |

Totals: A 22.25, B 22.25, C 22.75, D 23.25, plus 2 rehearsal, about **92 h against 96 wall-clock hours and 84 focused hours**. That leaves no slack, which is why the cut order is strict. If only one P1 survives, keep AIS cues, because they are the only real-data element and B has the capacity.

### Acceptance tests

Determinism: **D1** same seed in two processes with different `PYTHONHASHSEED` gives identical hashes. **D2** reset mid-run equals a fresh run. **D3** replay from the injection log matches hashes. **D4** grep test: no `time.time`, no global `random`, no iteration over a set without `sorted`. **D5** merge is commutative, associative and idempotent under Hypothesis. **D6** `agent/` imports neither `world/` nor `eval/`.

Fairness: **F1** warm state, event tape and channel tape hashes are equal across modes. **F2** segment ages at T−1 are byte-identical across modes, the strongest single test. **F3** repair-off produces zero repair claims after T. **F4** config diff between modes is exactly one key. **F5** at least 5 seeds, median and range, no single-seed headline.

Protocol: **P1** lost bid: cheaper boat wins on merge. **P2** winner dies mid-round: task re-auctioned next slot. **P3** refresh arrives mid-window: round cancelled. **P4** isolated boat claims nothing expired, and only the majority side claims on expiry (this replaces the plan's split test). **P5** rejoin: no boat idle after two rebalance periods. **P6** claim beats release at equal version. **P7** a group with a shore path elects no relay. **P8** deputy takes the relay with radio silent, or declines.

Story, from the plan: **S1** reset clears leases, queues, random state, ages and action counts, and five boats start 2/2/1. **S2** a different failed boat works the same way. **S3** starting to keep in view works before any operator input; Stop, expired Stop, stale, offline cap and battery return follow the policy. **S4** 04's lost link stays visibly crossed and peer observations still travel. **S5** no "gap closed" claim from assignment alone: a segment counts only after a sensor visit. **S6** relay loss with any current holder; no feasible replacement shows isolation.

Real scene, new: **R1** radio graph at stations is connected and 04 has a real direct link to cut. **R2** no station lies inside the lane band, and no scripted boat dwells there. **R3** AIS pings reach only boats inside modelled range.

### Milestones, cuts and the hard fallback rule

| Milestone | Exit check |
|---|---|
| Fri 21:00 | Contract, owners, default policies frozen; mentor decision written |
| Sat 00:00 | Five boats on the real scene, freshness on map, deterministic reset |
| Sat 12:00 | `core-fallback` tagged, baseline runner works, first gap measured, any boat removable |
| Sat 18:00 | Link loss, split and rejoin, relay takeover; deck v0 with business slides |
| Sat 23:00 | Contact and approval; feature freeze; first full video exists |
| Sun 09:00 | Final batch; real numbers replace all scratch figures |
| Sun 10:00 | Code freeze, tag `final` |
| Sun 10:30 at latest | Video uploaded and link tested signed out |
| Sun 11:30 | Deck submitted, filename starts with team number |
| Sun 12:00 | Hard deadline. Anything after it may not reach the pitch machine (Onboarding PDF p.2) |

**Cut order, first to go:** spoofed boat; evidence-log report (keep the chain); deputy; cue tasks down to one replayed cue; manual-operator run; extra scorecard rows; notification and retry queue; fallback branch variations; peer sharing down to a single-hop relay. **Never cut:** reset, the three-mode baseline, the video, the seven-criteria deck, gaps shown openly.

**Hard fallback rule.** Any milestone more than 60 minutes late triggers the next cut immediately, with no debate. If P0 for an owner is late, that owner's P1 is gone. If at **Sat 12:00 `core-fallback` does not run end to end, all P1 and all other features stop** until it does. If the first ON/OFF run shows no visible gap between modes, D stops feature work with A and fixes tasks or geometry before anything else, because the result slide depends on it. If `main` fails smoke or the batch at **Sun 09:30**, revert to the last green tag, disclose the reduced scope on the deck, and do not debug after 10:00. If the contact story is not running by Sun 09:00, ship Core with a labelled clip of what exists; a Core-only build is not a completed challenge scenario and the deck must say so.

Honesty rules hold throughout: no invented results, no hostile-intent claims, gaps shown openly, and every scratch figure above is replaced by a measured one or dropped.

## The pitch: three minutes that score all seven criteria

Timing is strict and jurors cut you off (Onboarding PDF p.3). About 350 spoken words. The demo sits early, so a failure still leaves time for the scored material. Do not name any real vessel in connection with suspicion anywhere in the deck, video or speech: say "the EstLink 2 cable" and "a tanker". Replayed AIS tracks appear as anonymous IDs, and cues read "cue for a look".

| Time | Beat | Say or show | Criterion |
|---|---|---|---|
| 0:00 to 0:20 | Person and problem | "For the one watch officer covering 25 by 10 km of the Great Belt, we built..." Real map | Problem |
| 0:20 to 0:35 | Why now | "On Christmas Day 2024 the EstLink 2 cable failed at 12:26. Authorities reached the tanker at 15:20. Four more cables went before 18:45, according to the indictment; no court has ruled on guilt. On Thursday a Helsinki court ruled in a later case; that verdict is not final." | Problem |
| 0:35 to 1:10 | Live moment | Boats running. Ask a military juror by name: "Which boat do we lose?" One word, one click. Repair runs, the gap stays visible, then moves | Feasibility, pitch |
| 1:10 to 1:40 | Insight and number | "Fewer boats cannot close the gap, only choose where it lands." Three-mode result, seeded runs, real numbers only | Technical, originality |
| 1:40 to 2:00 | Real versus modelled | Real AIS day, public approximate cable lines, synthetic dark contact, 2D sim. "A mentor told us X, so we changed Y" | Feasibility |
| 2:00 to 2:35 | Scale and money | Box, buyer, price, market lines below | Manufacturing, business, size |
| 2:35 to 2:50 | Team | What four people built this weekend, with real facts only | Team |
| 2:50 to 3:00 | Ask | "If you run a patrol or a cable, talk to us today about one supervised tabletop with a duty officer." | Call to action |

**Demo script.** Run locally on the team's laptop at high warp, with the repair visible within about 20 seconds. Boats are numbered. The juror says one word; if there is no answer in 3 seconds, the presenter picks the relay, which is the most dramatic failure. Click. Narrate one sentence: "The backup takes the relay, the lane boat takes the cable, and that picket stays open on screen." At 1:10 on the stopwatch move on, whatever is on screen. A live run is exploratory, so quote numbers only from fixed seeded runs. No juror interaction at an EDTH pitch is documented, so this is unproven.

**Failure fallback, rehearsed.** If the software freezes, say "That's the sim. Here is the same failure recorded an hour ago," and cut within 5 seconds, always saying it is a recording. A boat failing badly in the sim is the product, not a failure. Ladder: live laptop with no venue internet; then the 20 s clip for the chosen boat, one keypress away; then the mandatory video linked in the deck; then a static results slide. If only the organisers' machine is allowed, show the video, state the seeded result and offer the pick during questions. Settle this by Saturday midday. If the event shortlists, the deck and video may decide whether the team pitches at all, so they must stand alone.

**Lines for the scored criteria.** Every price is a team assumption or estimate and must be said as one.

| Topic | Line | Source |
|---|---|---|
| Deployment | "Boats launch from a harbour or Home Guard vessel, patrol a shift, return and charge. The box talks MAVLink to the existing autopilot, which keeps its own safety behaviour. One console on shore approves and stops." | [ArduPilot](https://ardupilot.org/rover/docs/boat-configuration.html) |
| Real-world limit | "This is simulation. A civil trial in Danish waters needs permission through the Emergency Management Agency four weeks ahead, or a defence operator." | [Order 1229](https://www.dma.dk/Media/638721095895242663/Executive%20Order%20on%20navigational%20safety%20regarding.pdf) |
| Night | "At night an unlit vessel is a weak case for a visible camera. We show that curve rather than hide it." | [Judgement] |
| Manufacture | "Software plus a EUR 2,500 to 4,500 retrofit box of off-the-shelf parts (our estimate; verified core about USD 1,900), built by a European EMS firm, on any ArduPilot boat." | [Compute Module 5](https://www.raspberrypi.com/products/compute-module-5/), [Pixhawk 6X](https://holybro.com/products/pixhawk-6x), [mesh radio listing](https://dasenic.com/product/doodle-labs-rm-2450-12m3-8186357) |
| Hull cost | "BlueBoat-class hulls from USD 4,400 for harbour trials; a five-boat set is about USD 22,000." | [Blue Robotics](https://bluerobotics.com/store/boat/blueboat/blueboat/) |
| Buyer | "In Denmark that is Navy Command, which holds surveillance, environmental response and rescue." | [EMSA](https://portal.emsa.europa.eu/web/dona/country-profiles/denmark/competent-authorities-for-coast-guard-functions) |
| Demand | "Sweden contracted 1,440 boat-days in October 2026. The US Coast Guard paid USD 15.5m for 16 boats. Denmark's new contract is being written." | [defence-industry.eu](https://defence-industry.eu/sweden-contracts-saildrone-to-operate-four-uncrewed-vessels-for-baltic-sea-surveillance/), [Tectonic](https://www.tectonicdefense.com/saildrone-scores-15-5m-uscg-contract/), [Defense News](https://www.defensenews.com/global/europe/2026/09/24/with-denmark-saildrone-logs-first-flag-registration-for-naval-surveillance-drone/) |
| Pain | "One EstLink 2 repair was estimated at EUR 50 to 60m, and owners may not recover it." | [ceenergynews](https://ceenergynews.com/uncategorized/repair-works-estlink-2-begins-may/) |
| Model | "Per-boat licence plus site subscription, through boat makers and service operators: EUR 160,000 a year per five-boat site, proposed." | Team assumption; comparables [Hivemind](https://insideunmannedsystems.com/shield-ai-raises-240m-to-scale-hivemind-enterprise-developer-platform/), [Nemyx](https://auterion.com/auterion-launches-nemyx-enabling-fully-coordinated-drone-swarms/) |
| Market | "Maritime situational awareness, USD 3.9bn in 2025 heading to USD 7.8bn by 2034; USV hulls alone USD 0.8bn growing to USD 1.6bn by 2030. A Baltic start is EUR 3 to 5m of licences a year (our estimate), which is why this has to spread to all small USV fleets, ports and offshore energy." | [Fortune Business Insights](https://www.fortunebusinessinsights.com/maritime-situational-awareness-system-market-119054), [MarketsandMarkets](https://marketsandmarkets.com/PressReleases/unmanned-surface-vehicle.asp) |
| Complement | "Voyagers are wide-area persistent sensors. Small boats are a cheap local response layer." | [Defense News](https://www.defensenews.com/global/europe/2026/09/24/with-denmark-saildrone-logs-first-flag-registration-for-naval-surveillance-drone/) |

Have the USD 5,300 per vehicle-day derivation ready if a VC asks: USD 15.5m across 16 boats for about 184 days, assuming the contract covers only those days. Do not say "Denmark bought Saildrones", "we partner with" anyone, "prevents cable cuts", or a Baltic total cable length. For the deck, add © OpenStreetMap contributors, call cable lines "public approximate routes", and cite the ruling number R 706/2025/12270 rather than the restricted-marked copy. The deck must also state what was achieved during the hackathon (Onboarding PDF p.3), so keep Friday-to-Sunday screenshots.

## Friday's first two hours: find the owner, then test the user

Be in the room for any challenge and mentor presentation before hacking starts, and note every name attached to USVs, undersea infrastructure and autonomy. Treat each mentor as a possible juror: the Paris 2026 FAQ reserves judging for military representatives, selected mentors and partner companies ([FAQ](https://events.eurodefense.tech/paris-2026/hackathon-faq)). Challenge 07's owner could not be identified, and the evidence leans towards an open problem statement rather than a sponsor challenge, with low-to-moderate confidence. If so, there may be no dedicated mentor and the team must recruit one. Skyfall, Fire Point and IRON around the event raise the odds of a Ukrainian juror who will test operational realism.

| Minutes | Who | Goal |
|---|---|---|
| 0 to 15 | Organisers | Owner, mentor, stage logistics, hardware |
| 15 to 50 | Military, naval, Ukrainian operators | User, operator policy, picket reality |
| 50 to 80 | Technical and autonomy mentors | Has it been tried, is a 2D sim credible |
| 80 to 100 | Investors and industry | Who pays, how it scales |
| 100 to 120 | Team | One-page decision; freeze the contract |

If only three questions get asked, ask 1, 3 and 5.

| # | Ask whom | Question |
|---|---|---|
| 1 | Organisers | Is 07 a sponsor challenge or open problem statement? Who owns it, and who is its mentor? |
| 2 | Organisers | Does each challenge or track have its own recognition? How many teams pitch, is there a shortlist? |
| 3 | Organisers | Can we use our own laptop and HDMI? Is a live demo possible in the 3 minutes, and who clicks? |
| 4 | Operators | Who owns this mission in Danish waters? Is "coastguard" the right user at all? |
| 5 | Operators | Should a boat start keeping in view at once, or wait for approval? Is "watching is pre-approved" acceptable? |
| 6 | Operators | Would you station a 2 m boat 1.5 km from the Great Belt lane? What stand-off is sane? Is 1 nm right? |
| 7 | Operators | With two boats gone, cables before lane: is that the right default, and who should set it? |
| 8 | Operators | Is AIS-off the main signal, or AIS-on and behaving strangely? What does a look need to achieve? |
| 9 | Operators | What actually kills a small USV out there: sea state, fouling, radio, traffic? |
| 10 | Technical | Has this been tried, and is there one simple reason it fails? What baseline would you trust? |
| 11 | Technical | Would you believe a 2D sim, and which single real element would change your mind? |
| 12 | Technical | Is a 14 km shore link and 8 km boat hop plausible at 2 m antenna height? Is a Sprogø or bridge mast realistic? |
| 13 | Investors | Who signs, from which budget? Per hull, per vehicle-day or per area? Does EUR 160,000 a site sound sane? |
| 14 | Investors | What makes this a company rather than a feature of a boat maker's product? |

Run these in pairs, one talking and one writing. Show the map rather than describe it. If a mentor attacks the idea, spend a while finding what can be kept: at Lviv the teams that held on and adapted did better than those who dropped everything ([Resilience Media](https://www.resiliencemedia.co/p/dispatches-from-kyiv-and-lviv-ukraines)). End with one go or no-go on user and policy.

## What is measured, what is estimated and what is still unknown

| Status | Item |
|---|---|
| **Measured, with limits** | One Tuesday only, 3 November 2026. 85 vessels, 73 HVDC crossings, 80 Great Belt 1 crossings, median 11.7 kn, zero AIS gaps over 10 min, 2 stops near a cable. A sample, not a rate. Pleasure craft are near their yearly low, with 1 Class B vessel in the box |
| **Measured** | Lane width 0.85 to 1.44 km; cargo and tanker P95 offset 0.856 km; clip 61,408 rows |
| **Thresholds set on the same day** | Under 3 kn, off-lane over 1 km, 10-minute lead, and the west picket side. **Nothing is validated on other data**, and 9 filtered events cannot separate results that differ by one or two |
| **Approximate** | Cable lines are few-vertex public lines. Assume errors of hundreds of metres to about 1 km [Judgement]. Say "public approximate routes", never "actual cable routes", and do not claim "inside the 200 m zone" on the real scene, because the data is coarser than the zone. Great Belt 1 and GC3 may share a corridor |
| **Must stay synthetic** | The AIS-off event. AIS cannot count a vessel with no AIS, and the day showed zero gaps. Also the dark contact's camera observations and any cable-owner alarm, which must be labelled a mock feed |
| **Scene mismatch, disclosed** | The box has one major power cable, one minor 60 kV cable with zero crossings, and data cables. EDTH's "two power cables and a data cable" is met only loosely |
| **Estimated** | All crossing and look percentages, all [Scratch model] figures, all radio ranges (two-ray, flat sea, nothing measured), `r_detect` values, stand-off, retrofit box price, licence price, Baltic revenue, per-criterion scores, all hours |
| **Weak sources** | Market reports: no method readable. USD 5,300 a day is derived. Saildrone's Danish trial price is unknown. Fibre-sensing vendor claims are unchecked |
| **Unknown, ask** | Challenge owner, mentors, jury, prize, stage setup, own-laptop rule, hacking start, pre-existing code rule for Copenhagen (the FAQ is Paris 2026) |
| **Unknown, physical** | Coastline: no water mask, so land share and every station need a chart check. Current, wind and station-keeping are unmodelled. Bridge avoidance and collision avoidance are not modelled, and traffic-lane rule text was not verified, so check it before quoting. Whether Sprogø can host a mast |
| **Unknown, legal** | Danish baselines for the scene and whether the 200 m ban applies in each zone, so do not state a zone unless plotted and checked by a mentor. The 1857 regime needs a lawyer's reading. AIS time zone: treat as UTC, unverified |
| **Unknown, product** | Whether any operator accepts automatic start, even for watching. Boat makers' interest in third-party swarm software. Any real per-boat autonomy price |
| **Not modelled in the scratch runs** | Radio, slots, leases, battery, land, the deputy, cue tasks during the patrol run. Rebalance as written raised worst age on this horizon (18,260 s vs 14,460 s) in a 10-phase run, so measure whether it earns its place beyond fixing the idle boat |

## Conclusion

The research changed the shape of the project more than its details. Going in, the question was how to make a boat auction look original. Coming out, the answer is that the auction should be invisible and the honest cost of failure should be the product. Testing the plan on real water showed that two of its most quoted numbers were artefacts: the near-tie belonged to a drawing, and the 64.7% belonged to a boat no sailor would park there. Those corrections helped the team. Each removed a claim a sharp juror would have broken on stage, and together they produced a sharper one: fewer boats cannot close the gap, only choose where it lands, and a person should choose.

The weekend's real prize is what the guide says it is: a position to keep building (Onboarding PDF p.1). Almere on 13 to 15 November focuses on maritime security ([EDTH newsletter](https://pro.eurodefense.tech/p/funding-opportunities-six-november-hackathons)), and the EUDIS voucher's safe deadline is 16 November, though it needs a registered company and takes about 4% of applicants ([EUDIS](https://eudis.europa.eu/business-accelerator_en), [Starburst](https://starburst.aero/news/unveiling-of-the-20-companies-selected-for-the-third-cohort-of-the-eudis-business-accelerator/)). A second AIS day, taken before anyone quotes a rate, would test every threshold in this report for almost no effort, and it is the cheapest proof of seriousness available after Sunday.
