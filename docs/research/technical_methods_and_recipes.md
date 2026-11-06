# Technical methods and recipes for the Challenge 07 USV swarm demo

Written 6 November 2026 for Team Elysa's Secret. Evidence labels used throughout: **[Source]** means read this session. **[Own calculation]** means computed this session from the plan's numbers. **[Scratch model]** means a throwaway stress model, not project code and not a measurement of any real system. **[Judgement]** means an engineering estimate with no source. **[Unverified]** means not confirmed this session.

Research limits: WebSearch hit its session cap part-way through, and the coordinator then stopped further web research. Several pages also refused direct fetches (USCG NAVCEN, MDPI, core.ac.uk, the DMA download portal). Remaining topics rest on pages already read. Each Gaps section says what is missing.

## 1. What is wrong with the plan, and what must change before Friday 21:00?

### Takeaway
The proposed fixes are necessary but do not separate repair-on from repair-off. In the plan's own geometry the headline still nearly ties at 14,400 s (18,180 s vs 17,620 s, 3%), because the pre-event patrol cycle of about 17,000 s already sets the maximum. Three changes matter most: drive the two power cables as one corridor, replace the bid cost with cycle time after cheapest insertion, and give idle boats a way to get work back. With the first two, the same comparison becomes 14,680 s vs 12,060 s (18%).

### Cited Findings
- EDTH's brief fixes five USVs, 2–3 m long, 6–8 h endurance, camera, AIS receiver and short-range radio; roles of two cable scouts, two lane watchers and one relay; failures halfway through the mission; and an operator who "approves decisions" — [Task07EDTH.txt](C:\Users\franc\Desktop\studia\ElysasSecret\EDTH\Task07EDTH.txt)
- The plan's defaults are 3 m/s, 500 m camera radius, 8 km radio, 7 h endurance, 0.25–1 s delay per hop, 5% loss, 2 s heartbeat, 6 s bid window, 20 s lease and a 600 s revisit target — [current-plan-copy.html](C:\Users\franc\Desktop\studia\ElysasSecret\EDTH\research_notes\Challenge 07 scoring research\current-plan-copy.html)
- A project memory note says the EDTH hacker guide publishes seven jury criteria, makes the deck due Sunday noon, and runs 3-minute pitches back to back with the demo as a linked video. This is second-hand and the PDF was not re-read here — [Hacker Onboarding PDF](C:\Users\franc\Desktop\studia\ElysasSecret\EDTH\Hacker Onboarding — EDTH Hackathons.pdf)

### Inferences

#### Status of the six known fixes

| Known fix | Verdict | What still needs doing |
|---|---|---|
| 14,400 s run, events at halfway | Needed, not sufficient | Headline still near-ties unless the corridor and cost changes also go in. Prefer 16,800 s with events at 7,200 s, which stays under the return limit [Scratch model]. |
| Seed ages at reset | Needed | Seed from one saved warm-up run shared by all modes. Random seeds would let the seed set the maximum. |
| Scout holds until relieved | Accept | Also add a keep-in-view radius (section 4). |
| Shadow cap 1800 s | Accept | Approach of 986 s leaves about 814 s in view [Own calculation]. |
| "Free" excludes last cable scout | Accept | Add to contact eligibility (section 2). |
| Shore at south-centre | Incomplete | 04 at the plan's position is 8.9 km from that point, still beyond 8 km, so there is still no direct link to cut [Own calculation]. Use a 12 km shore-link range (section 4). |
| 60× live view | Incomplete | At 60× repair lasts under 1 s of wall time, and 14,400 s takes 240 s, longer than the 3-minute pitch [Own calculation]. Use a time-warp (section 9). |

#### New flaws found

| # | Flaw | Evidence | Fix |
|---|---|---|---|
| N1 | Maximum age is set before the event, so the headline barely moves | Pre-event worst 17,020 s; OFF 18,180 s [Scratch model] | Corridor plus cost change; report km overdue as well |
| N2 | 600 s revisit target is impossible | Needs 46 boats on a closed loop or 92 back-and-forth [Own calculation] | Use 10,800 s (3 h) |
| N3 | Roles are unbalanced: 31 km per cable boat, 10.3 km per lane boat | Measured off the plan's SVG [Own calculation] | Corridor task; let the lane boats absorb load |
| N4 | The two power cables are 773–905 m apart on the plan's map, so one pass with a 500 m radius sees both, yet they are separate tasks | [Own calculation]; map is not to scale | Merge into one corridor task; samples stay on both cables |
| N5 | Plan cost appends to queue end and ignores geometry | Plan row vs minimax row, section 3 | Cheapest-insertion cycle bid |
| N6 | A boat back from shadowing, or one that lost a merge, gets no work: it may only bid on open work, and none is open | With shadowing, one boat's cycle reached 32,066 s (8.9 h, over endurance) [Scratch model] | Rebalance rule |
| N7 | An isolated boat sees every other lease expire, is sole bidder and claims nearly everything; endurance alone barely limits it because 7 h is 75.6 km | Logic walk-through; [Own calculation] | Majority rule for expiry claims, cycle cap |
| N8 | Nothing defines who starts a bid round or when; windows start when each boat happens to hear the release | Section 2 | Time-slotted rounds |
| N9 | A full 7 h run cannot be evaluated: the return rule fires near 17,400 s for a boat 18 km from home (25,200 − 1,800 − 6,000) | [Own calculation] | End the run before about 17,000 s or stagger starting batteries |
| N10 | Detection and verification are one radius. If ship detection reaches 5.9 km, four parked boats cover the whole strip and the patrol problem vanishes | [Own calculation] | Two radii; visit credit uses the short one (section 4) |
| N11 | 2 s heartbeats do not fit an 8 km licence-free link | 40-byte heartbeat is 160 bit/s per boat; a 1.07 kbit/s link at 10% duty allows 107 bit/s [Own calculation] | 5 s heartbeat; state the radio assumption |
| N12 | Brief says the operator "approves decisions"; plan is immediate action with veto | Brief vs plan | Confirm with mentor; label as "boat acts, operator approves or vetoes after" |
| N13 | Plan assumes submission about 13:00; guide reportedly says deck due Sunday noon | Second-hand | Move results and video earlier (section 10) |

### Gaps
- The hacker guide's jury criteria were not checked here. Read the PDF before finalising the pitch.
- Route distances come from the plan's illustrative SVG, which says it is not to scale. Real cable separation may differ, and N4 only holds if it is under about 1 km.

## 2. Is the auction and ownership logic sound?

### Takeaway
The core idea is sound and has a proper name: a per-task last-writer-wins register whose clock is a logical counter with a replica-ID tie-break. The plan does have real bugs: undefined round starts, isolated boats claiming the fleet's work, cost ignored on merge, and idle losers. The fixes below are small. Do not claim SSI bounds or consensus.

