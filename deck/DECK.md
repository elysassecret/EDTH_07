# Deck v0 (markdown outline)

**File:** `<team number>_ElysasSecret.pdf`. The number is the team number, not the challenge number: **[TEAM NUMBER: ask Franco]**. Upload by Sun 11:30, hard deadline Sun 12:00.

**Rules for this file**
- Every measured number comes from `eval/` on the frozen `final` tag and stays **[from Sun 09:00 batch]** until then. `eval/results.md` holds the current preliminary numbers. They are not for slides while `run_batch` prints PRELIMINARY.
- Label each measured number truth (evaluator) or reported (shore).
- Say "cue for a look", never "suspicious".
- Prices are sourced or marked as team estimates. Every source is in `docs/research/buyers_market_manufacture.md`.
- No fake screenshots. **[SHOT: ...]** marks where a real one from the team console goes.

---

## 1. Title [pitch]

**Elysa's Secret. Challenge 07: Swarm Coordination for Collaborative Missions.**

"Fewer boats cannot close the gap, only choose where it lands."

**[SHOT: console, five USVs on the Great Belt chart]**

## 2. The problem [relevant problem]

One watch officer. A 25 by 10 km box of the Great Belt. Three cables under one of the busiest lanes in Danish waters.

- Christmas Day 2024: EstLink 2 failed about 12:26. Authorities first reached the tanker Eagle S by radio at 15:20. In October 2025 a Finnish court dismissed the charges for lack of jurisdiction, so no court has ruled on guilt.
- One fault costs EUR 50 to 60m (EstLink 2, estimate), and the owner may not recover it.
- Small patrol boats fail in ordinary ways: battery, radio, a boat that drops out. Someone has to reassign the work, or nobody does.

User: Navy Command watch officer in Denmark. **[TO CONFIRM with a mentor: `deck/mentor_log.md`]**

## 3. What we built [feasibility]

Five boats on the real Great Belt box. No coordinator: each boat runs the same code, auctions work, merges task tables and notices silent peers through leases. The shore sees only what the radio delivered.

| Real | Modelled |
|---|---|
| AIS day, 3 Nov 2026, anonymised | Radios, loss, delay |
| Public approximate cable lines (OSM) | Current, tide, battery |
| Lane measured from that AIS day | Synthetic dark contact, 2D sea |

**[SHOT: architecture figure from `docs/ARCHITECTURE.md`]**

## 4. Live break [feasibility, pitch]

A juror picks a failure. The swarm repairs what it can. The gap it cannot close stays on the operator's screen.

**[SHOT: judge-chosen failure, then the uncovered picket alert]**

## 5. The result [originality, feasibility]

Three modes on identical inputs, differing in one config key. Same warm state per seed. Truth.

Numbers from `eval/results.md`, `main` at `b922b40` with the #109 eval changes (same values as `86806cb`), 2026-11-07. Replace the revision from the `final` tag on Sunday.

| Truth, 5 seeds | static | off | elysa |
|---|---|---|---|
| Cable km overdue at end | 15.2 (14.6 to 15.2) | 3.3 (2.3 to 7.5) | 0.0 (0.0 to 1.7) |
| Mean km overdue, failure to end | 10.7 (10.2 to 12.2) | 1.0 (0.5 to 2.8) | 0.0 (0.0 to 0.4) |
| Worst sample age (s) | 24,328 | 16,249 | 11,106 |
| Failure to all segments owned | not reached | not reached | 60 s |

**30 paired seeds, off against elysa:** km overdue 6.7 vs 1.4 (median), elysa better in 30 of 30, equal 0, worse 0, median gain 4.8 km. Worst age better in 24, equal in 6.

**The cost, on the same slide:** after a loss we keep the cables at the cost of the south lane picket. Real cargo and tanker crossings in view after the failure: 9 of 9 without repair, 5 of 9 with it (worse in 20 of 30 seeds). The boats never see AIS; "in view" is the evaluator checking camera range against the private AIS day. Without repair the picket is empty too; the crossings stay in view only because boat 4 never moves.

