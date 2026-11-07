# The pitch: three minutes that score all seven criteria

About 350 spoken words. Demo early, so a failure still leaves time for the scored material. Never name a real vessel in connection with suspicion. Replayed AIS tracks are anonymous IDs. Measured numbers stay [from Sun 09:00 batch] until the final run.

| Time | Beat | Say or show | Criterion |
|---|---|---|---|
| 0:00–0:20 | Person and problem | "For the one watch officer covering 25 by 10 km of the Great Belt, we built the brain that lets five small boats reorganise themselves when things break." Real map on screen | Problem |
| 0:20–0:35 | Why now | "On Christmas Day 2024 the EstLink 2 cable failed at about 12:26. Authorities reached the tanker by radio at 15:20. No court has ruled on guilt." | Problem |
| 0:35–1:10 | Live moment | Ask a juror: "Which boat do we lose?" One click in the Exercise panel. Repair runs; the gap stays visible. "The lane boat takes the cable, and that picket stays open on screen." | Feasibility, pitch |
| 1:10–1:40 | Insight and number | "Fewer boats cannot close the gap, only choose where it lands." Scorecard: three modes, seeds, median and range. Cable km overdue [from Sun 09:00 batch]. Say that lane crossings in view do not improve | Originality |
| 1:40–2:00 | Real versus modelled | Real AIS day, public approximate cable lines, synthetic dark contact, 2D sim, modelled radios. "A mentor told us X, so we changed Y" | Feasibility |
| 2:00–2:35 | Scale and money | Retrofit box on any ArduPilot boat, EMS build; buyer Navy Command; per-boat licence plus site subscription; market frame and the honest Baltic-only number | Manufacturing, business, size |
| 2:35–2:50 | Team | What four people built this weekend, real facts only [from Sun 09:00] | Pitch |
| 2:50–3:00 | Ask | "If you run a patrol or a cable, talk to us today about one supervised tabletop with a duty officer." | Pitch |

## Demo

```bash
pnpm --dir web build
uv run python -m server --serve-web --demo
```

Open `http://localhost:8765/?operator`. Shot list and timings: `server/DEMO.md`. The juror names a boat. If nobody answers in 3 s, switch off the relay, USV 05. At 1:10 on the stopwatch move on whatever is on screen. A live run is exploratory: it starts cold on seed 1, so quote numbers only from `scorecard.md`.

## Failure ladder, rehearsed

1. Live laptop, no venue internet needed.
2. Software freezes: "That's the sim. Here is the same failure recorded earlier." Cut to the clip within 5 s and say it is a recording.
3. The mandatory video linked in the deck.
4. A static results slide.

If only the organisers' machine is allowed, show the video, state the seeded result and offer the pick during questions.

## Lines for the scored criteria (every price is sourced or said as an estimate)

- Deployment: "Boats launch from a harbour or Home Guard vessel, patrol a shift, return and charge. The box talks MAVLink to the existing autopilot, which keeps its own safety behaviour. One console on shore approves and stops."
- Real-world limit: "This is simulation. A civil trial needs a permit, or a defence operator."
- Night: "An unlit vessel at night is a weak case for a visible camera. The sim's detection radius drops to 500 m, and we say so."
- Manufacture: "Software plus a EUR 2,500 to 4,500 retrofit box of off-the-shelf parts, our estimate, built by a Nordic EMS firm, on any ArduPilot boat."
- Buyer: "In Denmark that is Navy Command, which holds surveillance, environmental response and rescue."
- Model: "Per-boat licence plus site subscription, through boat makers and service operators: EUR 160,000 a year per five-boat site, proposed."
- Market: "Maritime situational awareness is about USD 3.9bn in 2025; USV hulls about USD 0.8bn. Baltic licensing alone is EUR 3 to 5m a year, our estimate, which is why this has to spread to all small USV fleets, ports and offshore energy."

Do not say: "first", "we detect dark ships", "they are centralised", "no radio traffic", "court-ready", "tamper-proof", "blockchain", "one operator can run five boats", "prevents", "hostile", "suspicious", "actual cable routes", "Denmark bought Saildrones", "we partner with".
