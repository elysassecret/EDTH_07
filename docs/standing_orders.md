# Standing orders: the operator policy

Short form for judges: **Watching is pre-approved. Everything beyond watching waits for a person.**

| Tier | Actions | Rule | Where in the code |
|---|---|---|---|
| Automatic safety | Return on reserve, leave a task when battery says so, stop and hold | Boat acts, then reports. Cannot be stopped | `agent/core.py` `_start_return`, hull `forced_return` |
| Delegated under standing order | Open a track, keep in view at 1 nm stand-off, repair sectors, take over relay, log, alert | Starts at once. Operator may Confirm or Stop | `agent/contact.py`, `agent/auction.py`, Stop = `VETOED` record |
| Held for approval | Close inside stand-off to 500 m and photograph, send a report, take a second boat off the cables | No answer means no action. Boat keeps watching | `Shore.command("approve")` → `CMD close` → `standoff_floor_m` |
| Authority only | Order to stop or raise anchor, board, detain, contact flag state, assign blame | System only supplies the record | not implemented on purpose |

Offline rule: a shadowing boat that lost its shore path keeps watching until reserve or the 1,800 s cap, never escalates, and queues the report (`reports[].queued`).

Stale: no boat has observed the contact for 60 s. Cap: 1,800 s, a review point in standing orders, not doctrine. Cannot hold: the contact moves faster than the boat; the boat logs the last course and returns to its tasks.

Buttons: **Confirm / Stop** on watching (delegated tier); **Approve / Decline** on holds. Never "Acknowledge" (means "seen" in real alert systems) and never "Veto" on the screen.

Military and state vessels: AIS cue rule reports only, no task, the fleet keeps clear.
