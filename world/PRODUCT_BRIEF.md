# Elysa’s Secret — product pitch and roadmap

A point-in-time summary based on the GitHub review of main at `b50da01`. Implementation and open-item status should be rechecked before external use.

## The pitch

**Elysa’s Secret is a coordination system for a small fleet of uncrewed patrol boats protecting maritime infrastructure.**

Imagine one shore operator watching cables across the Great Belt. One boat runs low on battery. Another loses its direct radio link. Then a patrol boat sees a vessel lingering near a cable without AIS.

Today, the operator would have to reorganize the patrol manually. Our system lets the boats redistribute work, relay observations, and assign a watcher themselves—while the operator approves consequential actions.

**The important promise isn’t “we magically maintain complete coverage.” It’s: “we repair what we can, and clearly show what becomes uncovered.”**

We’re building the decision layer between **an alert appearing** and **a boat being sent**, including the cost of that response to the rest of the patrol.

## Future ideas at a glance

Proposed improvements—not a list of completed capabilities. Links lead to the detailed sections below.

- **[Independent USVs](#7-prove-independent-operation-solo-with-peers-and-with-shore):** preserve onboard core functions when peers or the dashboard disconnect; demonstrate clean reconnection.
- **[Explainable assignments](#1-explain-every-assignment):** show why a boat received a task and what it gives up.
- **[Response-cost previews](#2-preview-the-operational-cost-before-approval):** estimate coverage and energy consequences before approval.
- **[Mission-level energy management](#3-add-mission-level-energy-management):** budget tasks and recovery reserves, manage power priorities, and rotate boats through charging.
- **[Honest uncertainty](#4-represent-uncertaintynot-just-positions):** show stale tracks, positioning uncertainty, and incomplete observations.
- **[Gazebo and autopilot integration](#next-stage-vision-a-maritime-testbed-in-gazebo):** test the same fleet brain against richer dynamics and sensors, then connect ArduPilot SITL.
- **[Explainable AIS triage](#6-add-explainable-ais-triageafter-the-gate):** rank cues for human review and connect them to feasible responses.
- **[Satellite-inspired resilience](#what-we-can-borrow-from-satellites):** resource-aware scheduling, degraded modes, fault recovery, and prioritized data delivery.

## What is implemented

### 1. A working simulated fleet

- Five boats over public approximate Great Belt cable routes.
- Two cable sweepers, two lane pickets, and a relay.
- Motion, battery consumption, current/tide reversal, and low-power SENTINEL drift-and-correct.
- Range-limited sensors and radio, with delay, packet loss, directed link cuts, and peer forwarding.
- Deterministic seeds, reset, failure injection, and boat restoration at the world layer.

These are **simulation models**, not calibrated claims about a real hull.

### 2. Decentralized task allocation

Each boat runs its own decision logic:

- Auctions assign work using travel, workload, battery, and role costs.
- Leases identify unavailable owners.
- Task records reconcile after communications recover.
- Returning boats release their assignments.
- Replacement boats prioritize older, unvisited work.
- Deputies can take over a silent relay or watcher.

The allocation logic is decentralized; the demonstration currently runs these agents together in a simulator—not on five physical boats.

### 3. The contact-response story

- Boats detect the synthetic camera-only contact.
- The scout keeps it in view until another boat takes over.
- Shore receives contact reports through the radio.
- Confirm/Stop and Approve/Decline cards support operator control.
- Staleness, battery limits, time caps, and a faster-departing contact constrain the response.

This demonstrates a **cue for a look**, not automated intent detection.

### 4. A usable operator console

- Offline chart, fleet cards, contact tracks, communications overlay, and coverage ages.
- Clearly separated delivered shore knowledge and evaluator truth.
- Alerts, decision previews, event narration, failure controls, and stale-data indicators.
- Logging/replay, incident reports, and tamper-evident shore evidence records.

### 5. Evaluation infrastructure

- Static, repair-off, and swarm-repair comparison modes.
- Seeded starts, warm-up, sample-level coverage metrics, and repeatability/fairness checks.
- Real AIS crossing analysis on the **evaluator side**, when the private data is available.

**Important distinction:** the boats do not yet receive real AIS replay through their sensors. And the published performance report needs refreshing after the latest changes; it is not our final headline evidence.

## What still needs finishing—already scheduled

| Work | Current state at this snapshot |
|---|---|
| **Restore GitHub Actions** | Billing/spending restriction prevents jobs from starting. Organization-owner action required. |
| **Python setup documentation** | Implemented in PR **#64**, awaiting merge; retains Python 3.12 and documents the reported Windows workaround. |
| **Dashboard boat restoration** | World support exists, but bridge/UI enablement remains **#63**. |
| **Scorecard in the dashboard** | **#59** connects the evaluator’s generated scorecard to `/truth`, including its preliminary label. |
| **Boat-signed evidence** | PR **#65** adds onboard signed chain heads; requires review, contract sign-off, and shore/report integration. |
| **Final results** | **#19**: rerun the accepted implementation, verify fairness and sensitivities, then update results and deck figures. |
| **Map assets** | Coastline work is implemented; remaining satellite work is tracked in **#9**. |
| **Release proof** | Complete real-console video, final deck, clean-start and actual two-laptop offline checks. |
| **AIS input to boats** | **#52**, deliberately gated until the core and full video are complete. |

The remaining work is largely **integration, evidence, and release readiness**, rather than inventing another major subsystem.

## What would make it a better product?

Priority order:

### 1. Explain every assignment

**“Why did this boat get the task?”**

Show the factors behind a decision: arrival time, battery reserve, existing workload, and the role it would abandon. We already calculate much of this; exposing it would build operator trust.

### 2. Preview the operational cost before approval

The ghost route is useful. The next step is showing the **predicted coverage and energy consequences** of sending that boat.

That turns the console from a fleet display into a decision-support tool. Predictions must remain labelled as model estimates.

### 3. Add mission-level energy management

**“Can this boat complete the task, return safely, and leave enough fleet capacity behind?”**

Current battery consumption, return-home logic, and SENTINEL mode are useful foundations. The next step is an energy manager that protects both the **boat** and the **mission**, rather than reacting only to a low-battery threshold.

- **Budget before assignment:** estimate energy for transit, task execution, station-keeping, sensors, communications, and return to a reachable recovery point. Include an uncertainty reserve; battery percentage alone is not a measure of task feasibility.
- **Replan during execution:** update the budget when current, progress, payload demand, or battery health differs from expectations. Reject or hand over tasks that would consume the recovery reserve.
- **Manage power by priority:** duty-cycle nonessential payloads and reduce optional processing or data transfer when appropriate. Never trade away required navigation safety, essential communications, or battery protection to preserve a patrol metric.
- **Rotate the fleet:** arrange replacements before a boat leaves, account for charging or battery swaps and dock availability, and show when the available fleet cannot meet the patrol target.
- **Explain the trade-off:** show estimated task energy, recovery reserve, remaining useful patrol time, and the coverage lost by returning or reducing activity. Label predictions as model estimates and expose uncertainty.

This is a strong path from a four-hour demonstration toward sustained operations. Charging logistics and hardware power-control interfaces are proposed capabilities, not existing integrations.

**Acceptance scenario:** an adverse current raises a boat’s predicted return cost. Before its reserve is consumed, it requests a handover, the fleet reallocates feasible work, and the console explains any remaining gap. Evaluate reserve violations, unserved work, and recovery outcomes—not just total energy saved.

### 4. Represent uncertainty—not just positions

Show uncertainty around stale tracks, degraded positioning, and incomplete coverage observations. A precise-looking dot can be more misleading than an openly uncertain estimate.

### 5. Build a Gazebo-based maritime testbed

Use **Gazebo as the next-stage simulation environment**, with a path to **ArduPilot software-in-the-loop (SITL)** and eventually a supervised real boat.

The current simulator proves the coordination loop under simplified assumptions. Gazebo would let us test how those decisions survive more detailed vessel motion, environmental disturbances, and simulated sensors. The proposed approach is described below; this integration is **not implemented**.

One credible integration would add more product confidence than several extra dashboard panels. Collision avoidance and navigation safety would need explicit ownership before physical deployment.

### 6. Add explainable AIS triage—after the gate

Use real AIS behaviour to rank items for human review, explain the contributing signals, and offer “send a boat to look.”

Its distinguishing feature should be the connection to response planning: **not just which vessel merits review, but whether we can respond and what patrol coverage that response costs.**

### 7. Prove independent operation: solo, with peers, and with shore

**“Every USV is a complete operational unit; connecting it to others adds capability, not permission to keep functioning.”**

Each boat should be able to carry out its authorized mission on its own, cooperate directly with peers, and accept operator supervision through the dashboard. Disconnecting one layer must not disable the onboard core or require restarting the mission in a different mode.

The current decentralized allocation is a foundation, but agents running together in one simulator process do **not** prove independent deployment. This is a proposed architecture and demonstration requirement, not a claim that the existing system already satisfies it.

#### What must remain onboard

The proposed core is local navigation and safety handling, own-sensor processing and tracking, energy and recovery protection, execution of authorized tasks, health monitoring, and timestamped local event recording. These functions must not depend on a dashboard session, a shore service, a peer leader, or an internet connection. Navigation safety and full onboard sensing remain integration work, not established capabilities of the present decision-layer demo.

Independence does not mean identical mission performance in every mode. A solo boat cannot replace the coverage, relaying, or handovers of a fleet. Shore-only information is unavailable while disconnected, and actions requiring operator approval remain blocked unless already explicitly authorized under a valid policy.

| Operating mode | What the boat must retain | What connection adds |
|---|---|---|
| **Solo: no peers, no shore** | Execute a locally stored, authorized patrol within resource and safety limits; observe, record, and recover without waiting indefinitely for external decisions. | No cooperative coverage or live operator decisions; unmet work remains explicit. |
| **With peers, without shore** | The same local core, plus direct exchange of observations, task allocation, relaying, and feasible handovers. | Fleet coordination without making one peer an indispensable central controller; approval-required actions still wait or expire. |
| **With shore, without peers** | The same local core, with delivered telemetry and valid operator commands. | Human supervision of a single boat without requiring a fleet or quorum. |
| **With peers and shore** | The same local core and peer coordination. | The full supervised fleet experience; dashboard failure must not stop onboard execution. |

#### Demonstrate independence—not just a disconnected screen

- **Separate the runtimes:** run each boat’s agent and adapter in its own process with explicit communication boundaries. Keep the shared simulator as test infrastructure, not an onboard dependency. A later multi-computer demonstration can strengthen deployment evidence.
- **Exercise every mode:** start a boat solo; run peers without shore; supervise one boat without peers; then connect the full fleet. Include cold starts without a shore service, not just temporary disconnections after initialization.
- **Disconnect during work:** close the browser, stop the shore service, partition peers, and terminate one boat runtime separately. Verify that unaffected boats keep executing feasible authorized work and respecting their local protections.
- **Reconnect without reset:** reconcile task leases and observations, preserve event timestamps, reject expired or duplicate commands, and report conflicting assignments. Reconnection must not silently replay an old approval or overwrite newer local safety state.
- **Use evidence from each boat:** collect per-boat logs of task progress, observations, energy decisions, and recovery actions. Check both continuity of core functions and the capabilities lost during each outage; shore cannot report an outage-period event as received live.

**Acceptance scenario:** begin a supervised fleet patrol, remove shore connectivity, isolate one boat from its peers, and stop another boat’s runtime. The isolated boat continues only its locally feasible authorized work or takes its defined recovery action; the remaining peers coordinate available work. Restore connectivity and show reconciliation without restarting agents, concealing gaps, or executing stale commands.

The claim to prove is **continuity of onboard core functions with explicit degradation**, not uninterrupted fleet coverage or unrestricted autonomy. Implementation across `agent/`, `server/`, and `contract/` requires the respective owners’ agreement and contract review.

## What we can borrow from satellites

Satellites and patrol boats share an operational problem: limited onboard resources, intermittent contact with operators, and a need to preserve themselves without abandoning the mission silently. The following are **proposed maritime adaptations**, not claims that spacecraft software can be reused unchanged.

| Spacecraft practice | Useful adaptation for this fleet | Important boundary |
|---|---|---|
| **Resource-aware onboard scheduling** | Admit patrol, relay, and observation tasks only when energy, sensor availability, storage, and communication capacity permit; replan when those resources change. | Extend the existing allocation logic rather than introducing a competing task owner. Safety and recovery reserves are constraints, not merely auction penalties. |
| **Power prioritization and payload duty cycling** | Allocate power to essential navigation and communications first; schedule optional sensing, processing, and bulk uploads around the remaining budget. | Reduced sensing must change the reported observation freshness and coverage confidence. Never show a sleeping sensor as providing live coverage. |
| **Safe mode and staged recovery** | Enter a defined degraded mode on critical energy or subsystem faults, preserve essential functions, notify peers, and require explicit recovery checks before resuming work. | A boat cannot simply switch off propulsion: depending on traffic, current, and position, safe behaviour may require controlled return or station-keeping. SENTINEL is not automatically a safe mode. |
| **Fault detection, isolation, and recovery (FDIR)** | Compare commanded motion with measured progress and power draw; distinguish a possible propulsion fault from environmental resistance, release infeasible tasks, and report the diagnosis with uncertainty. | Start with explainable rules and bounded recovery attempts. A residual is evidence of a mismatch, not proof of a particular failure. |
| **Onboard prioritization of data** | Retain detailed observations locally, send compact contact alerts and health summaries first, and forward bulk evidence when bandwidth and energy allow. | Preserve original timestamps and provenance; label delayed delivery and never imply that shore has received data still held onboard. |

### Where to start

Prioritize **energy-aware task admission, a defined degraded-mode policy, and explainable health monitoring**. They strengthen the current fleet loop directly. More elaborate onboard scheduling and data prioritization can follow when resource limits are measured rather than guessed.

For Gazebo experiments, inject increased drag, reduced propulsion effectiveness, stale sensors, and lost communications. Compare commanded progress with observations and the energy model. Gazebo motion alone does not provide a calibrated battery model; propulsion efficiency, payload loads, and usable battery capacity still need explicit modelling and eventual hardware measurements.

### Research basis

- [NASA — Small Spacecraft Technology: Power](https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/): spacecraft power generation, storage, distribution, and fault-management functions. This supports the resource-management analogy, not our proposed boat thresholds or energy estimates.
- [ESA — Proba-1 payloads](https://www.esa.int/Applications/Observing_the_Earth/Proba-1/Payloads): autonomous onboard planning, scheduling, and payload-resource management.
- [SOHO — Spacecraft emergencies and modes](https://soho.nascom.nasa.gov/soc/esr/): an example of spacecraft safe-mode and recovery procedures; maritime safe behaviour must be designed separately.
- [ESA — Using AI for more reliable space missions](https://www.esa.int/Enabling_Support/Preparing_for_the_Future/Discovery_and_Preparation/Using_AI_for_more_reliable_space_missions): telemetry-based fault detection and protective-action research. This is an ISS demonstrator, not evidence of a deployed satellite capability or a requirement to use AI here.

## Next-stage vision: a maritime testbed in Gazebo

**The same fleet brain and operator console, tested in a richer simulated sea.**

Imagine approving a response on the existing chart, then seeing the assigned boat turn into waves, struggle to hold station, or lose sight of a contact. The important question is not whether the water looks convincing. It is whether the fleet notices the operational consequences, reallocates work, and tells the operator what it can no longer cover.

### Why Gazebo fits

Gazebo’s maritime tooling provides a starting point for buoyancy, hydrodynamic drag, thrusters, and wave interaction. The **Virtual RobotX (VRX)** project is a useful reference for a maritime simulation environment and WAM-V vehicle models—not an off-the-shelf model of our intended patrol boat.

This would let us investigate:

- **Motion and station-keeping:** how turning, acceleration, drift, and environmental disturbances change arrival times and patrol coverage.
- **Sensor limitations:** how viewpoint, occlusion, update rate, and configured noise affect contact tracking. Rendering a camera image does not itself implement a detector.
- **Failure recovery:** whether the fleet still reallocates work when a boat cannot make progress or a sensor stops updating.
- **Autopilot integration:** whether high-level patrol decisions can be executed through ArduPilot SITL rather than directly moving a simulated position.

None of this makes the result a validated digital twin. Hull dynamics, sensor performance, and energy consumption still need calibration against the selected hardware and measured data.

### Keep two simulation backends

**Do not discard the current Python simulator.** It serves a different purpose:

| Backend | Primary job |
|---|---|
| **Fast Python world** | Deterministic regression tests, seeded batch evaluation, baseline comparisons, and the lightweight offline demo. |
| **Gazebo testbed** | Selected physics-and-sensor scenarios, autopilot integration, and inspecting failures hidden by simplified motion. |

Gazebo should be an optional integration environment, not a new requirement for every contributor or the existing demo. Assets and plugins must be available locally for offline runs. Pin the tested software stack and record physics settings; do not assume cross-platform, bit-for-bit repeatability or the Python simulator’s execution speed.

### Proposed integration boundary

```text
Fleet agent → mission intent → navigation controller / optional ArduPilot SITL
                                         ↓ actuator commands
                                  Gazebo vessel + sensors
                                         ↓ own observations
                                  per-boat adapter → fleet agent
```

The fleet agent decides **which work to do**. The navigation controller decides **how to execute it**. Gazebo supplies the simulated physical environment and sensor outputs.

An adapter in `world/` would translate between that environment and the existing agent interface, using simulation time. Agents must still receive only their own sensor observations and delivered radio messages—not Gazebo ground truth. The existing radio model should remain responsible for communication loss and delay unless explicitly replaced and validated; Gazebo is not automatically a maritime radio simulator.

The shore console should remain the operational interface. A Gazebo view is a complementary engineering and demonstration view, not a replacement for the chart or a back door for evaluator truth. Any required contract or console changes need the respective owners’ review.

### Build it in stages

1. **One boat, one route:** demonstrate stable flotation, propulsion, waypoint following, simulation-clock handling, and offline startup. Begin with an existing maritime model rather than recreating the Great Belt in 3D.
2. **Connect the fleet brain:** run an existing patrol task through the adapter, with explicit coordinate-frame and unit conversions. Check that missing or stale observations are handled honestly.
3. **Add ArduPilot SITL:** exercise the autopilot boundary, including command acknowledgement, telemetry loss, and safe stopping. The ArduPilot Gazebo plugin does not itself require ROS; introduce ROS 2 only if a concrete integration needs it.
4. **Expand to the fleet:** test reassignment, radio partition/rejoin, and contact handover with independently controlled boats. Measure compute requirements before promising five-boat real-time operation on the demo laptop.
5. **Compare and calibrate:** compare task completion, coverage gaps, tracking continuity, and recovery behaviour with the lightweight model. Explain differences rather than mixing both backends into one performance headline.

**First proof:** the operator assigns a patrol; a boat executes it in Gazebo; an injected failure triggers reassignment; and the console exposes the resulting coverage gap without showing undelivered information. This is an integration acceptance scenario, not a claim of navigation safety or readiness for unsupervised deployment.

### Technical references

- [Gazebo maritime surface-vehicle tutorial](https://gazebosim.org/api/sim/8/surface_vehicles.html)
- [Virtual RobotX (VRX)](https://github.com/osrf/vrx)
- [ArduPilot SITL with Gazebo](https://ardupilot.org/dev/docs/sitl-with-gazebo.html)

## Recommendation

Finish and prove the existing loop first. Then pursue **Gazebo as the next-stage integration testbed**, starting with one boat rather than a wholesale simulator rewrite. In parallel, invest in **decision explanations, response-cost previews, and mission-level energy management**, including battery rotation and satellite-inspired degraded-mode and recovery policies. Make **independent operation across solo, peer-connected, and shore-connected modes** an explicit acceptance requirement throughout that work.

The product remains the coordination and decision layer—not the simulator. Gazebo strengthens it if it helps us demonstrate where our decisions hold up, where they fail, and what the operator needs to know.