### Cited Findings
- SSI auctions run one single-item auction per round with as many rounds as items; every robot may bid on any unallocated target, and each robot bids only on its cheapest target — [Kishimoto & Sturtevant, AAMAS 2008](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0299.pdf)
- SSI Tree rules guarantee factors of 2 for MiniSum and 2n for MiniMax when the triangle inequality holds, and that paper notes a 10× factor for 5 robots on MiniMax, leaving much more room for improvement — [Kishimoto & Sturtevant](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0299.pdf)
- MiniSum minimises the sum of path costs; MiniMax minimises the largest single robot's path cost; both are NP-hard — [Kishimoto & Sturtevant](https://aamas.csc.liv.ac.uk/Proceedings/aamas08/proceedings/pdf/paper/AAMAS08_0299.pdf)
- SSI's total travel distance is reported as within a constant factor of optimal in known terrain — [Koenig et al., AAAI 2006](https://idm-lab.org/bib/abstracts/Koen06b.html)
- A 2014 AAMAS study found SSI broadly ahead of other single-item auction variants, though not in every scenario — [AAMAS 2014](https://aamas.csc.liv.ac.uk/Proceedings/aamas2014/aamas/p1443.pdf)
- CBAA and CBBA use auctions for task selection and consensus on winning bid values for conflict resolution, converge to conflict-free assignments, and are reported robust to inconsistent situational awareness and topology change — [Choi, Brunet & How, IEEE T-RO 2009](https://dspace.mit.edu/handle/1721.1/52330)
- RFC 677 (Johnson & Thomas, 1975) uses timestamp pairs (T, D), ordered by T and then by originating site D, keeps the most recent, and handles deletions with creation timestamps, which is the ancestor of the plan's rule — [RFC 677](https://www.rfc-editor.org/rfc/rfc677.txt)
- Shapiro's survey credits Johnson and Thomas with greatest-timestamp-wins, and describes state-based CRDTs as a join-semilattice where merge is the least upper bound — [Shapiro, Encyclopedia of Big Data Technologies](https://perso.lip6.fr/Marc.Shapiro/papers/replicated-data-types-Encyclopedia-DB-systems-2016-authorversion.pdf)
- The replica-ID tie-break is an implementation convention rather than something in Shapiro's text; libraries use "higher node ID wins" — [peat-lite LWW source](https://docs.rs/peat-lite/0.2.2/src/peat_lite/lww.rs.html)
- Leases give holders time-limited rights. Non-Byzantine failures affect performance rather than correctness, short leases of about 10 s were near-optimal in their file-access study, and clock behaviour is a known weak point — [Gray & Cheriton, SOSP 1989](https://courses.cs.duke.edu/spring15/cps210/readings/leases-sosp89.pdf); clock caveat per [this review](https://blog.acolyer.org/2014/10/31/leases-an-efficient-fault-tolerant-mechanism-for-distributed-file-cache-consistency/)

### Inferences

#### What to call it, correctly
- Allocation: "sequential single-item auction, fixed-order variant". The plan auctions tasks in ID order, while true SSI lets each robot bid across all open tasks. The Tree-rule bounds therefore do not apply. In the scratch model fixed order matched full SSI closely, so keep fixed order.
- Merge: "per-task last-writer-wins register using a logical counter with replica-ID tie-break". It descends from RFC 677's (T, D). Because it uses a counter it needs no synchronised clock for ordering.
- Liveness: leases (Gray & Cheriton).
- Bid objective after the change below: MiniMax-style.
- Not CBBA, not consensus. Adding the bid to the key makes same-version conflicts resolve like CBAA's "best bid wins", but that is a shared idea and not an implementation of CBAA.
- Guarantee language: eventual convergence per connected group, given delivery. Duplicate patrol is harmless and missing patrol is the hazard, so the design favours availability.

#### Failure walk-through

| Case | What the plan does | Verdict | Fix |
|---|---|---|---|
| Lost bid: A is cheapest, B never hears A | Both claim at the same version; higher ID wins even if costlier | Converges, wrong boat | Put bid in key |
| Winner dies between bid and claim | No timer restarts the round | Bug: task stranded | Slots: task stays open, re-bid next slot |
| Late bid | Windows unaligned; 4-hop bid misses 6 s in 2.1% of deliveries [Own calculation] | Bug | 12 s slots on shared time |
| Lease race: refresh arrives mid-window | No cancel rule | Bug: needless takeover | Re-check `is_open` at close |
| Same record with two lease values | Merge undefined because refresh keeps version | Bug | Per-boat lease; records carry no lease |
| Split brain | Both sides claim; highest version wins | Sound by design | Keep; add quorum and cap |
| Isolated boat | Claims all expired tasks; its higher versions then beat live owners on rejoin | Serious bug | Quorum for expiry claims |
| Rejoin leaves owners empty | Loser drops and has nothing to bid on | Serious bug | Rebalance |
| Simultaneous release | Two tasks open, fine. Release and claim at equal version resolve by ID, so a working owner may drop | Minor | State rank: claimed beats released |
| Duplicate relay | Each partition elects, both shed patrol work | Waste, then idle boat | Only elect if shore is silent; deputy; rebalance |
| Version churn at range edge | Each dropout over 20 s bumps version and moves tasks | Real risk | 60 s lease; one claim per slot |
| Veto vs later claim | Depends on delivery | Minor | Vetoed state outranks claimed |
| Lease false alarm from loss alone | P(10 refreshes lost) is 4.8e-8 at 4 hops, assuming independence [Own calculation] | Not the risk | Real risk is range flapping |

Plan rules that survive unchanged: losers drop at once, no outbidding a live claim, tombstones on release, retain and re-advertise records, one owner per connected group as the promise.

#### Exact pseudocode changes

Constants (integers, milliseconds):
```python
HEARTBEAT=5_000; PEER_STALE=20_000; LEASE=60_000; SLOT=12_000
DEPUTY_GRACE=10_000; REBALANCE=300_000; SHORE_SILENCE=30_000
CYCLE_MAX=21_600_000   # 6 h
RELEASED, CLAIMED, VETOED = 0, 1, 2
```

Record and merge. Drop `lease deadline`, `last update time` and the bid's `proposed version`:
```python
@dataclass(frozen=True, slots=True)
class Rec: task:str; ver:int; state:int; bid:int; owner:int; deputy:int  # deputy 0 = none

def key(r): return (r.ver, r.state, -r.bid, r.owner)
def merge(a, b): return a if key(a) >= key(b) else b
```

One lease per boat. Heartbeats renew all of a boat's tasks and forwarding leaves `t_sent` untouched:
```python
def lease_ok(b, t): return b == me or t <= last_hb[b] + LEASE

def is_open(task, t):
    r = table[task]
    if r.state == RELEASED: return True
    if r.state == VETOED or lease_ok(r.owner, t): return False
    if r.deputy and t < last_hb[r.owner] + LEASE + DEPUTY_GRACE: return False
    return True
```

Slotted rounds with no coordinator, using shared sim or GNSS time. A dead winner resolves itself because the task simply stays open:
```python
def on_slot(t):                     # fires when t % SLOT == 0
    e = t // SLOT
    close_round(e-1, t)
    for task in sorted(table):      # relay and contact IDs sort first
        if is_open(task, t) and can_bid(task, t):
            send(Bid(task, e, bid_cost(task), me)); break   # one bid per slot

def close_round(e, t):
    for task, bs in sorted(bids.pop(e, {}).items()):
        if not is_open(task, t): continue          # live claim arrived: cancel
        bs = sorted(bs, key=lambda b: (b.cost, -b.boat))
        if bs[0].boat == me:
            dep = bs[1].boat if len(bs) > 1 and kind(task) in ("relay", "contact") else 0
            publish(Rec(task, max_ver(task)+1, CLAIMED, bs[0].cost, me, dep))
            insert_into_tour(task)
```

Bid cost. This is the smallest change that matters, and the battery term is untouched:
```python
def cycle_after(task):  return cheapest_insertion_length(tour, task) * 1000 // V_MM_S
def bid_cost(task):     return cycle_after(task) + 1_800_000 * (1000 - batt_permille) // 1000
```

Eligibility. Adds the quorum, cap and last-scout guards:
```python
def can_bid(task, t):
    if mode in (RETURNING, UNAVAILABLE): return False
    if kind(task) == "seg":
        if mode == SHADOWING or i_am_relay(): return False
        r = table[task]
        if r.state == CLAIMED and 1 + live_peers(t) < n_active()//2 + 1:
            return False                       # expiry takeover needs a live majority
        cyc = cycle_after(task)
        return cyc <= CYCLE_MAX and energy_ok(cyc)
    if kind(task) == "relay":
        return shore_age(t) > SHORE_SILENCE and energy_ok_relay()
    if kind(task) == "contact":
        return not i_am_relay() and not i_am_last_cable_owner() and energy_ok_contact()

# n_active drops boats that announced return, or have been silent 600 s.
```

Reconcile:
```python
def on_record(r):
    cur = table[r.task]; new = merge(cur, r)
    if new is cur: return
    table[r.task] = new; forward(new)
    if cur.owner == me and cur.state == CLAIMED and new.owner != me:
        drop_from_tour(r.task)
```

Rebalance, the fix for N6 (limit 1.25 was used in the scratch model):
```python
def on_rebalance(t):                 # every REBALANCE, staggered by boat ID
    lo = min(available_peers(t), key=cycle)
    if my_cycle() > 1.25*lo.cycle and len(tour) >= 2 and not any_open(t):
        s = segment_whose_removal_lowers_max_cycle(lo)
        if estimated_cycle_after(lo, s) < my_cycle():
            publish(Rec(s, max_ver(s)+1, RELEASED, 0, me, 0))
```

Named deputy (idea 2), for relay and contact only:
```python
def on_tick(t):
    for task, r in table.items():
        if r.deputy == me and r.state == CLAIMED and not lease_ok(r.owner, t):
            if can_bid(task, t):
                publish(Rec(task, r.ver+1, CLAIMED, bid_cost(task), me, 0))  # no radio round
            else:
                publish(Rec(task, r.ver+1, RELEASED, 0, me, 0))              # decline: reopen
```

Why deputies only for relay and contact: patrol segments have hours of slack, so saving one auction changes nothing in worst age. A deputy on segments would also inherit a lost boat's whole sector, because the same second-lowest bidder recurs. The real value is taking over with no radio round when the link is what failed. If a deputy cannot act, it declines and an auction follows after `DEPUTY_GRACE`.

Veto is a record: `Rec(contact_id, ver+1, VETOED, 0, 0, 0)`.

Contact (known fixes included): the scout keeps the contact until another boat reports it in view, and only then releases. Stale means no boat has observed it for 60 s [Judgement].

### Gaps
- CBBA's convergence bound, diminishing-marginal-gain condition and 50% guarantee could not be read: the paper fetch was blocked. Do not quote them without checking.
- These references are from memory and were not verified this session; check before putting them on a slide: Lamport, "Time, Clocks, and the Ordering of Events", CACM 1978, which is the source for (counter, process ID) total order (the fetched PDF is a scan and unreadable); Dias et al., "Market-based multirobot coordination: a survey and analysis", Proc. IEEE 2006; Gerkey & Mataric, "Sold!", IEEE TRA 2002, and their 2004 task-allocation taxonomy; Parker, ALLIANCE, IEEE TRA 1998; Liskov & Cowling, "Viewstamped Replication Revisited" 2012, a precedent for a pre-agreed successor (site unreachable).
- The quorum rule is my proposal and no source was checked. It changes the plan's split test: only the majority side should claim on expiry.

## 3. Multi-robot patrol theory and the scenario estimate

### Takeaway
"Worst idleness" is the standard term, and "worst revisit age" is the same thing sampled on points. Losing one of four boats should cost about 33% in steady state if work is rebalanced, and leaves orphaned ages growing without limit if not. The plan's cost does balance load, but poorly. The smallest change is cycle time after cheapest insertion, with no idleness term in the bid.

### Cited Findings
- Idleness of a node is the time since its last agent visit, and worst idleness is the largest idleness across all nodes over the whole patrol. Chevaleyre chose it for simple analysis, notes it upper-bounds average idleness, and attributes the criteria to Machado et al. — [Chevaleyre, IAT 2004](https://www.cs.utexas.edu/~pstone/Courses/393Rfall18/readings/Chevaleyre.pdf)
- Idleness starts at 0 for all nodes in that definition, and a simulated worst idleness only approximates the true value — [Chevaleyre](https://www.cs.utexas.edu/~pstone/Courses/393Rfall18/readings/Chevaleyre.pdf)
- For one agent, the TSP cycle is optimal for worst idleness (Theorem 1) — [Chevaleyre](https://www.cs.utexas.edu/~pstone/Courses/393Rfall18/readings/Chevaleyre.pdf)
- With r agents spaced on a closed path of length l: l/r − max edge ≤ WI ≤ l/r + max edge (Lemma 1) — [Chevaleyre](https://www.cs.utexas.edu/~pstone/Courses/393Rfall18/readings/Chevaleyre.pdf)
- The Christofides-based cyclic strategy satisfies WI ≤ 3·opt + 4·max edge (Theorem 2) — [Chevaleyre](https://www.cs.utexas.edu/~pstone/Courses/393Rfall18/readings/Chevaleyre.pdf)
- The best cyclic strategy is within 3·max edge of the best partition (Theorem 3), but partition can win on graphs with long corridors between regions; inside a region the optimal move is that region's TSP tour (Lemma 4) — [Chevaleyre](https://www.cs.utexas.edu/~pstone/Courses/393Rfall18/readings/Chevaleyre.pdf)
- Portugal & Rocha compared five approaches in ROS simulation using average idleness of the graph — [Portugal & Rocha, SSRR 2011](https://home.deec.uc.pt/~rprocha/publications_ficheiros/PR11-SSRR11.html)
- Recent work still targets worst idleness, defined as the maximum over an infinite horizon — [Scherer et al., RA-L 2022](https://www.dynsyslab.org/wp-content/papercite-data/pdf/scherer-ral22.pdf)

### Inferences

#### Analytic estimate [Own calculation]
Formulas: closed tour of length C with n spaced boats gives WI ≈ C/(nv). An open line of length ℓ swept back and forth with radius r gives WI ≈ 2(ℓ−r)/v. Using v = 3 m/s, r = 500 m:

| Case | n=4 | n=3 | n=2 |
|---|---|---|---|
| 83 km, equal shares, back-and-forth | 13,500 s | 18,111 s | 27,333 s (over 7 h endurance) |
| Corridor, 61.5 km of driving | 9,932 s | 13,354 s | 20,198 s |
| Closed tours, assumed C = 90–110 km | 7,500–9,167 s | 10,000–12,222 s | not computed |

- As briefed: cable boats have 31 km each (20,365 s), lane boats 10.3 km each (6,538 s).
- Ideal effect of one departure is n/(n−1): 4→3 costs +33%, 3→2 costs +50%. Without repair, orphaned samples age at 1 s per second, reaching age at T + (H−T).
- During shadowing plus one battery return only two boats patrol, and the bare 83 km case exceeds endurance. Priorities will be needed if that lasts: cables before lane.
- Because Lemma 4 favours tours inside a region, boats should loop their segments as a tour. The cheapest-insertion bid does this automatically.

#### Stress model [Scratch model]
Plan geometry, 19 segments, boats 01–04 on tours, relay excluded, warm-up to steady state, boat 01 leaves at T. Instant auctions, no radio, no return reserve for other boats. The shadow case removes 03 for 1800 s at T+180. Medians over 10 random phases (8 for the corridor).

Worst age in seconds, then share of samples older than 3 h at the end of the run:

| Case | OFF | Plan cost | Minimax cost | Full SSI | Minimax + rebalance |
|---|---|---|---|---|---|
| As briefed, 14,400 s | 18,180 / 0.25 | 17,620 / 0.12 | 17,040 / 0.11 | 17,040 / 0.10 | 17,020 / 0.06 |
| As briefed, 14,400 s, shadow | 18,180 / 0.25 | 18,200 / 0.28 | 18,200 / 0.24 | 18,180 / 0.18 | 19,300 / 0.19 |
| As briefed, 25,200 s | 21,300 / 0.31 | 19,200 / 0.22 | 17,060 / 0.13 | 17,060 / 0.13 | 17,060 / 0.13 |
| Corridor, 14,400 s | 14,680 / 0.18 | 14,040 / 0.01 | 12,060 / 0.00 | 12,060 / 0.00 | 12,060 / 0.00 |
| Corridor, 14,400 s, shadow | 14,680 / 0.18 | 14,340 / 0.15 | 12,640 / 0.04 | 12,640 / 0.04 | 13,200 / 0.15 |
| Corridor, 16,800 s, T=7,200 (6 phases) | 17,040 / 0.26 | 14,480 / 0.02 | 12,820 / 0.06 | not run | 12,600 / 0.02 |
| Corridor, 16,800 s, T=7,200, shadow (6 phases) | 17,040 / 0.26 | 16,440 / 0.26 | 14,120 / 0.08 | not run | 13,740 / 0.12 |
| Corridor, 25,200 s | 19,460 / 0.26 | 15,180 / 0.07 | 13,040 / 0.02 | 13,040 / 0.02 | 12,260 / 0.00 |
| Corridor, 25,200 s, shadow | 19,460 / 0.26 | 17,840 / 0.33 | 14,760 / 0.17 | 14,720 / 0.13 | 13,980 / 0.00 |

Pre-event worst age was 17,020 s as briefed and 10,300 s with the corridor. Share over 3 h before the event was 0.08 and 0.00.

What this shows:
- The corridor is the biggest single gain: pre-event worst age falls 39%.
- Best evaluation setup found: corridor, 16,800 s, events at 7,200 s. Repair-off reaches 17,040 s against 12,600–12,820 s with the minimax bid, a gap of about 25%, and the run ends before the return rule fires. With shadowing the gap is 17,040 s against 13,740–14,120 s.
- The plan's cost balances, but with poor tours: example cycles of 10,445 / 10,469 / 15,886 s against 10,445 / 11,964 / 8,246 s for minimax.
- Fixed order with the minimax cost matched full SSI, so no change to auction order is needed.
- Without rebalance a boat back from shadowing sits idle, and in those rows repair can look worse than OFF on the overdue share.
- Rebalance helps the end state most on long runs. It can raise the transient maximum, as in the 19,300 s and 13,200 s cells, so one release per 300 s is a sensible limit.
- Worst age alone is a weak discriminator. Km overdue against a 3 h target separates the modes far better.
- The 25,200 s rows ignore the return reserve (flaw N9), so treat them as a long-horizon guide only.
- Script for reproduction: `C:\Users\franc\AppData\Local\Temp\claude\472a0e765c674616\5a7ba5d4-21c3-47e6-850a-2271ddf60119\scratchpad\tools\patrol.py` (set `CORR=1` for the corridor). It is temporary and is not project code.

#### Recommendations
1. Keep the name "worst revisit age" in speech and cite "worst idleness" in slides.
2. Add one idleness-free change to the bid: cycle after cheapest insertion. Segment age is identical for all bidders, so adding it to the bid cannot change who wins.
3. Report three numbers: worst age in the post-event window, km overdue against 3 h at end of run, and time from event to all segments owned.
4. Merge the power cables into one corridor task.

### Gaps
- Pasqualetti, Franchi & Bullo (IEEE T-RO 2012, cooperative patrolling on chains and trees) and Elmaliach, Shiloni & Kaminka (AAMAS 2008, polyline patrolling) are the closest published fits to cables as open lines, but neither could be fetched. Both are cited from memory [Unverified]. The back-and-forth formula above is my derivation.
- Machado et al.'s original paper was not read directly; it is cited via Chevaleyre.
- Auction-based patrol papers (Menezes, Tedesco & Ramalho) were not checked, so there is no literature comparison for idleness in bids.
- Ten or eight phases is a small sample and the model is idealised. The real simulator must repeat this with at least 5 seeds.

## 4. Realistic parameters

### Takeaway
A 500 m radius is defensible as verification range and far too small as ship detection range. An 8 km radio is defensible only for a narrowband or licensed link, not Wi-Fi class. 3 m/s is above the one 2 m hull verified, so keep it as a stated assumption with a sensitivity run.

### Cited Findings
- Maritime Robotics Otter: 2.0 m long, 62 kg, top speed 4.5 kn, 20 h at 2 kn, 5 GHz MIMO radio or Wi-Fi as standard, with VHF, 4G and other options — [Maritime Robotics](https://www.maritimerobotics.com/otter)
- Denmark deployed four Saildrones in the Baltic in June 2025 to monitor the shadow fleet and threats to underwater infrastructure — [Wikipedia, Unmanned surface vehicle](https://en.wikipedia.org/wiki/Unmanned_surface_vehicle)
- AIS Class A transmits at 12.5 W, Class B CS at 2 W, Class B SO at 5 W — [Wikipedia, AIS](https://en.wikipedia.org/wiki/Automatic_identification_system)
- AIS viewing is limited to VHF range of about 10–20 nmi; Class A has a nominal 20 nmi at sea, Class B about 5–10 miles, and range depends on the height and quality of both antennas — [Wikipedia, AIS](https://en.wikipedia.org/wiki/Automatic_identification_system)
- Radio horizon is d ≈ 4.12√h km for h in metres with k = 4/3, and the optical horizon is d ≈ 3.57√h — [Wikipedia, Line-of-sight propagation](https://en.wikipedia.org/wiki/Line-of-sight_propagation)
- Two-ray far-field loss is PL = 40·log10(d) − 10·log10(G·ht²·hr²), a 40 dB per decade slope beyond d_c = 4π·ht·hr/λ — [Wikipedia, Two-ray model](https://en.wikipedia.org/wiki/Two-ray_ground-reflection_model)
- Johnson criteria at 50% probability: detection 1.0, orientation 1.4, recognition 4 and identification 6.4 line pairs — [Wikipedia, Johnson's criteria](https://en.wikipedia.org/wiki/Johnson%27s_criteria)
- Required light visibility: 50 m and over, masthead 6 miles, side and stern 3; 12–50 m, masthead 5 (3 if under 20 m), side and stern 2; under 12 m, masthead and stern 2, side 1 — [33 CFR 83.22](https://www.law.cornell.edu/cfr/text/33/83.22)
- Maritime EO detection is hard because of background motion from waves and wakes, camera motion and low contrast — [Prasad et al., SMD survey](https://arxiv.org/abs/1611.05842)
- Meshtastic link budgets at 22 dBm and 0 dB antenna: LongFast 153 dB at 1.07 kbit/s, MediumFast 148 dB at 3.52, ShortFast 143 dB at 10.94; rates are theoretical maxima — [Meshtastic radio settings](https://meshtastic.org/docs/overview/radio-settings/)
- EU_868 in Meshtastic uses 869.4–869.65 MHz, 10% duty cycle, 27 dBm limit — [Meshtastic LoRa config](https://meshtastic.org/docs/configuration/radio/lora/); the same duty limit appears in [TTN's duty-cycle page](https://www.thethingsnetwork.org/docs/lorawan/duty-cycle/)
- ESP32 Wi-Fi delivers up to +20.5 dBm on 802.11b, and sensitivity is −98 dBm at 802.11b 1 Mbps — [ESP32 datasheet](https://documentation.espressif.com/esp32_datasheet_en.pdf)

### Inferences

All figures in this block are [Own calculation] unless marked.

- 3 m/s is 5.8 kn, above the Otter's 4.5 kn (2.3 m/s). One hull is thin evidence, and the brief's 3 m size is larger, but "3 m/s for 7 h" is not supported by what was verified.
- Radio: two-ray at 8 km with antennas at 2 m gives 144.1 dB. Maximum range: LongFast 13.4 km, or 7.5 km with 10 dB margin; ShortFast 7.5 km, or 4.2 km with margin; ESP32 at 1 Mbps about 1.8 km, or 1.0 km with margin (118 dB budget). Radio horizon at 2 m/2 m is 11.7 km.
- A shore mast helps: 2 m to 10 m gives horizon 18.9 km, and 12 km costs 137.2 dB, about 7 dB easier than 8 km between boats.
- AIS: horizon from a 1.5 m antenna to a 25 m ship antenna is 25.6 km, and to a 4 m small-craft antenna 13.3 km.
- Camera horizon from 1 m: 3.6 km to the sea surface. Upper parts of a target show further: 11.6 km for 5 m height, 14.9 km for 10 m, 19.5 km for 20 m.
- Pixel limits for 1080p across 60° (0.545 mrad): detect a 15 m high ship at 13.8 km, recognise at 3.4 km, identify at 2.1 km; detect a 3 m RIB at 2.75 km; read 0.5 m letters at about 183 m. With a 20° lens: 41 km, 10 km, 6.4 km, 8.3 km and 550 m. These are geometric upper bounds that ignore haze, waves and motion.
- Four boats on the midline cover the whole strip once radius reaches 5.9 km; five need 5.59 km; three need 6.51 km.

#### Recommended values

| Parameter | Plan | Recommended | Status and basis |
|---|---|---|---|
| Speed | 3 m/s | Keep 3 m/s; sensitivity run at 2.3 m/s | Assumption; 2.3 m/s is Otter top speed |
| Endurance | 7 h | Keep | From brief |
| Visit-credit radius (verify) | 500 m | 500 m as `r_verify` | Pixel limit for reading hull marks is 183–550 m |
| Ship detection, day | none | 5,000 m | [Judgement] well inside 11.6–14.9 km geometry and 13.8 km pixels |
| Small craft detection, day | none | 1,500 m | [Judgement] inside 2.75 km pixel limit |
| Detection, night, lit | none | 5,000 m | [Judgement] inside the required light ranges |
| Detection, night, unlit | none | 500 m | [Judgement] with no source; state plainly that a visible camera is weak here |
| Keep-in-view for shadowing | implicit 500 m | 2,000 m | [Judgement] would cut the 986 s approach to about 319 s |
| AIS receive, Class A | none | 20,000 m | Under 25.6 km horizon and 20 nmi nominal |
| AIS receive, Class B | none | 8,000 m | Under 13.3 km horizon |
| Radio boat to boat | 8 km | Keep; sensitivity at 4 km | Label "narrowband or licensed link, low data rate" |
| Radio shore link | 8 km | 12 km | Mast gives about 7 dB more than boat-to-boat at 8 km |
| Delay, loss | 0.25–1 s, 5% | Keep | Chosen test inputs |
| Heartbeat / peer stale | 2 s / 8 s | 5 s / 20 s | Fits a narrowband story |
| Lease | 20 s per task | 60 s per boat | Cheap against multi-hour cycles |
| Bid window | 6 s per task | 12 s slot | 4-hop p99 is 6.65 s; p99.9 is 8.61 s |
| Stale contact | 15 s | 60 s, scout holds until relieved | Team fix plus [Judgement] |
| Shadow cap | 120 s | 1800 s | Team fix |
| Revisit target | 600 s | 10,800 s | 0% overdue before event with corridor |
| Run length | 1800 s | 16,800 s | Best separation found; under the about 17,400 s return limit (N9) |
| Events | 600 / 720 / 900 s | 7,200 / 7,320 / 7,500 s | Same offsets as the plan |

Consequence of two radii: scouts see ships far beyond the route, so the lane needs less driving. Lane boats become AIS-cued responders, which is idea 1. Detection creates a contact; only a pass within `r_verify` freshens a route sample.

### Gaps
- Only one real USV was verified. Heron and other small USV specs were not obtained, so the speed range rests on the Otter.
- No measured over-water ranges for small-boat mesh radios were found; all range figures are model-based. Waves, boat motion and antenna gain are not modelled, and the two-ray model assumes a flat surface.
- ITU-R M.1371 itself was not read. Class A and B figures are via Wikipedia because the USCG pages were blocked.
- SeaShips and measured ship-detection ranges from about 1 m above water were not obtained. SMD was read at abstract level only, so there are no measured camera ranges here.
- COLREG values above are from the US rule; the "miles" there were not confirmed as nautical on that page. Minimum height of hull markings could not be confirmed.

## 5. AIS-based cueing

### Takeaway
Use dead reckoning for crossing time, and a cell-by-course-by-speed count table for "unusual here". Both are explainable and trainable within an hour once data is parsed. Skip neural methods. Thresholds alone produce too many false alarms, so an alert should only trigger a boat to go and look, and must never claim intent.

### Cited Findings
- TREAD applies DBSCAN to vessel flows to extract waypoints and routes, judges normality from transition probabilities between waypoints, and also uses rule alerts such as port speed limits or restricted-area entry — [Pallotta, Vespe & Bryan, Entropy 2013](https://www.mdpi.com/1099-4300/15/6/2218/htm) (search excerpts only; full text blocked)
- Ristic et al. use adaptive kernel density estimation over historic AIS and a Gaussian-sum tracking filter — [Ristic et al., FUSION 2008](https://dblp.uni-trier.de/rec/conf/fusion/RisticSMG08.html)
- GeoTrackNet learns a probabilistic neural model of tracks and adds a location-aware a contrario detector, evaluated on over 4.2 million AIS messages — [Nguyen et al.](https://arxiv.org/abs/1912.00682)
- A French drift study flagged a ship as adrift if it met two of three criteria: under 4 knots, drift angle over 10°, or "not under command". True positive rate was 90%, and 37% of its alerts were false; even 1% false positives would mean a dozen false alerts per hour at a surveillance centre — [Ackermann et al., MARINE 2023](https://scipedia.com/wd/images/2/2f/Gillan_Schmitt_2023a_5582_on_the_use.pdf)
- That study removed clearly bad records, such as a cargo ship reporting over a hundred knots — [Ackermann et al.](https://scipedia.com/wd/images/2/2f/Gillan_Schmitt_2023a_5582_on_the_use.pdf)
- Anchored-vessel drag studies identify anchored ships by speed and label dragging as leaving a vessel-specific anchor circle built from heading, chain length and dimensions — [EGU26-16188](https://meetingorganizer.copernicus.org/EGU26/EGU26-16188.html)
- A Korean VTS method estimates the turning-circle centre from AIS heading and position — [KoreaScholar](https://db.koreascholar.com/Article/Detail/261733)
- A fuzzy method associates higher ground speed and yaw width with higher drag probability, and higher heading change rate with lower probability — [SPIE record](https://medicalimaging.spiedigitallibrary.org/profile/Yongtao.Xi-4473990)
- Yi Peng 3 was reported at about seven knots, with AIS off for 7.5 hours after Gotland. Investigators quoted by the WSJ suspected over 100 miles of anchor drag, while naval journalist Tom Sharpe doubted that scenario at seven knots — [Wikipedia, 2024 Baltic cable disruptions](https://en.wikipedia.org/wiki/2024_Baltic_Sea_submarine_cable_disruptions)
- Eagle S's anchor was found at the end of a drag line of about 100 km; design speeds are 12 kn service and 14.5 kn maximum; officers were charged on 11 August 2025; the page gives no verdict — [Wikipedia, Eagle S](https://en.wikipedia.org/wiki/Eagle_S)
- Global Fishing Watch keeps only gaps of at least 12 hours, over 50 nm from shore, with over 10 pings per day. It excludes near-shore waters because of interference, and reports false-positive rate 3.72%, precision 0.86 and F0.5 0.739 — [Welch et al., Science Advances 2022](https://escholarship.org/content/qt3xs2q931/qt3xs2q931.pdf)
- Class A reports every 2–10 s under way and every 3 min at anchor; Class B CS every 30 s, or 3 min under 2 knots — [Wikipedia, AIS](https://en.wikipedia.org/wiki/Automatic_identification_system)
- DMA offers free historical AIS as CSV in ZIP files and states no usage terms on that page — [DMA](https://www.dma.dk/safety-at-sea/navigational-information/ais-data)
- EMODnet lists telecom cable routes and vessel density rasters, described as free of restrictions — [EMODnet](https://emodnet.ec.europa.eu/en/human-activities)

### Inferences

#### Method choice

| Method | Train on 1–3 days? | Explainable? | Decision |
|---|---|---|---|
| Dead reckoning | No training | Yes | Use for crossing time |
| Cell × course × speed table | Under an hour [Judgement] | Yes | Use for "unusual here" |
| Kernel density | Feasible | Mostly | Skip; the table is simpler |
| TREAD | Probably thin | Partly | Cite as the grown-up version |
| GeoTrackNet, autoencoders | No | Weakly | Skip this weekend |

#### Recipe (budget: one hour for the data gate, then 4 hours)
1. Clip one day to the demo box, drop implausible speeds, split tracks at gaps over 10 min. Use a second day as held-out.
2. Use a 500 m grid, 8 course bins and 4 speed bins. Count with add-one smoothing.
3. Score = −log P(course bin, speed bin | cell). Threshold at the 99.5th percentile of held-out scores.
4. Crossing cue: project position by SOG and COG for up to 30 min. If the track meets a cable corridor, create `xing:{mmsi}:{cable}`.
5. Only auction a cue when the score is unusual, or the speed-drop rule fires inside the corridor. Otherwise every lane ship would create a task, since a cable under a lane is crossed by everything.
6. Feasibility: a boat bids only if ETA is before crossing time minus a margin. At 12 kn a ship makes 6.2 m/s, twice boat speed, so boats intercept ahead and cannot chase.
7. Validate honestly with synthetic injected events. Report only "found N of M injected events on one held-out day".

#### What anchor dragging looks like
Two different things:
- Ship at anchor dragging in weather: low speed, position leaves the anchor circle, heading and course diverge.
- Ship under way with anchor down, the Baltic concern: reported speeds near 7 kn against a 12 kn service speed. Proposed rule: speed falls over 30% below its own 30-minute median without a course change, inside a cable corridor. The 30% figure is my choice with no validation behind it. Experts dispute the physics at those speeds, so call it a speed anomaly and do not call it anchor dragging.

#### AIS gaps
Global Fishing Watch's method does not transfer: it is for offshore satellite coverage and explicitly avoids crowded near-shore water. Use a local rule instead:
```python
expected = interval_for(class_, status, sog)        # 2–10 s, 30 s or 3 min
silent = now - last_rx > max(6*expected, 60_000)
heard_others = count_vessels_rx(window=expected*6, range_at_least=predicted_range)
reception_gap = silent and heard_others == 0        # our receiver is probably the problem
suspected_off = silent and heard_others >= 3 and predicted_inside_rx_range
```
The multiplier and counts are team-chosen defaults. A vessel that never transmitted produces no gap at all, so dark contacts still need a camera detection.

Fleet voting helps: a track is only "silent" if every boat in range agrees, since the boats share AIS records.

### Gaps
- Whether DMA's portal works, its file size and its CSV schema are unknown: it reset connections on HTTP and HTTPS. Test this first on Friday, and fall back to labelled synthetic traffic.
- Daily vessel counts and cable-crossing counts for any Danish strait were not found. The handoff note says idea 1 is unproven until one AIS day is counted.
- No sourced dead-reckoning error figures were found, so the 30-minute horizon is a judgement.
- AIS field conventions such as heading 511 meaning "not available" are from memory [Unverified]. Check against the CSV.
- No verified Danish cable routes: EMODnet lists telecom cables, while power cable data was not checked. Reuse terms for DMA data are unconfirmed.

## 6. GPS spoofing detection among peers

### Takeaway
Impossible-jump detection is not enough, because a carry-off attack moves a receiver gradually. In a 2D sim the strongest cheap check is radio range consistency, plus withholding visit credit from a distrusted boat. No peer check can catch a spoof that moves the whole fleet together.

### Cited Findings
- Spoofing makes receivers compute false position or time and is hard to spot because counterfeit signals resemble real ones — [Wikipedia, Spoofing attack](https://en.wikipedia.org/wiki/Spoofing_attack)
- In a carry-off attack the spoofer first synchronises with genuine signals, then raises power and pulls the receiver away gradually — [Wikipedia, Spoofing attack](https://en.wikipedia.org/wiki/Spoofing_attack)
- Using more than one navigation system at once is recommended, and Galileo OSNMA added signal authentication in 2025 — [Wikipedia, Spoofing attack](https://en.wikipedia.org/wiki/Spoofing_attack)

### Inferences

| Check | Catches | Misses | Effort |
|---|---|---|---|
| Speed gate: step over v_max × dt × 1.5 | Sudden jump | Gradual drag | 20 min |
| Range consistency: I hear you directly, but you claim to be beyond range × 1.2 | Large offsets | Small offsets, common-mode | 30 min |
| Neighbour set: your claimed position implies peers you do not report hearing, or the reverse | Moderate offsets | Sparse fleets | 45 min |
| AIS cross-check: reported position vs the set of ships it hears at that range | Moderate offsets | Fleet-wide spoof, since ships' own GNSS may be spoofed too | 1 h |
| Camera bearing to a peer or AIS ship | Small offsets | Needs line of sight; synthetic here | 1 h |

Action when flagged, because detection without consequence shows nothing:
1. Peers mark the boat `POSITION_UNTRUSTED`.
2. Its visits stop freshening route samples.
3. Its tasks are released and re-auctioned.
4. Dashboard shows reported age and true age side by side, using the labelled evaluator view.

That last split is the demo: a spoofed boat makes a cable look fresh while nobody is there.

Priority: P2, about 3 h, only after the evidence log. Signed messages stop a forged sender, not an honest boat fed false GNSS, so the two ideas do not overlap.

### Gaps
- Primary spoofing papers were not read. Tippenhauer et al. (CCS 2011) and Psiaki's work are from memory [Unverified]. The C4ADS report's URL returned 404.
- No Baltic-specific GNSS interference source was verified, so do not quote incident figures.
- The checks above are my design and were not tested.

## 7. Tamper-evident logs

### Takeaway
About 3 hours with a per-boat hash chain, Ed25519 signatures on periodic heads, and log heads carried in heartbeats so peers can witness them. It proves records were not edited later, not that a sensor told the truth.

### Cited Findings
- A tamper-evident log must detect tampering within a signed log and detect different instances making inconsistent claims. Hash-chain logs need auditors to examine every intermediate event, and history trees bring that to logarithmic — [Crosby & Wallach, USENIX Security 2009](https://www.usenix.org/legacy/event/sec09/tech/full_papers/crosby.pdf)
- Schneier and Kelsey make entries written before a compromise unreadable and prevent undetected change or deletion — [Schneier & Kelsey, ACM TISSEC 1999](https://www.schneier.com/academic/archives/1999/05/secure_audit_logs_to.html)
- `cryptography` offers `Ed25519PrivateKey.generate()`, `.sign(data)`, `Ed25519PublicKey.verify(sig, data)` and `public_bytes_raw()`; signatures are 64 bytes; failure raises `InvalidSignature` — [cryptography docs](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- JSON has many byte forms, so canonicalise before hashing. JCS sorts properties and fixes number formatting, and rejects NaN and Infinity — [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.txt)

### Inferences

Design:
```python
entry = {"seq":n, "t_ms":t, "boat":b, "kind":k, "body_sha256":h, "prev":prev_hash}
entry_hash = sha256(rfc8785.dumps(entry)).hexdigest()
# every 20 entries, and on any task or contact change:
head = {"boat":b, "seq":n, "hash":entry_hash, "t_ms":t}
sig = key.sign(rfc8785.dumps(head))
```
- Sign heads only. Log task records, contact observations, veto receipts and operator actions.
- Use integers (metres, milliseconds) in entries to avoid float formatting issues.
- Every heartbeat carries `(seq, hash)`, and each peer logs what it received. Truncating a log afterwards then conflicts with heads already held by peers, which covers the inconsistent-claims point. A linear chain is fine at this scale, so skip Merkle trees.
- `verify.py` walks each chain, checks signatures, cross-checks witnessed heads, and prints pass or the first bad sequence number.
- Generated incident report: a contact timeline with hashes. Demo moment: edit one line of a saved log and run the verifier.
- Keep this out of the determinism hash, or derive keys deterministically from the seed.

Effort [Judgement]: chain and signing 1 h, witness logging 30 min, verifier 45 min, report 45 min.

### Gaps
- `from_private_bytes` for deterministic keys, and whether signing cost matters at this rate, were not checked. `cryptography` is not installed here, so nothing was timed.
- Haber & Stornetta (1991) as the origin of hash-linked timestamps is from memory [Unverified].

## 8. Real radios

### Takeaway
Feasible but not worth doing this weekend unless someone already owns boards. Run agents on a laptop with boards as dumb radios. No verified Copenhagen same-day stock was found, range cannot be shown indoors, and a linked-video demo reduces the "unplug it live" value.

### Cited Findings
- MicroPython's `espnow` supports ESP32. Payload is 250 bytes on v1, 1470 bytes on v2 with ESP-IDF 5.4 or later. Peers: 20 total, 6 encrypted — [MicroPython docs](https://docs.micropython.org/en/latest/library/espnow.html)
- ESP-IDF states the same 20 peers but up to 17 encrypted, default 7, which differs from MicroPython's 6 — [ESP-IDF ESP-NOW](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_now.html)
- Packets are dropped when receive buffers fill even though the sender gets an acknowledgement; Wi-Fi power saving makes reception unreliable; `irq()` callbacks can be missed under load; `recv()` allocates and can fragment memory — [MicroPython docs](https://docs.micropython.org/en/latest/library/espnow.html)
- There is no application-level delivery guarantee, so Espressif suggests app-level ACKs, retransmission and sequence numbers; callbacks must stay short; default rate is 1 Mbps — [ESP-IDF ESP-NOW](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/network/esp_now.html)
- All peers must share a Wi-Fi channel — [MicroPython docs](https://docs.micropython.org/en/latest/library/espnow.html)
- ESP32 has 520 KB of SRAM — [ESP32 datasheet](https://documentation.espressif.com/esp32_datasheet_en.pdf)
- Let Elektronik lists ESP32 NodeMCU boards at 80 and 88 DKK and has a LoRa category with no products visible on the home page. It is in Fredericia, opens 08:30–17, and ships stock in 1–2 weekdays — [Let Elektronik](https://let-elektronik.dk/)
- Ardustore lists an ESP32 development board category; location and pickup were not shown — [Ardustore](https://ardustore.dk/)

### Inferences

| Option | Verdict | Why |
|---|---|---|
| Agent loop in MicroPython on ESP32 | No | Five boards to debug, memory fragmentation, slow insertion bids, and a second implementation that breaks determinism [Judgement] |
| Laptop agents, boards as radios over USB serial | Possible P2 | Keeps one codebase; `radio` interface swaps backend. About 4–6 h [Judgement] |
| LoRa boards | No | 1.07 kbit/s at 10% duty gives 107 bit/s per node. Heartbeats alone need 160 bit/s at the plan's 2 s, or 64 bit/s (60% of the allowance) at the recommended 5 s, before any bids or records [Own calculation] |
| Skip hardware | Recommended | Shipping from Fredericia on a Friday will not arrive in time, and no same-day pickup in Copenhagen was confirmed |

If boards already exist: five ESP32 dev boards with USB data cables (about 400–440 DKK at the Let Elektronik prices above), fixed channel 1, `sta.config(pm=sta.PM_NONE)` and `reconnects=0`, a bridge sketch that passes framed bytes between serial and ESP-NOW broadcast, and a 250-byte message cap. Keep range simulated: gate packets in software, because a room shows nothing about 8 km. Risks: crowded 2.4 GHz at the venue, Windows COM port shuffling, serial latency.

The honest pitch for hardware is "same protocol over a real lossy link", and only if finished before the Saturday 23:00 freeze.

### Gaps
- No Copenhagen shop with same-day ESP32 stock was verified; web search was unavailable by then. Check any local maker shop or ask other teams.
- Arduino ESP-NOW API and ESP32 long-range mode details were not checked. Wi-Fi LR range claims are unverified.
- Current MicroPython firmware version was not checked. `mpremote` 1.29.0 and `esptool` 5.6.0 exist on PyPI, not tested.

## 9. Simulator and dashboard architecture

### Takeaway
Use a fixed 1 s tick with integer milliseconds, a heap for radio deliveries, a pre-drawn channel tape so all modes face identical radio conditions, JSONL logs, and a plain Canvas map fed by WebSocket at 10 Hz. Avoid tiles and bundlers.

### Cited Findings
- `SeedSequence.spawn` and `Generator.spawn` create independent child streams from one seed — [NumPy docs](https://numpy.org/doc/stable/reference/random/parallel.html)
- Python seeds `str` and `bytes` hashes randomly unless `PYTHONHASHSEED` is set — [Python docs](https://docs.python.org/3/using/cmdline.html)
- Dicts preserve insertion order, while sets are unordered and make no promise on iteration order — [Python data model](https://docs.python.org/3/reference/datamodel.html)
- `websockets.asyncio.server.broadcast()` sends to all clients without yielding and applies no backpressure; slow clients are dropped on ping timeout — [websockets docs](https://websockets.readthedocs.io/en/stable/topics/broadcast.html)
- Latest PyPI versions on 6 Nov 2026: numpy 2.5.4 (requires 3.12+), shapely 2.2.0, websockets 17.4, msgspec 0.22.0, pytest 9.2.0, hypothesis 6.170.14, cryptography 50.0.2, rfc8785 0.1.4, pandas 3.1.1, scikit-learn 1.9.1, pyproj 3.8.0, pyserial 3.5 (2020) — [PyPI](https://pypi.org/)
- npm dist-tags on 6 Nov 2026: leaflet latest 1.9.4 with 2.0.0-beta.1 as beta; maplibre-gl 6.16.0; deck.gl 9.4.1; pmtiles 4.5.0 — [npm](https://www.npmjs.com/package/leaflet)

### Inferences

#### Core loop
```text
each tick (1 s sim):
  1 world.step()           motion, battery, scripted events
  2 radio.deliver(t)       heap of (deliver_ms, seq, dst, msg)
  3 agents step in ID order, each with only its own sensors and inbox
  4 metrics.update(t)      ground truth, evaluator only
  5 if due: emit snapshot, log state hash
```
- Integer milliseconds everywhere. Agents read `t` from an argument, never `time.time()`.
- Messages cross the radio as encoded bytes, then decoded. This blocks shared mutable objects, which are the likeliest hidden leak, and enforces a size limit.
- Channel tape: pre-compute drop and delay per directed link per second from `Generator.spawn`, about 500,000 link-seconds for 16,800 s on 30 directed links. Adaptive and baseline then see identical radio weather even though they send different messages. This is the common-random-numbers idea and is the key fairness trick.
- Warm-up: one headless run to steady state, saved as `warm_state.json`, is the start point for every mode and every demo.
- Headless batch: `python -m eval.run_batch --modes adaptive,off,manual --seeds 1,2,3,4,5`, writing `runs/<config-hash>/`.

#### Replay and messages
- JSONL. Line 1: seed, config hash, git commit, schema version. Then event lines, plus snapshots every 10 sim-s and a state hash every 60 sim-s.
- Replay re-runs from seed plus injection list and checks the hashes. It does not play back snapshots.
- Envelope: `msg_id, src, t_created, t_expire, kind, hops, payload`.
- Kinds: `HB, BID, REC, OBS, CONTACT, VETO, ACK`.
- Snapshot shape: `{t, speed, boats[{id,x,y,mode,batt,link,tour}], tasks{id:{v,owner,deputy,state}}, seg_age{}, contacts[], events[]}`.
- Two WebSocket channels: `/shore` carries delivered data only, and `/truth` carries evaluator data on a separate labelled panel.

#### Time-warp and frame rate
- 10 Hz of snapshots at 60× is 6 sim-s per frame. A boat moves 18 m, under 1 pixel on a 1,000 px map of 25 km, so 5–10 Hz is ample [Own calculation].
- Fixed 60× hides repair and overruns the pitch. Use automatic warp: 240× between events, dropping to 5× for 120 sim-s around each event. 16,800 s at 240× is 70 s, plus 24 s for each of 3 slowed events, about 2 min 20 s for a video [Own calculation]. Trim the quiet periods further if the video must be shorter.

#### Map choice

| Option | Decision |
|---|---|
| Plain Canvas 2D in local metres | Use. No tiles, no network, matches the plan's fallback |
| Leaflet 1.9.4 with local GeoJSON | Only if real geography is added; avoid 2.0 beta |
| MapLibre, deck.gl, PMTiles | Skip; setup cost with no story gain |

Keep the UI to one `index.html` and two JS files with no bundler. Coastline, if used, is a static GeoJSON converted to local metres with `pyproj`.

#### Repo layout
```text
edth07/
  requirements.txt
  config/default.toml      every number, hashed into each run
  scenarios/fixed.toml     event tape
  contract/                frozen Fri 21:00; change needs A + B
    constants.py messages.py tasks.py views.py
  agent/      (A)          imports contract only
    core.py table.py auction.py tour.py relay.py contact.py deputy.py
  world/      (B)
    sim.py routes.py motion.py sensors.py radio.py channel.py
  eval/       (D)          never imported by agent/
    metrics.py run_batch.py report.py
  server/     (C)
    bridge.py replay.py
  web/        (C)
    index.html map.js panels.js
  ais/        (B, gated)   offline; emits a replay file
  evidence/   (C)
    chain.py verify.py
  tests/
  runs/                    gitignored
```
Rules: each person stays in their own folder, `contract/` changes by pull request only, `main` must always pass `pytest -q tests/smoke`, and a tagged `core-fallback` is kept.

#### Install
Not installed or tested in this session. Versions are from PyPI metadata. Everyone should use the same Python minor; this machine has 3.14.3, and 3.12 or newer works with numpy's requirement.

`requirements.txt`:
```text
numpy==2.5.4
shapely==2.2.0
websockets==17.4
msgspec==0.22.0
pytest==9.2.0
hypothesis==6.170.14
cryptography==50.0.2
rfc8785==0.1.4
pandas==3.0.5
scikit-learn==1.9.1
pyproj==3.8.0
```
pandas 3.0.5 is pinned rather than 3.1.1 because 3.1.1 is two days old and 3.0.5 is what this machine already runs. If numpy's newest wheel causes trouble, 2.4.6 is also already installed here. `scikit-learn` is optional, since the grid model needs only numpy. `pyserial==3.5` only if boards are used.

PowerShell:
```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -c "import numpy, shapely, websockets, msgspec, cryptography, rfc8785; print('ok')"
pytest -q
```
Bash:
```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
```
Run this before 19:00 and on venue Wi-Fi. Windows wheels for cp312 were confirmed in metadata for numpy, scipy, shapely, pyproj, websockets and pandas; msgspec's listing was cut off in my check.

#### Test list
Determinism:
- D1 Same seed in two separate processes with different `PYTHONHASHSEED` gives identical state hashes.
- D2 Reset mid-run equals a fresh run.
- D3 Replay from injection log matches hashes.
- D4 Grep test: no `time.time`, no global `random`, no iteration over a set without `sorted`.
- D5 Hypothesis: merge is commutative, associative and idempotent; any delivery order gives one final record.
- D6 Import test: `agent/` imports neither `world/` nor `eval/`.

Baseline fairness:
- F1 Warm state, event tape and channel tape hashes are equal across modes.
- F2 Seg ages at T−1 are byte-identical across modes. This is the strongest single fairness test.
- F3 `reassignment=off` produces zero repair claims after T.
- F4 Config diff between modes is exactly one key.
- F5 Report at least 5 seeds, with median and range; no single-seed headline.

Protocol:
- P1 Lost bid: cheaper boat wins on merge.
- P2 Winner dies mid-round: task re-auctioned next slot.
- P3 Refresh arrives mid-window: round cancelled.
- P4 Isolated boat claims nothing expired.
- P5 Rejoin: no boat idle after two rebalance periods.
- P6 Claim beats release at equal version.
- P7 Group with shore path elects no relay.
- P8 Deputy takes relay with radio silent, or declines.
- Plus the plan's existing acceptance tests. Its split-and-rejoin test must change: only the majority side claims on expiry.

### Gaps
- No speed benchmark exists for the real simulator, and headless run time is not measured.
- Whether msgspec has a cp314 wheel for Windows was not confirmed. Fallback is `dataclasses` with stdlib `json`.
- OSM land polygons were unreachable, so no offline coastline source is verified.

## 10. Module list, effort, parallel split and integration risks

### Takeaway
P0 is about 64 person-hours against about 84 available, leaving room for only some extras. Do the deputy and evidence log first, gate AIS behind the Core fallback, and cut boards and the drone. All hours are judgement estimates.

### Cited Findings
- The plan's workstreams are A swarm brain, B world and comms, C dashboard, D product, proof and pitch, with milestones Fri 21:00, Sat 00:00, Sat 12:00, Sat 18:00, Sat 23:00 — [current-plan-copy.html](C:\Users\franc\Desktop\studia\ElysasSecret\EDTH\research_notes\Challenge 07 scoring research\current-plan-copy.html)
- Past-note context: the team handoff recommends patrol the ships, named deputy and evidence log, pending team decision, with idea 1 unproven until one AIS day is counted. This comes from a project memory note and was not re-verified.

### Inferences

#### Modules [Judgement]

| ID | Module | Pri | Owner | Hours | Depends on | Exit check |
|---|---|---|---|---|---|---|
| M0 | Contract, config, event tape | P0 | A+B | 4 (2 each) | none | Schema frozen Fri 21:00 |
| M1 | World: motion, battery, routes, corridor, samples, sensors | P0 | B | 5 | M0 | Five boats patrol, Sat 00:00 |
| M2 | Radio: range, delay, loss, store-and-forward, channel tape | P0 | B | 4 | M0 | Link-off test passes |
| M3 | Agent core: table, merge, heartbeat, per-boat lease | P0 | A | 4 | M0 | D5 passes |
| M4 | Slots, bids, cheapest insertion, repair, rebalance | P0 | A | 7 | M3 | P1–P6 pass |
| M5 | Relay task and shore-age gossip | P0 | A | 2.5 | M4, M2 | P7, relay-loss test |
| M6 | Contact, shadow, veto, last-scout guard | P0 | A+C | 5 (3+2) | M4 | Story tests |
| M7 | Evaluator, warm-up, scenario runner, baseline switch | P0 | D | 4 | M1 | F1–F5 |
| M8 | Bridge, replay, time-warp | P0 | C | 3 | M1 | D3 |
| M9 | Dashboard: map, roles, ages, links, veto, failure controls | P0 | C | 8 | M8 | Judge can break any boat |
| M10 | Test suite | P0 | D | 4 | all | CI green |
| M11 | Integration buffer | P0 | all | 8 | all | Full story runs |
| M12 | Pitch, deck, video, submission | P0 | D (C on video) | 6 | M9 | Deck in by noon |
| M13 | Named deputy | P1 | A | 2 | M5 | P8 |
| M14 | Evidence log and verifier | P1 | C | 3 | M3 | Tamper demo |
| M15 | AIS ingest and grid model | P1 gated | B | 5 | Core fallback | Injection result |
| M16 | AIS-cued tasks | P1 gated | D | 3 | M15, M4 | Cue flows through auction |
| M17 | Spoofed boat | P2 | A or D | 3 | M14 | True vs reported age |
| M18 | Radio boards | P2 | none | 5 | M2 | Only if boards exist |
| M19 | Boat-launched drone | Cut | none | 0 | none | Out of scope; no parameters verified |

Totals: P0 64.5 h, P1 13 h, P2 8 h. Capacity assumption: four people × about 21 focused hours = 84 h. P0 plus P1 is 77.5 h, leaving about 6.5 h, so if P0 slips, P1 goes first.

Order for extras: M14 and M13 first, since they are cheap and need no external data; M15 and M16 only if the data gate passes in one hour; M17 only if Saturday evening is clear.

The manual-operator comparison is P0 in the plan and not separately costed here. If time is short, run it once and label it, or cut it as the plan's cut order allows.

#### Parallel split

| Block | A swarm brain | B world and comms | C dashboard | D proof and pitch |
|---|---|---|---|---|
| Fri 19–21 | Contract | Contract | Snapshot schema review | Mentors; record decisions; read jury criteria |
| Fri 21–Sat 00 | Table, merge, tests | Routes, corridor, motion | Canvas map from a fake snapshot | Warm-up and evaluator skeleton |
| Sat 08–12 | Slots, bids, repair | Radio, channel tape | Live bridge, failure controls | Baseline runner; fairness tests |
| Sat 12:00 | Tag `core-fallback` | | | First ON/OFF numbers |
| Sat 12–18 | Relay, split and rejoin, rebalance | Store-and-forward; AIS gate 1 h | Link and freshness views, time-warp | Protocol tests; metric review |
| Sat 18–23 | Contact, deputy | AIS model if gate passed | Veto UI, evidence log | AIS cues if gate passed; deck draft |
| Sat 23:00 | Feature freeze | | | |
| Sun 08–10 | Bug fixes only | Bug fixes only | Record video | Final 5-seed results |
| Sun 10–12 | Code freeze at 10:00 | Offline copy | Video edit | Deck and submission by 11:30 |

The plan's Sunday times assume about 13:00 and need moving earlier if the noon deadline is confirmed. Assumes sleep from about 00:00 to 08:00.

#### Riskiest integration points
1. **A with B, timing semantics.** Slots, leases and message ordering rest on the tick contract. Test with a fake radio on Friday night.
2. **Hidden state sharing.** A shared object or evaluator data reaching an agent invalidates the "no coordinator" claim. Encode at the radio boundary and run D6.
3. **Metric not separating modes.** If corridor and cost changes do not show a gap by Sat 12:00, the result slide has nothing. D checks early and owns this.
4. **Contact with patrol.** Shadow release, last-scout guard and the boat's return touch every other rule. This is where the idle-boat bug lives.
5. **Rejoin behaviour.** Merge plus rebalance can oscillate. Keep the one-release-per-period limit and watch version counts.
6. **Time-warp with event display.** Events must slow down before they happen, so warp reads the scripted tape and not a live trigger.
7. **AIS replay gating.** Replay must respect each boat's reception range and never broadcast a global table.
8. **Data gate overrun.** One hour, then synthetic. The portal did not respond from this environment.
9. **Late features.** Nothing new after Sat 23:00, and the fallback tag stays runnable.

### Gaps
- All hours are judgement estimates and team skills per module are unknown.
- Actual team allocation, sleep and the pre-19:00 code rule remain to be confirmed.
- The guide's jury criteria may reorder P1, because the memory note says seven criteria are published. Read them before locking priorities.
