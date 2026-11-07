# Standing orders: the operator policy

Short form for judges: **Watching is pre-approved. Everything beyond watching waits for a person.**

| Tier | Actions | Rule | Where in the code |
|---|---|---|---|
| Automatic safety | Return on reserve, release tasks when the battery says so | Boat acts, then reports. Cannot be stopped | `agent/core.py` `return_due`, `go_home` |
| Delegated under standing order | Keep in view outside 1 nm, reassign segments, take over the relay | Starts at once. Operator may Confirm or Stop | `agent/contact.py`, `agent/auction.py`; Stop is a `VETOED` record |
| Held for approval | Close to 500 m for a look | No answer means no action. Boat keeps watching | `ShoreNode.command("approve")`, then `CMD` to the boat; `Contacts.radius` |
| Authority only | Order to stop or raise anchor, board, detain, contact flag state, assign blame | System only supplies the record | Not implemented, on purpose |

Offline: a watching boat that loses its shore path keeps watching until reserve, the 1,800 s cap or a stale track, and never closes in without an approval it received. **No queued report exists on the team agent yet**: do not claim one.

Stale: no boat has observed the contact for 60 s. Cap: 1,800 s, a review point, not doctrine. Cannot hold: the contact moves faster than the boat, which reports the course and goes back to its tasks.

Buttons: **Confirm / Stop** on watching (delegated tier), **Approve / Decline** on holds. Never "Acknowledge", which means "seen" in real alert systems, and never "Veto" on the screen.

Military and state vessels: the plan is report only, no task. AIS cue tasks are not built (#52).
