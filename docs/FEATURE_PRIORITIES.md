# Challenge 07: Blue Shadow, energy modes, feature priorities

Companion to [BUILD_PLAN.md](BUILD_PLAN.md). Nothing here overrides that plan's honesty rules, cut list or timeline. New items are marked **NEW** with an hour estimate (judgement).

---

## 1. BlueShadow: who they are and where we fit

**Facts (public sources, Nov 2026):**
- Copenhagen company. Founder/CEO Charles Maher, described as a former US Navy submarine officer. CTO Maksym Hrebinnyk.
- **Shore platform:** a common operating picture with fusion of AIS, radar, EO/SAR/IR, SIGINT/ELINT and OSINT, a *Contact Correlation Engine* (dark-ship detection), a *Threat Assessment Engine* (vessel threat scores, critical-infrastructure risk scores), and an *AI Event Response Engine* that opens "event rooms", sends alerts, and "deploys drones based on threat severity". Customers listed: navies, coastguards, subsea cable owners, wind farms, ports and insurers. Their own use case is a cable-cutting scenario for a Nordic telecom.
- **BlueShadow Edge:** an autonomy module on each USV of their *Blue Dragon* swarm. Blue Dragon intercepts Shahed drones 10–20 km off Odesa. Vessels share a picture, each computes its own kill probability, the swarm assigns engagements, and the swarm is self-healing: lose one boat and the rest continue. The design is 12-boat squadrons (10 at sea, 2 in maintenance) with 5 shore staff. In mid-2026 Edge was "not yet live", with the first unit deployment expected spring 2027.

**What this means for us:**
- "They do monitoring, we do the swarm brain" is **not quite true**. Their Edge module *is* a swarm autonomy layer, but for **air-threat interception** (a kill chain, minutes long). Ours is for **persistent patrol of infrastructure** (hours long, with energy limits, coverage gaps and a human approving decisions). Say the difference precisely, or a juror who knows them will catch it.
- **Positioning line:** "Platforms like a shore COP raise the alert. We decide which boat goes, keep the rest of the cable watched, and show what that choice costs."
- They are a **natural integration partner**, not a competitor to attack: their Event Response Engine "deploys drones", and our brain could take that alert and turn it into one boat's task.
- **Do NOT claim a partnership, endorsement or customer relationship.** The most we can say is "we spoke to people at the event working on this", and only if true.
- **Ask Maher or his team (mentor round):**
  1. Would a shore COP like yours want to hand a task to a patrol swarm through an API? What format?
  2. What kills small USVs on 24/7 rotation: battery, weather, fouling or comms?
  3. Is "watching is pre-approved, everything else waits for a person" acceptable to a navy?
  4. How do you plan the 10-at-sea / 2-in-maintenance rotation? (This feeds feature 31.)

