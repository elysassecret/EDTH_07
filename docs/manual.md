# Team manual: what is on the screen and why

Read this once before pitching. Everything here is what the code actually does.

## 1. The map

- **The box.** A 25 × 10 km rectangle of the Great Belt between Funen and Zealand, long axis roughly north to south (rotated 165°). Corners, cable lines and the lane come from `data/scene-coordinates.json`. North arrow top right; Korsør naval station is outside the box to the east, so it is drawn clamped at the edge with an arrow. The box is water except Sprogø island, which we do not model (no land mask: say so if asked).
- **Cables (thin lines).** Five public lines from OpenStreetMap and TeleGeography. We patrol three: **H** = HVDC Storebælt I (400 kV power, north), **G** = Great Belt 1 fibre (data, south), **M** = the 60 kV Sprogø–Funen cable (small, south-west). The other two are drawn faintly for context. Each patrolled cable is cut into ≤5 km segments: H:0 H:1 H:2, G:0 G:1 G:2, M:0. The ribbon of dots along them is the **freshness**: green = a boat passed within 500 m recently, red = older than the 12,000 s target. That ribbon is evaluator data (ground truth), not what the shore knows.
- **The dotted band in the middle.** That is the shipping lane: the grey band is where 90% of cargo and tanker traffic actually sailed on 3 November (5th to 95th percentile offset, measured from AIS), the dashed line is its centreline. Ships of 20 m or more must use it. Nobody parks a 2 m boat in it, which is why the pickets sit 1.5 km west of it.
- **Grey triangles.** Real ships from the AIS replay, pointing along their course, fading with age. In Shore view you see only tracks that reached shore: its own 20 km receiver plus what boats relayed.
- **Circles around boats.** Faint big circle = camera detection range for a dusk-class contact (2,000 m). A boat sees a ship-sized target at 5 km by day and an unlit small craft at only 500 m at night; the demo uses the 2,000 m dusk value. The small 500 m "verify" range is what freshens a cable sample and what it takes to read a name.
- **Red diamond** = a contact without AIS. **"cue for a look"** circle = where an AIS track is predicted to cross a cable.

## 2. Boats, colours and roles

Five boats, 2.3 m/s (4.5 kn), 7 h endurance, camera, AIS receiver, 8 km radio (14 km to the shore mast). The colour is the boat's **mode**:

| Colour | Mode | Meaning |
|---|---|---|
| blue | PATROL | sweeping its cable segments, or holding a picket |
| purple | RELAY | parked at the relay station so the north can reach shore |
| orange | SHADOWING | keeping a contact in view at 1 nautical mile stand-off |
| amber | HOLDING | the scout that found a contact, watching until someone relieves it |
| grey | RETURNING | going home on battery; its tasks are released |
| dark | UNAVAILABLE | docked or dead |
| teal | CUE | going to look at a predicted cable crossing |

**Why these starting roles.** The brief says two boats scout the cables, two watch the lane, one relays. The mission file gives boat 1 the southern cables (G and M), boat 2 the HVDC (H), boat 3 the north picket, boat 4 the south picket, boat 5 the relay. That is only the starting hand: after that every boat earns work by bidding. Nothing is hard-wired.

**Pickets.** A picket is a fixed watch point on a cable where it crosses the lane, 1.5 km west of the lane centreline (outside the traffic). A picket boat sits still, sees every ship crossing that cable at that point, and is the cheapest boat to send anywhere, so it is also the fleet's spare. Pickets are the lowest-priority task: a picket boat that wins a cable segment or a contact drops its picket, and the screen then says **picket N/S UNCOVERED since …** and keeps saying it. That open gap is deliberate: with fewer boats you cannot close the gap, only choose where it lands, and the standing order says cables before lane.

**Link column** (Roles panel, shore picture): *direct* = shore heard this boat itself in the last 20 s; *relay (Ns)* = shore knows about it through another boat's heartbeat, N seconds old; *none (Ns)* = nothing for a while, data is N seconds stale. A cut link is drawn red and crossed on the map.

## 3. How work moves between boats (one paragraph)

Every 5 s a boat broadcasts a heartbeat with its whole task table. Hearing a boat (or hearing someone who heard it) renews its lease for 60 s. If the lease runs out or a task is released, the task is open. Every 12 s each boat bids once, on the first open task it is eligible for, in the order relay, contact, cue, segment, picket; the bid is "how long my patrol loop would be with this added" plus transit and a battery penalty. The cheapest bid wins and the winner publishes a claim with a version number; conflicting claims merge by a fixed rule (version, then claim beats release, then cheaper bid, then higher boat ID), so two boats that can talk always end up with the same table. An isolated boat cannot take over expired cable work (it needs to hear a majority). Every 5 minutes an overloaded boat hands one segment to the lightest peer.

## 4. The scripted story (seed 1)

