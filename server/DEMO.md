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
`?operator` and turn on **☰ View settings → Evaluator comparison**.

Record in a window at least 1440 px wide (full screen 1920×1080 is best): then the fleet column
shows on the left. Below 1440 px the fleet is behind the **Fleet · 5** button.

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
| 0:00 | 6900 s (12:10Z) | Paused. Five USVs: 01 and 02 sweep cables, 03 and 04 picket the lane, 05 relays. Coverage headline top left of the chart | Setup |
| 0:11 | 7200 s (12:15Z) | EXERCISE banner. USV 01 low battery → RTB chip, "Return to Korsør"; caution alert. 04 takes `seg:G:*` (card: "Cable sweep (Great Belt 1 fibre, 60 kV …)"); "Lane picket S uncovered" caution | Battery low and reassign |
| 0:31 | 7320 s (12:17Z) | Link 04 → shore cut: red ✕ "LINK CUT". 04's card: "Via USV 0…"; its reports keep arriving through 05 | Link loss, store-and-forward |
| 0:44 | ~7865 s | USV 02 chip turns KEEP IN VIEW (warp slows). C-07 appears on the chart as NO AIS; warning "C-07: camera contact, no AIS match. Cue for a look." | Dark contact |
| 0:48 | ~8054 s | USV 03 card: "Keeping C-07 in view"; "Lane picket N uncovered" caution. **Operator attention (right): HELD card "USV 03 to close to 500 m for a look at C-07"** (and a DELEGATED keep-in-view card). Click **Review & approve** (or focus the card and press **A**), read the dialog, press **Enter** (Authorize & send): "Not sent · 5s undo window … Undo queued answer" at the bottom, then "Approved by operator; boat delivery not yet confirmed" | Approval card |
| 0:52 | ~8265 s | USV 02 relieved: chip back to PATROL, cable sweep again | Scout holds until relieved |
| 1:08 | 9200 s (12:48Z) | C-07 departs. Warning "Cannot hold C-07: leaving faster than our boats". After the approved look the contact card shows the name and anchor imaged. By ~9260 s (1:18) USV 03 is back on "Lane picket N" | Contact leaves |
| 1:32 | 10 800 s (13:15Z) | Link 04 → shore restored; 04 "Direct to shore" | Rejoin |
| 1:51 | 11 100 s (13:20Z) | EXERCISE: USV 05 (relay) switched off | Relay loss |
| 2:01 | ~11 160 s | 02, 03 and 05 grey out with "… ago" on their cards, warning alerts. The shore shows them as old, never as live | Shore picture goes stale |
| 2:12 | ~13 305 s (13:57Z) | Shore hears 02 and 03 again; 03's card now says "Relay" (press **3** to see it in Selected) | Relay takeover |
| 2:26 | 14 000 s (14:08Z) | Evaluate. Coverage headline: oldest cable visit and "Cable zone gap open"; both lane pickets open in alerts | Remaining gap shown |

Evaluator cut-ins (second window, Evaluator comparison on): at ~0:48 the purple ring "C-07 · truth only,
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
   **0:48** "Getting closer is my decision, not the boat's. I approve; I have five seconds to undo."
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

- **The approval card is real now** (since #42): if nobody answers it within 05:00 it becomes an
  alarm (~8354 s); if you approve, it is delivered within seconds. Answering on camera is the
  point of the beat.
- **seg:M:0 shows "none since start" (shore-reported).** No boat reports a visit to that
  segment in this run, so the headline names it. That is what the shore knows; don't explain it
  away on camera.
- Video times are approximate; re-time after any change to `agent/`, `world/` or the preset.

## Two-laptop rehearsal (Sun 09:00, N1 · N3 · N5 · N6 · N8 · N11)

Do this on **both** demo laptops, from scratch. Write down the result of each step (pass / fail,
and the times) for the deck notes.

1. **Online:** a clean clone in a new folder:
   `gh repo clone elysassecret/EDTH_07 EDTH_07-rehearsal && cd EDTH_07-rehearsal`
2. **Online:** `uv sync`, then `pnpm --dir web install --frozen-lockfile`, then `pnpm --dir web build`.
3. **Online:** `uv run ruff check .` and `uv run pytest -q`. All must pass. The offline test
   `tests/server/test_web_static.py` checks the build for web addresses.
4. **Turn Wi-Fi off** (and unplug any cable). Keep it off until step 10.
5. Start a stopwatch, run `uv run python -m server --serve-web --demo`, open
   `http://localhost:8765/?operator`. Stop the watch when the console shows **12:10:00Z** and five
   USVs. N8 asks for under 30 s; write down the real time.
6. Press **Run**. By about 0:31 the link 04→shore is crossed; the decision cards, alerts and the
   event timeline all fill in. Nothing on screen may wait for the network.
7. **FEED LOST (N5):** press Ctrl+C in the terminal. Within 2 s the red banner "FEED LOST —
   display frozen at …" appears over the chart and the fleet cards say FROZEN.
8. **Reconnect (N6):** start the command again. The console comes back on its own, without a page
   reload, paused at 12:10:00Z.
9. **Evidence:** ☰ View settings → Evidence and incident reports → "Tamper demo · change one
   character" names the changed record; "Whole run" downloads the incident report `.md` file.
10. Wi-Fi back on. Note any step that failed and who owns the fix.

Projector laptop: run it once at 1280×720 (U8) and choose ☰ View settings → Display: DUSK or DAY for the room.
