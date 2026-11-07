# Operator guide: one screen

Five uncrewed boats guard three cables and a shipping lane in the Great Belt. They share out the work themselves. **You do not steer them. You watch, answer, and acknowledge.**

## The headline (top of the chart)

"6 of 7 cable segments within target · seg:M:0: no visit confirmed" means: one segment has no confirmed visit; all others were visited inside the 3 h 20 min revisit target. When a segment goes over, it says since when. These ages are what shore has been told, never more. **Details** shows the counts.

## Your three actions

| Do | When | How |
|---|---|---|
| **Watch** | Always | Read the headline, the alerts and the line under each boat card that says why it does what it does |
| **Answer** | A card waits on the right | HELD card (closer look): **Approve** (A) or **Decline** (D); no answer means no action. DELEGATED card (already running): **Confirm** (C) or **Stop** (S). 5 s to undo with Esc |
| **Acknowledge** | An alert is new | **Acknowledge** or Space on the top alert. It means "seen"; the condition may still be active |

Keys: **?** this help · **1** to **5** select a boat · **Esc** undo or close.

## Legend

| Mark | Means |
|---|---|
| Magenta / purple line | Power / data cable to sweep |
| Teal · yellow · orange on a cable | Visited recently · due · over target |
| Grey dashed cable | No visit confirmed |
| Blue dot with a line | Our boat and its heading. Grey dot: not heard, last known place |
| Green square / yellow cluster | Ship with AIS / contact with NO AIS, a cue for a look |
| Thin / thick blue line, red ✕ | Radio link / route to shore / link cut |
| White dashed line | Route a waiting card proposes |
| Blue shading | Depth, 0–10, 10–20, 20–30, over 30 m |

Full row text: `deck/LEGEND.md`.

## Standing orders

1. **Automatic safety.** A boat low on battery goes home and gives up its tasks. It reports; nobody can stop it.
2. **Delegated.** Keeping a contact in view from outside 1 nm, swapping cable segments and taking over the relay start at once. You may Confirm or Stop.
3. **Held.** Closing to 500 m for a look waits for your Approve. No answer, no move; the boat keeps watching.
4. **Authority only.** Stopping, boarding or blaming a vessel is not the system's job. It only keeps the record.

## How the boats decide

[AGENT RULES: copy the short table from `agent/RULES.md` once A delivers it (#86). Until then, from `agent/auction.py`: each boat bids the time it needs to get there plus a penalty for a low battery; the lowest bid wins; a boat that falls silent loses its tasks when its lease runs out, and another boat takes them.]

## What the simulator models (`world/MODEL.md`)

| Model | Value |
|---|---|
| Speed | 2.3 m/s (about 4.5 kn) |
| Battery | 7 h; goes home with a 30 min reserve |
| Camera | Ship by day 5 km, dusk 2 km, unlit at night 500 m; keep in view 2 km; close look 500 m |
| Radio | Boat to boat 8 km, to Korsør mast 14 km, 5 % loss, up to 4 hops |
| Sea | 0.5 m/s current, turns once at 2.5 h. No waves, no collision avoidance |
