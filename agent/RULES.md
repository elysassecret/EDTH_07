# The rules each boat follows

Owner: A. Plain words for the watch officer, the help overlay and the operator guide. Every number
is the one in the code or config named next to it. Each boat runs these same rules on its own;
there is no leader.

## Who does what

1. **Every task has one owner.** A task is a cable segment to sweep, a lane picket station, the
   relay station or a contact to keep in view. The owner is the boat that won it last.
2. **A boat proves it is alive with a heartbeat every 5 s** (`HEARTBEAT`). Heartbeats are passed on
   by other boats, up to 4 hops (`MAX_HOPS`), so a boat out of the shore's range is still heard.
3. **Silent too long, its tasks open again**: after 60 min for cables and pickets
   (`seg_lease_s = 3600`) and 60 s for the relay and a contact (`LEASE`).
4. **Open tasks are auctioned every 12 s** (`SLOT`). Each free boat bids what the task would cost it,
   and the cheapest bid wins. Each boat bids on one task per round, in this order: the relay,
   a contact, cables, pickets (`BID_ORDER`).
5. **The bid is a time.** Travel time to reach the task, plus the time of its whole patrol loop
   with that task added, plus up to 30 min for a low battery, plus 3 h 20 min (`role_penalty_s =
   12000`) if a picket bids on a cable or a sweeper bids on a contact. That last term keeps a
   picket free for a contact and the cables covered before the lane.
6. **Taking over a silent boat's cables needs a majority of the fleet** (3 of 5). Boats that went
   home do not count; boats that are merely out of range still do. A group cut off by the radio
   never takes over the others' work.
7. **The relay and a contact have a named backup** (the second-cheapest bid). If the owner goes
   silent, the backup takes over without a new auction.
8. **A boat that wins the relay or a contact gives up its cables and picket**, so they can be
   auctioned to someone free.
9. **An idle boat may take a cable from an overloaded one** (`rebalance_ratio = 1.25`: the other
   loop is 25 % longer), at most once every 5 min (`REBALANCE`). Pickets and the relay are never
   counted as idle.
10. **After taking over cables, a boat first sweeps the one it has seen least recently.**

## Battery

11. **A boat goes home when its battery covers only 1.2 × (the trip home, against the current it
    measures, plus a 30 min reserve)** (`return_safety = 1.2`, `reserve_s = 1800`). It releases all
    its tasks at once, so others bid on them in the next round. Nobody can stop this.
12. **A boat never bids on a task it cannot finish and still get home** with the same margin.

### Critical energy: the degraded mode (#104)

What the boat does when the return rule (11) fires, and what it does not claim:

- **What stays on:** propulsion towards Korsør, the heartbeat (now with mode `RETURNING`, so peers
  and the shore know at once), radio forwarding for others, the camera and contact reports. The
  boat keeps no task and bids on nothing.
- **Who is told:** every peer and the shore, by the released task records (others re-auction them
  in the next 12 s round) and by the heartbeat mode. The console raises "USV NN returning to
  Korsør".
- **The estimates:** the trip home uses the boat's own measured current, re-evaluated every tick,
  so an adverse current moves the decision earlier. All of it is a model estimate at cruise speed.
  In 60 seeded runs (30 seeds, off and elysa) the lowest battery any boat ended with was 112 ‰,
  above the 71 ‰ reserve.
- **What counts as recovered:** reaching Korsør (mode `UNAVAILABLE`). Recharging and coming back
  to work are **not modelled**; a restored boat (`boat_restore`) keeps its battery.
- **SENTINEL is not a safe mode.** It is the low-power way to hold a station with motors off
  while the current is weak; it never replaces going home.

## Contacts

13. **A cue for a look**: a track with no AIS, slower than about 1 kn (`loiter_sog_mm_s = 515`),
    within 1 km of a cable, watched for 3 min (`CONTACT_DWELL`), becomes a contact task.
14. **The boat that saw it holds it until the watcher has it in view** (2 km, `keep_in_view_m`).
15. **Watching is standing order 2**: it starts at once, outside 1 nm (`standoff_m = 1852`). The
    watch officer may Confirm or Stop. Stop ends it for good.
16. **No boat goes inside 1 nm of a contact without approval**, not even while sweeping a cable;
    it goes round. A look within 500 m (`standoff_floor_m`) is **standing order 3**: it waits for
    the watch officer, and no answer means no action.
17. **A watch ends** when the contact moves faster than our boats (it reports the course and goes
    back to its tasks), when no boat has seen it for 60 s (`CONTACT_STALE`), or after 30 min
    (`SHADOW_CAP`) for a review.
18. **The last boat sweeping cables never leaves them for a contact.**

## Standing orders

Numbered by the rows of `deck/standing_orders.md`: **1** automatic safety (going home), **2**
delegated (keep in view, reassign cables, take over the relay), **3** held for approval (close to
500 m), **4** authority only (not implemented, on purpose).

## The `why` on the shore picture

When a boat claims a task it sends one line, under 120 characters, built from what it knows at
that moment, e.g. `USV 04: cheapest of 3 bids (USV 03 +1 h 06 m); 23
min away, battery ~4 h 09 m after, drops pick:S [battery return]`: the next bidder and how much
more its bid was, the travel time, a model estimate of the battery left after doing the task once
and getting home, and the role the boat gives up (rule 8). The tag in brackets says why the task was open:

| Tag | Meaning |
|---|---|
| `battery return` | Its owner went home (rule 11) |
| `lease expired` | Its owner went silent past its lease (rule 3) |
| `rebalance` | An overloaded boat handed it over (rule 9) |
| `handed over` | Its owner took the relay or a contact (rule 8) |
| `back to my own task` | The boat takes back what it gave up, e.g. its picket after a contact |
| `contact: nearest free boat` | A new contact (rules 4, 5, 15) |
| `relay: no shore path N s` | The boat has not heard the shore for N s (rule 7) |
| `deputy takeover` | The named backup took over (rule 7) |
| `open task` | Nobody owned it yet |

The shore shows only reasons it received. A reason that did not arrive is left blank, never
guessed.