| Sim clock | What you will see |
|---|---|
| 00:00–02:00 | Warm state: 1 and 2 sweep, 3 and 4 picket, 5 relays. Ages spread. AIS cues appear now and then. |
| 02:00:00 | Boat 1 low battery, goes home. Its four segments show as GAP. |
| 02:00:25–02:01:01 | Boat 4 wins G:0, G:1, G:2, M:0 one per slot and leaves picket S: "picket S UNCOVERED" stays on. |
| 02:02:00 | Boat 4's shore link is cut (red). Its row goes to *relay* via boat 5. Dark vessel starts loitering on the HVDC (truth view only). |
| ~02:05 | Boat 2 sweeps past, watches it 180 s, opens contact:C-07 and holds. Boat 3 wins it, leaves picket N, moves to stand-off. A card appears: Confirm / Stop; then Approve / Decline for closing in. |
| 02:33:20 | The vessel leaves at 6 kn: "cannot hold", report, boat 3 back to picket N. |
| 03:00:00 | Boat 4's link returns; tables reconcile. |
| 03:53:20 | Evaluate: scorecard pops up. |

## 5. Buttons

- **Pause / 5× 60× 240× / auto.** Auto runs 240× and slows to 5× for a minute around each scripted event.
- **Reset** with mode (static = pickets only, off = sweeps without reassignment, elysa = full) and seed. Same seed = identical run.
- **Shore view / Truth (evaluator).** Shore shows only delivered data: this is what the watch officer could legitimately see. Truth shows ground truth and is labelled.
- **Kill n / Rn.** Boat n goes silent (dead hull); R brings it back. After 60 s its tasks open and get re-auctioned.
- **Cut / Restore link a–b.** Cuts one radio link both ways. 4–shore is the scripted one; 5–shore isolates the north.
- **Battery low n / Go.** Forces boat n home.
- **Spawn dark contact at click.** Press the button, then click on the map. A synthetic AIS-off vessel appears there, drifting at 0.4 kn. **It shows only in the Truth view** until a boat sees it, because shore cannot know about a vessel nobody has reported. A contact is opened only if it is within 500 m of a cable (the click is snapped onto the nearest cable if you are within 3 km of one) and a boat passes within 2 km and watches it for 180 s. Place it on a cable a scout is heading toward and wait; the narrator panel tells you what happened.
- **Scorecard / Evidence check.** The scorecard is this run's numbers. Evidence check verifies every boat's signed log chain, then edits one line in a copy and shows the verifier catching it.
- **Keys.** Space pause, 1–5 kill/restore, r cut/restore the 5–shore link.

## 6. Panels on the right

- **What is happening.** Plain-language narrator (evaluator side): every claim, release, failure, detection and operator action in one sentence with the reason. Use it to pitch.
- **Roles.** Mode, tasks, battery, link per boat, as shore sees them.
- **Pickets.** Covered or UNCOVERED since when.
- **Cable ages.** Worst age per segment against the 12,000 s target, listed in the order the config names the cables (H, M, G). Below: km overdue (the headline), worst age, lane crossings in camera view.
- **Decisions.** Operator cards. Delegated tier: Confirm or Stop. Held tier: Approve or Decline; nothing happens until you press.
- **Tasks.** Owner, version, deputy, state per task; GAP with seconds for open segments and pickets.
- **Events.** The shore's own event log.

## 7. Would it work elsewhere?

Yes, the code is scene-agnostic: `data/scene-coordinates.json` holds the box (centre, bearing, size), the cable polylines, the lane centreline with its width, and the stations; `config/default.toml` holds the rest. A new strait means a new JSON from OSM cable lines plus one day of AIS to measure the lane, then `python -m tools.scene_check` to confirm stations are water and the radio graph connects. What is **not** modelled anywhere: coastline, islands, currents, sea state, collision avoidance. We say that openly.

## 8. Ranges in one place

| Thing | Value | Why |
|---|---|---|
| Boat speed | 2.3 m/s (4.5 kn) | Maritime Robotics Otter top speed; 3.0 m/s as sensitivity |
| Endurance / reserve | 7 h / 30 min | brief; return rule fires when reserve + trip home is all that is left |
| Camera detect | 2,000 m dusk (5,000 day ship, 1,500 small craft, 500 unlit night) | judgement values, stated as such |
| Camera verify | 500 m | pixel geometry for reading hull marks |
| Keep-in-view / stand-off / floor | 2,000 / 1,852 / 500 m | 1 nm stand-off is the only published shadowing distance |
| AIS receive | 20 km Class A, 8 km Class B | VHF horizon from a 1.5 m antenna |
| Radio | 8 km boat–boat, 14 km boat–shore mast, 5% loss, 0.25–1 s delay, 4 hops | two-ray model, nothing measured |
| Heartbeat / lease / slot | 5 s / 60 s / 12 s | fits a narrowband link |
| Dwell rule | no AIS match, under 1 kn, within 500 m of a cable, 180 s | the brief's loiterer |
