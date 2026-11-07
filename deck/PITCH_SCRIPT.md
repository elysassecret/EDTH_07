# Pitch script: three minutes, spoken

Owner: D (#89). What the presenter says while the screen shows the demo. About 400 words; read at a calm pace it lands near 2:50. **Read it aloud once with a stopwatch and write the time at the bottom.** Beat order and times follow `server/DEMO.md`. Every number is from `eval/results.md` (30 paired seeds, `main` at `86806cb`) and is **truth**, the evaluator's measurement; on Sunday replace them from the `final` tag run (`deck/runbook.md`). Slide-only material (market, price, team) lives in `deck/pitch.md` and `deck/DECK.md`.

Bold = say it. *Italic = what is on screen or what you do.*

---

**0:00 Problem** *(console paused at 12:10Z, five boats on the Great Belt chart)*

**One watch officer on shore. A 25 by 10 kilometre box of the Great Belt, three cables under one of the busiest lanes in Danish waters, and five small uncrewed boats. Boats fail in ordinary ways: a battery runs low, a radio drops out. Someone has to reshuffle the work, or nobody does.**

**0:20 What we built** *(press Run)*

**The boats share out the work themselves. No boat is in charge: each one bids for tasks, the cheapest bid wins, and a silent boat's tasks go to someone else. The officer does not steer. The officer approves.**

**0:35 Beat 1, battery** *(12:15Z: USV 01 heads home, 04 takes the cable, "Lane picket S uncovered")*

**USV 01 is low on battery and goes home to Korsør. Within a minute, USV 04 has taken its cables. That leaves the south lane picket empty, and the screen says so. We never hide the gap.**

**0:55 Beat 2, link** *(12:17Z: red cross on 04's link to shore)*

**Now 04 loses its link to shore. It keeps working, and its reports still arrive through the relay boat.**

**1:05 Beat 3, contact** *(12:26Z to 12:29Z: NO AIS contact, keep-in-view, the HELD card)*

**A contact with no AIS stops on the power cable. That is a cue for a look, nothing more. A boat keeps it in view from outside one nautical mile; that is pre-approved. Closing to 500 metres is not. It waits for a person.** *(Approve, press Enter.)* **I approve. I have five seconds to undo.**

**1:35 Beat 4, relay** *(13:20Z: 05 off, 02 and 03 greyed with "… ago")*

**Now we switch off the relay boat. Two boats go grey: the shore cannot hear them, so it shows where they were and when, never where they might be. Then another boat takes over the relay, and they come back.**

**1:55 The number** *(results slide, or Evaluator view)*

**We ran thirty paired seeds, same start, with and without repair, measured by an evaluator that sees the truth. With repair, the median cable left overdue at the end is 1.4 kilometres. Without it, 6.7. Better in all thirty seeds.**

**2:15 The trade-off** *(same slide, second row)*

**It costs something, and we show it. To keep the cables fresh, the boat on the south lane leaves its post. Real ships crossing within camera range after the failure: 9 of 9 without repair, 5 of 9 with it. Fewer boats cannot close the gap, only choose where it lands.**

**2:35 Limits** *(limits slide)*

**This is simulation: a flat sea, modelled radios, public approximate cable lines, one real AIS day. The boats never see AIS. With shorter four-kilometre radios the gain shrinks and the contact is never handed over.**

**2:50 Ask**

**If you run a patrol or a cable, give us one supervised tabletop with a duty officer.**

---

## Number sources (check before every read-through)

| Said | `eval/results.md` row | Label |
|---|---|---|
| 30 paired seeds; 1.4 vs 6.7 km; better in 30 of 30 | Headline, "Cable km overdue at end" | truth |
| 9 of 9 vs 5 of 9 crossings in view | Headline, "Real cargo and tanker crossings in view after T" | truth |
| Gain shrinks at 4 km radio, contact never handed over | Sensitivities, "km overdue, 4 km boat radio", "Watcher in view of C-07" | truth |
| 1 nm, 500 m, 5 s undo | `config/boat.toml`, `deck/standing_orders.md`, the console | config, not measured |

The trade-off sentence is the one agreed on #68 (copied in `eval/results.md`, "The trade-off"). The limits sentence is `deck/DECK.md` section 11, shortened.

## Never say

"suspicious", "hostile", "detects dark ships", "coverage restored", "prevents sabotage", "court-ready", "one operator can run five boats". Never quote a number from a live run: the live demo is one seed.

## Read-through log

| Date | Reader | Time | Notes |
|---|---|---|---|
| | | | |