**Sources:** [blueshadow.dk](https://www.blueshadow.dk/) · [RBC-Ukraine on Blue Dragon](https://newsukraine.rbc.ua/analytics/blueshadow-unveils-sea-drone-system-designed-1783068417.html) · [ua.news](https://ua.news/en/world/danska-kompaniia-rozrobila-sistemu-blue-dragon-dlia-zakhistu-odesi-vid-shakhediv) · [Odessa Journal](https://odessa-journal.com/public/how-a-swarm-of-blue-dragon-sea-drones-will-defend-odessa-from-shahed-drones)

---

## 2. Energy system: "Sentinel" low-power modes

**The idea in one line:** a boat that doesn't need to move should stop driving. It drifts as a floating sensor (a "satellite"), keeps its camera, AIS and radio on, and saves its battery for when it matters or for a better moment to go home.

**Why it is physically real:**
- Propulsion power grows roughly with the **cube of speed** through the water. Halving speed cuts propulsion power about 8×. Stopping leaves only the "hotel load" (sensors, radio, computer), which is far smaller than propulsion [judgement; measure on a real hull].
- **Current and wind decide the cost of going home.** A boat at 2.3 m/s (~4.5 kn) against a 1.5 kn current makes ~3 kn over ground, so the trip home takes about 1.5× longer and costs about 1.5× the energy. Great Belt currents are often significant [verify the typical range with a mentor or DMI before quoting a number].
- The research report lists current, wind and station-keeping as **unmodelled**. This closes that gap and answers the juror question "what kills a small USV out there?"

**Modes (state machine):**

| Mode | Propulsion | Sensors / radio | Used for | Who decides |
|---|---|---|---|---|
| PATROL | Cruise speed | All on | Cable sweeps | Swarm (auction) |
| ECO | Reduced speed | All on | Long transits, low battery | Swarm, automatic |
| **SENTINEL** (drift-and-correct) | Off. Motors pulse only when the boat drifts outside a radius (e.g. 300 m) of its station | All on | **Pickets, relay**: anything stationary | Swarm, automatic |
| **DORMANT** (deep standby) | Off, drifting freely in a safe area clear of the lane | AIS receive + slow heartbeat (e.g. 60 s). Camera off; wakes on a cue or a command | Waiting for favourable current, or a near-empty battery holding position as a sensor | **Delegated under standing order:** starts at once, operator can Confirm/Stop |
| RETURN | Cruise speed (ECO if needed) | All on | Going home to charge | **Automatic safety tier:** cannot be stopped |

**Rules the brain follows:**
1. **Current-aware return rule (replaces the fixed-time rule).** Return when `battery ≤ (energy to reach Korsør against forecast current + hotel load + reserve) × 1.2`.
2. **Mode changes the bid.** A SENTINEL or DORMANT boat bids cheaply on stationary tasks (picket, relay) and does not bid on sweeps. Energy state changes which jobs a boat takes, with no special-case code: the cost goes into the existing `bid_cost`.
3. **Wait-or-go decision.** If going home now costs more than waiting for the current to turn, and the battery can carry the hotel load until then plus a margin, the boat proposes DORMANT ("Hold at drift station for 40 min, return on the tide"). The operator sees it as a Confirm/Stop card.
4. **Never DORMANT inside the shipping lane** or within the cable stand-off of a contact.

**What the dashboard shows:**
- Battery as **time and range**, not percent: "2 h 10 min · must return by 14:20 Z".
- A mode chip on each USV card (PATROL / ECO / SENTINEL / DORMANT / RTB).
- A **current arrow layer** and the projected route home.

**Data:** use a fixed current/wind field in the sim (one direction, plus a tide flip at a set time). Real forecasts can come later from the DMI open-data service or Copernicus Marine [verify access].

---

## 3. Pattern of life: honest scope

**What it is:** learning what normal traffic looks like (where ships go, how fast, where they stop) so that unusual behaviour stands out (slow over a cable, off the lane, loitering).

**Why it's secondary:**
- The team has **one AIS day**. The report says thresholds were set and tested on the same day and that 9 events can't separate results.
- AIS anomaly detection is **common hackathon work** and is sold by Windward and others.

**How to make it credible later:** download 2–4 weeks of free Danish Maritime Authority AIS data. Build a grid of normal speed and heading per cell, then flag deviations as **cues**: "cue for a look", never "suspicious". Feed them into the existing `cue:` task type.

---

## 4. Challenge 02: modular add-on ("Triage")

**What 02 asks:**
- Score and rank **vessel-days** near cables using anchor-drag signs: slowing, dwelling, heading changes, and track geometry over a cable.
- Show the **evidence** behind each score.
- Cut the existing ~170 alerts/day down while still catching documented cuts.
- Judged on **how high the held-out real cut events rank** and **alerts/day at your threshold**. Explainability breaks ties.
- Data: historical DMA AIS plus EMODnet cable routes.

**How it fits 07:** perfectly, as the layer *before* the swarm.
- **02 answers "which ship deserves a look?"**
- **07 answers "which boat goes, and what does that cost the patrol?"**
- Combined line: *"From 170 alerts a day to a short ranked queue, and a boat on the top one, with the patrol gap shown."*
- It replaces secondary features 26 (AIS cues) and 32 (pattern of life) with one stronger module. The research notes already found the real drag signature: ship under way, usually **AIS on**, slowing as the anchor drags.

**Recommendation: "02-lite" inside the 07 product, not a full 02 entry.**
- A full 02 entry needs many days of Baltic AIS (large downloads), a clean evaluation, and a person full-time. The 07 plan has no spare person.
- 02-lite: an explainable score on the AIS you already have, a **ranked triage queue** on the dashboard, and the top items become `cue:` tasks for the swarm.
- **Cost:** B's existing 5.5 h AIS/cue budget, plus about 2 h for C's queue panel.
- **Still only after features 1–25 are green and the video is recorded.**

**Score design (explainable by construction):**

| Feature | Signal | Example evidence text |
|---|---|---|
| Speed drop near cable | Transit speed → under ~3 kn within ~1 km of the cable | "Slowed 11.2 → 2.1 kn, 600 m from HVDC" |
| Dwell | Minutes within the cable buffer | "38 min within 1 km of cable" |
| Heading instability | Heading variance / zig-zag while slow | "Heading changed 5× in 20 min" |
| Track–cable geometry | Crossing the cable several times, or running along it | "Crossed cable 3×; ran parallel for 2.4 km" |
| Off-lane | Distance from the normal lane at that point | "1.8 km west of the usual lane" |
| AIS gap | Missing reports while near the cable | "No AIS for 22 min near cable" |
| Routine discount | Known routine types or behaviour lower the score: cable/survey ships, pilots, SAR, ferries on schedule, fishing in normal fishing cells | "Pilot vessel: routine, score reduced" |
| Rarity (pattern of life) | How unusual this behaviour is for this cell, vs 2–4 weeks of history | "Slower than 98% of ships here" |

- **Score:** a weighted sum of features, each shown as a bar, so the explanation is the score itself.
- **Threshold:** choose it by daily volume ("top N per day an analyst can clear in a shift"), and report alerts/day at that threshold.
- **Never** score on flag or ownership, and never use the words "hostile" or "suspicious". The queue says "review".

**Dashboard additions (C):** a **Triage queue** tab. Each card shows rank, score bars, the track segment drawn on the cable, the evidence text, and "Send a boat to look", which creates a `cue:` task and shows the cost to the patrol.

**To confirm with organisers:**
1. Can a team submit to two challenges, or present 02 as part of 07?
2. Which documented cuts fall inside DMA AIS coverage? Several were outside Danish waters.

---

## 5. Feature priority list

**Features 1–25 = the product we build and demo this weekend.** Ranked by importance; if time runs out, cut from the bottom of each block, never from the top.
**Features 26+ = "in development" on the slides.** Present them as designed, not built. Show a diagram, never a fake screenshot.

### Main product (1–25)

**Swarm brain and world (owners A/B)**

| # | Feature | Why it's here | Plan ref |
|---|---|---|---|
| 1 | Real Great Belt scene: cables, lane, Korsør, 25 × 10 km box | Credibility | Scene |
| 2 | Five boats on 2+2+1 roles: 2 cable sweeps, 2 lane pickets, 1 relay | The brief, literally | Task set |
| 3 | Revisit age per cable segment | Basis of every metric | M7a |
| 4 | Deterministic reset and seeded runs | Repeatable demo and numbers | D1–D3 |
| 5 | Decentralised auction with battery in the bid, no coordinator | Core of "swarm brain" | M4a |
| 6 | Low battery → return home, tasks re-auctioned | Brief event 1 | M1b, M4a |
| 7 | Range-limited radio, peer hops, store-and-forward | Brief event 2 | M2a/b |
| 8 | Relay as a role another boat can take over | Brief: comms relay | M5 |
| 9 | Split/rejoin merge rule | Doesn't break when the link returns | M3, P4–P5 |
| 10 | Dark contact: detect, nearest free boat keeps it in view, scout holds until relieved | Brief climax | M6 |
| 11 | The remaining gap stays visible and is never hidden | Honesty rule and the core insight | S5 |
| 12 | Three-mode baseline runner and headline metric (cable km overdue + lane crossings in view) | Proves it works | M7b |
| 13 | Live failure injection: any boat, any link | Demo moment | Step 14 |
| 14 | Four-tier operator policy | "Approves decisions instead of steering" | Policy |
| 15 | **NEW** Current-aware return rule (fixed current field) | Energy realism, answers "what kills a USV" | B, ~1.5 h |
| 16 | **NEW** SENTINEL drift-and-correct mode for pickets and relay | Big endurance gain at low cost | A+B, ~1.5 h |

**Operator dashboard (owner C, you)**

| # | Feature | Why it's here |
|---|---|---|
| 17 | Offline chart with infrastructure layers | Foundation; no Wi-Fi dependency |
| 18 | USV cards: role, **mode chip**, battery as time + must-return-by, link, data age | Fleet at a glance |
| 19 | Contact tracks: AIS / camera-only "NO AIS" / fused, trails, seen-by | Shows what the swarm knows |
| 20 | Data-age honesty: stale boats greyed at last-known position, "LAST SEEN 02:14" | Never shows old data as live |
| 21 | Comms overlay: who links to whom, lost links crossed | Explains why a boat is cut off |
| 22 | Decision cards: Confirm/Stop and Approve/Decline, with a ghost-route preview | The operator's main job |
| 23 | Alerts in 3 levels (alarm/warning/caution), with acknowledge and deduplication | Real maritime alert practice |
| 24 | Coverage/revisit overlay and the headline number on screen | Makes the gap visible |
| 25 | Auto-warp (240× / 5× around events), event log, "FEED LOST" banner, **EXERCISE** banner on injected failures | Watchable demo; reliability |

### Secondary (26+, "in development" on slides)

Ranked in the order to add them if 1–25 are done early.

| # | Feature | Note |
|---|---|---|
| 26 | Real AIS replay + **02-lite triage**: explainable score, ranked queue, top items become cue tasks | The plan's first P1, merged with Challenge 02. Add first |
| 27 | Named deputy for relay/contact | Plan P1 |
| 28 | Evidence hash-chain and one-click incident report | Plan P1. A cable owner or navy would pay for this |
| 29 | **DORMANT mode and wait-for-current decision** | The full "satellite" idea; operator-confirmed |
| 30 | Wind/current layer from real forecasts (DMI / Copernicus) | Replaces the fixed field |
| 31 | Battery rotation scheduler: always N boats at sea, 24/7 | Same logic as the 10-at-sea/2-in-maintenance squadron model |
| 32 | Pattern-of-life rarity feature for the triage score (2–4 weeks of AIS) | Needs more data first |
| 33 | Day/dusk/night display modes | Easy polish; real ship-display practice |
| 34 | Replay scrubber and shift-handover summary | |
| 35 | Contact dossier: AIS data, AIS-off time, dwell, nearest ETA | |
| 36 | "Request manned asset" radio-ready text | Handoff to the Navy |
| 37 | Degraded GNSS mode with uncertainty circles | Baltic GNSS jamming is real |
| 38 | Spoofed-boat test | Plan P2 |
| 39 | Integration API: send tasks and tracks to an external COP | The BlueShadow-type integration |
| 40 | MAVLink bridge to one ArduPilot SITL boat | Proof it plugs into real autopilots |
| 41 | Full Challenge 02 entry: multi-day Baltic evaluation | Only if organisers allow two entries and 1–25 are done |

**Still cut (unchanged):** hardware radios, drone, Gazebo VRX, CBBA, lane sweeping.

---

## 6. Time cost and risk

- New main items 15–16 add about **3 h** to a plan that already uses ~82 of 84 focused hours. **To pay for them,** move the manual-operator comparison run to secondary, or drop fallback-branch variations; both are already early in the cut order. **Decision needed from the team on Friday.**
- If item 15 or 16 slips past Sat 18:00, it drops to secondary under the plan's hard fallback rule.

## 7. Slide wording

- **"Built this weekend":** features 1–25 with real screenshots and real seeded numbers.
- **"In development":** 26+ as a roadmap, with the energy state-machine diagram labelled "designed, not yet built".
- Never: "partnered with BlueShadow", "prevents sabotage", "detects dark ships" (the dark contact is synthetic), or any invented energy saving percentage. Say "drift mode removes propulsion load while stationary; savings to be measured on a hull".
