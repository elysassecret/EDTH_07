# Demo video: one command, shot list, narration (owner: C)

Code freeze Sun 10:00, video uploaded by 10:30 (unlisted, link tested signed out). Alexandru
records; nobody uploads from this repo.

## Run it

```bash
pnpm --dir web build                               # once, after any web/ change
uv run python -m server --serve-web --demo         # real sim, preset in server/demo.toml
```

Open **http://localhost:8765/?operator**. `?operator` hides the evaluator and truth switches,
so the screen is the watch officer's. For the evaluator shots, open a second window without
`?operator` and press **Evaluator OFF → ON**.

The run starts **paused at sim 6900 s (12:10:00Z)**. Start the screen recording, then press
**Run**. To retake, stop the command (Ctrl+C) and run it again: every start is the same seed,
the same tape and the same injection, paused at the same moment. The run log of each take lands in
`runs/` and can be checked with `uv run python -m server.replay runs/<file>.jsonl`.

What the preset does (`server/demo.toml`): seed 1; `scenarios/fixed.toml` (battery low 7200 s,
link 04→shore cut 7320 s, synthetic contact C-07 placed 7320 s and departing 9200 s, link back
10 800 s, evaluate 14 000 s); one injected exercise failure, **USV 05 (relay) switched off at
11 100 s**; 240× between events, 6× within 60 sim-s of an event and in four short extra
windows around the keep-in-view and relay beats. The whole run takes about 2:26 after Run.

## Shot list

Times: **video** = seconds after pressing Run, computed at the feed's 10 frames per second on
the preset (a slow laptop can stretch them a little; the sim times do not move). Sim times
measured on seed 1, 7 Nov 2026, and checked by `tests/server/test_demo.py`.

| Video | Sim time (UTC on screen) | What happens on screen | Brief beat |
|---|---|---|---|
| 0:00 | 6900 s (12:10Z) | Paused. Five USVs: 01 and 02 sweep cables, 03 and 04 picket the lane, 05 relays. Coverage box top left | Setup |
| 0:11 | 7200 s (12:15Z) | EXERCISE banner. USV 01 low battery → RTB chip, "Return to Korsør"; caution alert. 04 takes `seg:G:*` (card: "Cable sweep (Great Belt 1 fibre, 60 kV …)"); "Lane picket S uncovered" caution | Battery low and reassign |
| 0:31 | 7320 s (12:17Z) | Link 04 → shore cut: red ✕ "LINK CUT". 04's card: "Via peer"; its reports keep arriving through 05 | Link loss, store-and-forward |
| 0:44 | ~7865 s | USV 02 chip turns KEEP IN VIEW (warp slows) | Dark contact |
| 0:48 | ~8052 s | USV 03 card: "Keeping C-07 in view"; "Lane picket N uncovered" caution | Keep in view, handover |
| 0:52 | ~8265 s | USV 02 relieved: chip back to PATROL, cable sweep again | Scout holds until relieved |
| 1:08 | 9200 s (12:48Z) | C-07 departs (truth only). By ~9260 s (1:18) USV 03 is back on "Lane picket N" | Contact leaves |
| 1:32 | 10 800 s (13:15Z) | Link 04 → shore restored; 04 "Direct to shore" | Rejoin |
| 1:51 | 11 100 s (13:20Z) | EXERCISE: USV 05 (relay) switched off | Relay loss |
| 2:01 | ~11 160 s | 02, 03 and 05 grey out: "LAST SEEN …", warning alerts. The shore shows them as old, never as live | Shore picture goes stale |
| 2:12 | ~13 305 s (13:57Z) | Shore hears 02 and 03 again; 03's card now says "Relay" | Relay takeover |
| 2:26 | 14 000 s (14:08Z) | Evaluate. Coverage box: oldest cable visit and "Cable zone gap open"; both lane pickets open in alerts | Remaining gap shown |

Evaluator cut-ins (second window, Evaluator ON): at ~0:48 the purple ring "C-07 · truth only,
not on shore picture"; at ~2:05 purple rings show where 02 and 03 really are while the shore
still shows their last reports ("true 02 · … m off"). Say "evaluator view" when it is on screen.

## Narration (honest wording)

Read at a calm pace; every line matches something on screen. No numbers that are not on screen.

1. **0:00** "Five uncrewed boats patrol three cables in the Great Belt. The boats share out the
   work themselves; the watch officer approves decisions instead of steering. This is our
   simulator, seed 1, sped up."
2. **0:11** "USV 01 runs low on battery and heads home to Korsør. Its cable segments go to
   auction; USV 04 wins them. That leaves the south lane picket open, and the console says so."
3. **0:31** "Now 04 loses its link to shore. It keeps working, and its reports still reach shore
   through USV 05. The cut link stays visibly crossed."
4. **0:44** "A synthetic contact with no AIS stops on the HVDC cable. USV 02 keeps it in view
   until USV 03 arrives to take over; then 02 goes back to its sweep. That's a cue for a look,
   nothing more."
5. **1:08** "The contact leaves faster than our boats. 03 lets it go and returns to its picket."
6. **1:32** "04's link to shore comes back."
7. **1:51** "Now the relay boat, 05, is switched off. Boats 02 and 03 can't reach shore, so the
   console greys them out and shows when they were last heard. Old data never looks live."
8. **2:12** "USV 03 has taken over the relay role, and the shore hears both boats again."
9. **2:26** "We don't hide what's left: the console still shows the oldest cable visit and the
   open gap."

Never say "suspicious", "hostile", "detects dark ships", "coverage restored", "court-ready" or
"prevents sabotage".

## Known limits on the real sim (say them, or leave the beat out)

- **No approval card on the real sim yet.** The shore picture (`agent/shore.py`) sends no
  contact and no pending decisions, so the Confirm/Stop and Approve/Decline cards and the contact
  symbol never appear. Options: skip the card beat, or record it from `--mock` where the top bar
  says **MOCK FEED** and say "mock feed" in the narration. Needs Javier (A) for the real thing.
- **seg:M:0 shows "none since start" (shore-reported).** The shore never credits a visit to that
  segment (issue #22), so the headline names it. That is what the shore knows; don't explain it
  away on camera.
- "Cannot hold" and "Name NOT READ, Anchor NOT SEEN" only exist in the mock.
- Video times are approximate; re-time after any change to `agent/`, `world/` or the preset.
