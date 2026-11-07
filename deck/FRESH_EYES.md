# Fresh-eyes test: 10 minutes, one stranger

Owner: D (#89). Question: can someone who has never seen the console say what happened and what to do, within 60 seconds of each beat, with no explanation from us?

## Who and what

- **Tester:** one person who has not seen the console or our slides. Not a teammate. A mentor, another team, a volunteer. Record their role, not their name.
- **Screen:** the operator view, `http://localhost:8765/?operator`, at least 1440 px wide, after `pnpm --dir web build` and `uv run python -m server --serve-web --demo` (`server/DEMO.md`). The legend is open. Nobody touches the help overlay unless the tester finds it.
- **Revision:** write down `git rev-parse --short HEAD` before starting.
- **People:** D runs the stopwatch and writes. Nobody else speaks. If the tester asks a question, answer only "What do you think?" and write the question down: questions are findings.

## Script (say exactly this, then stop talking)

"You are the watch officer on shore. These five boats guard cables in the Great Belt. I will pause three times. Each time, tell me out loud what just happened and what, if anything, you would do. There are no wrong answers; we are testing the screen, not you."

Press **Run**. The preset pauses itself only at the start, so D clicks **Pause** (top bar) at each beat below, at the end of the video window given. Do not use Space: it acknowledges the top alert.

## The three beats

| Beat | Sim time (UTC on screen) | Video | Pass if the tester says, in their own words, both |
|---|---|---|---|
| 1. Battery return | 7,200 s (12:15Z) | 0:11 to 0:31 | (a) USV 01 is going home on low battery and another boat (04) took its cable work; (b) the south lane picket is now empty, and there is nothing to approve, at most acknowledge |
| 2. Contact and card | ~8,054 s (12:29Z) | 0:44 to 0:52 | (a) a contact with no AIS is being kept in view, it is a cue for a look, not a threat; (b) a boat asks to close to 500 m and it waits for them: Approve or Decline |
| 3. Relay off | 11,100 s (13:20Z) | 1:51 to 2:12 | (a) the relay boat 05 is off and boats 02 and 03 are greyed because shore cannot hear them, so their place is old; (b) nothing to approve, acknowledge, and wait for another boat to take the relay |

Times are from `server/DEMO.md` (seed 1, measured 7 Nov). Issue #89 lists relay off at 13:05Z; the preset injects it at 11,100 s, which is 13:20Z. Use the screen clock.

**Pass** a beat when both (a) and (b) are said within 60 s of the pause, unprompted. **Partial** when only one is. **Fail** otherwise, or when the tester says something the screen made them believe that is false (for example "the boat is hostile", "coverage is fine", "02 is at that dot now").

## Record (copy this table into the comment on #88)

Revision: `_______` · Date and time: `_______` · Tester role: `_______` · Screen width: `_______`

| Beat | Verbatim words (write everything, including "um" and wrong guesses) | Asked us | Time to answer (s) | Pass / partial / fail |
|---|---|---|---|---|
| 1. Battery return 12:15Z | | | | |
| 2. Contact and card 12:29Z | | | | |
| 3. Relay off 13:20Z | | | | |

After the three beats, two questions, words verbatim:

1. "What was the hardest thing to read on the screen?"
2. "Which mark on the chart did you not understand?"

## Afterwards

1. Post the table and the two answers on #88 within 10 minutes, verbatim, no cleaning up.
2. Name one change per failed beat, for C, smallest first (a word, a legend row, an alert line).
3. When C has fixed them, run the test again on a **different** person. A tester who has seen the screen once is no longer fresh.
4. Put the verdict (pass count per run, link to the #88 comment) in `deck/FEATURE_CHECKLIST.md` rows 17 and 24.

## Results

Not run yet. Waits for C's screen from #88 on `main`.