**Energy and recovery, 30 paired seeds, truth:** no boat ever below its reserve away from Korsør in either mode (0 boat-seconds). Unserved task-seconds after the failure: 27,204 without repair, 6,945 with it, better in 30 of 30; what stays unserved with repair is the south lane picket. Recovery outcome: without repair "not recovered" in 30 of 30, with repair "cables only" in 30 of 30.

Sensitivities: at 3.0 m/s the gain holds (4.0 vs 0.1 km). At 4 km boat radio it shrinks (4.9 vs 2.6 km) and the contact is never handed to a watcher: say so.

## 6. The contact [originality]

Watching is pre-approved. Everything beyond watching waits for a person.

Timeline of the synthetic dark contact: detected, held, handed to a watcher, cannot hold when it leaves. Detected in 10 of 30 seeds at 2.3 m/s (4 of 5 at 3.0 m/s), and why not the rest: it depends on where the sweeper is in its loop. Handed to a watcher in 8 of 30, 3 to 30 minutes after it appeared. Never at 4 km radio.

Standing orders table: `deck/standing_orders.md`.

**[SHOT: Keep in view card and decision dock]**

## 7. Mass-manufacturability [mass-manufacturability]

**What is built is software plus one retrofit box.** Same box and software on many hulls. Copies cost almost nothing, so scale is limited by test and support.

| Per hull, one unit, low volume | Price | Basis |
|---|---|---|
| Compute Module 5 | from USD 67.50 | list price |
| Pixhawk 6X, if the boat has no autopilot | USD 269 to 423 | list price |
| Mesh radio, Doodle Labs class | USD 1,305 to 1,450 | listings; one reseller is far higher |
| Jetson Orin Nano class, optional | about USD 300 to 600 | team estimate |
| AIS, LTE, GNSS, antennas, enclosure, harness | EUR 500 to 1,500 | team estimate |
| **Total** | **about EUR 2,500 to 4,500** | verified core about USD 1,900 |

- The box talks MAVLink to the boat's autopilot, which keeps its own safety behaviour. ArduPilot already runs on boats such as BlueBoat.
- Assembled and tested by a Nordic EMS firm. No relationship exists yet.
- Every release runs through simulation in CI: the software version of a production line.
- Scale risks: radio supply, export licences, secure boot, proof that no restricted-origin parts are inside.

## 8. Business opportunity [business opportunity]

**Who signs:** in Denmark, Navy Command through the Ministry of Defence's acquisition agency. It holds surveillance, environmental response and rescue, so one buyer covers all three.

**Which budget:** the DKK 4bn Navy Plan (2025), for monitoring critical marine infrastructure among other things. Share for autonomous units not known.

