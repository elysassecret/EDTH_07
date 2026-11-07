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

| Truth | static | off | elysa |
|---|---|---|---|
| Cable km overdue at end | [from Sun 09:00 batch] | [from Sun 09:00 batch] | [from Sun 09:00 batch] |
| Mean km overdue, failure to end | [from Sun 09:00 batch] | [from Sun 09:00 batch] | [from Sun 09:00 batch] |
| Worst sample age | [from Sun 09:00 batch] | [from Sun 09:00 batch] | [from Sun 09:00 batch] |
| Failure to all segments owned | not reached | not reached | [from Sun 09:00 batch] |

Seed by seed: elysa better in [k] of [n], equal in [k], worse in [k].

Say what repair did not do: it does not lower the worst age much, and lane crossings in view do not improve. Use paired seeds for off against elysa, median and range, never one seed.

## 6. The contact [originality]

Watching is pre-approved. Everything beyond watching waits for a person.

Timeline of the synthetic dark contact: detected, held, handed to a watcher, cannot hold when it leaves. Detected in [k] of [n] seeds, and why not the rest: it depends on where the sweeper is in its loop. **[from Sun 09:00 batch]**

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

Built between Friday and Sunday. Replace with final facts from `git log` at the `final` tag: **[tests passing, PRs merged, from Sun 09:00]**

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

## 13. Team and ask [pitch]

Javier: swarm brain. Simeone: world and data. Alexandru: operator console. Franco: proof and pitch.

**The ask: one supervised tabletop with a duty officer.**

**Video: [LINK, unlisted, tested signed out].** Map data © OpenStreetMap contributors (ODbL).