**Precedent:** Sweden contracted four Saildrone Voyagers through NORDEFCO, 1,440 vehicle-days, with data as the service. The buyer pays per vehicle-day, about USD 5,300 implied by a US Coast Guard contract (our arithmetic; Sweden's price is undisclosed).

**Our model (team assumption, to test with mentors):** EUR 20,000 per boat a year plus EUR 60,000 per site, EUR 160,000 a year for a five-boat site, sold through boat makers and service operators. Compare a crewed guard vessel at EUR 4,000 to 8,000 a day.

**Path:** tabletop with a duty officer, then a harbour trial, a sea trial, a paid site pilot. Saildrone's Danish trial began in June 2025 and a contract was still being created in September 2026, so expect over a year. We complement wide-area sensors; we do not compete with them.

## 9. Size of opportunity [size of opportunity]

One market frame, then the honest steps down.

| Step | Figure | Status |
|---|---|---|
| Maritime situational awareness | USD 3.9bn (2025), USD 7.8bn (2034) | Fortune Business Insights; scope clear, method not visible |
| Uncrewed surface vessels | USD 0.82bn (2025), USD 1.59bn (2030) | MarketsandMarkets; hulls, not software |
| Baltic, licence only | EUR 2.6 to 5.1m a year | Our estimate: 8 states, 16 to 32 sites, 80 to 160 boats |
| Baltic, managed service via a partner | EUR 36 to 72m a year | Our estimate: EUR 1,500 per boat-day |

Baltic licensing alone is a single-digit million business. The multi-billion frame needs all small USV fleets, ports and offshore energy. Say that out loud.

Real contracts next to the reports: Sweden 1,440 vehicle-days; US Coast Guard USD 15.5m for 16 Voyagers (2026).

## 10. Achieved this weekend [feasibility]

Built between Friday and Sunday. As of `main` at `86806cb` on Saturday: 273 tests (271 pass locally on Windows, 1 POSIX-only), 70 PRs merged, features 1–25 checked in `deck/FEATURE_CHECKLIST.md`. Refresh from `git log` at the `final` tag.

- Swarm brain: task table, merge, auction, leases, relay, contact handling, energy modes.
- World: real scene, integer motion, current and tide, directed radio cuts.
- Console: offline chart, alerts, decision cards, narrator, evidence chain, incident report.
- Proof: warm-up, three-mode batch, fairness checks, seeded repeat, real AIS crossings, story tests.

**[SHOT: scorecard and test run]**

## 11. Limits and pre-existing work [feasibility]

**Limits:** simulation only. 2D sea, no sea state, modelled radios, public approximate cable lines, one AIS day. 3.0 m/s is above an Otter-class top speed of 4.5 kn. A small boat cannot follow a ship at normal speed. A dark contact is seen in only some runs. A civil trial needs permits, or a defence operator.

**Pre-existing work:** `deck/pre_existing_work.md`, final wording after the organisers confirm the rule.

## 12. Deployment [feasibility, mass-manufacturability]

1. A boat maker or operator bolts on the box.
2. Boats talk over mesh, with LTE near shore.
3. One console on shore approves and stops. Output feeds the existing operations room.
4. Boats launch from a harbour or Home Guard vessel, patrol a shift, return and charge. Shifts overlap.
5. Updates are signed. Logs give an evidence trail.

## 13. Roadmap: what comes next [feasibility, size of opportunity]

Every row is **proposed, not implemented** unless it says otherwise. Status as of `main` on Sat 7 Nov; refresh at the `final` tag. Source: `world/PRODUCT_BRIEF.md`, issues #103 to #114.

| Next step | What it adds | Status, said plainly |
|---|---|---|
| Gazebo testbed, stage 1 | One boat, one route in a fuller physics and sensor sim, through the same agent code | Proposed. An adapter and its tests are on `main` (#113), never run against a Gazebo install (`world/GAZEBO.md`) |
| ArduPilot SITL | The same agent driving a real autopilot in software, then a supervised real boat | Proposed, not implemented (#114, plan only) |
| Explainable assignments | Why this boat: travel time, energy left, the role it drops | One-line reason on the shore picture is on `main` (#102). The factor breakdown is proposed (#103) |
| Response-cost preview | Before approving: trip, energy left after, cable that goes overdue meanwhile | Proposed (#112, open). **A model estimate**: straight line, cruise speed, no current, shore-reported ages. Not a measurement |
| Energy management | Admit a task only if the boat can finish it and return with its reserve; hand over before the reserve is used | Proposed, not implemented (#104, #106). Will be judged on reserve violations, unserved task-seconds and recovery outcome, which `eval/` now measures (#109), never on "energy saved" |
| Independent runtimes | Each boat and the shore as separate processes; shore can stop, boats keep working | Partly: wire boundary on `main` (#113) with a smoke test (#109); separate processes and command reconciliation proposed (#105) |

Say on the slide: "Proposed, not built: these are the next steps, not this weekend's result."

**[SHOT: none; a table slide]**

## 14. Team and ask [pitch]

Javier: swarm brain. Simeone: world and data. Alexandru: operator console. Franco: proof and pitch.

**The ask: one supervised tabletop with a duty officer.**

**Video: [LINK, unlisted, tested signed out].** Map data © OpenStreetMap contributors (ODbL).
