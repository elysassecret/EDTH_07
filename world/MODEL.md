# World Model Reference (`world/`)

Owner: Simeone (B). Every number below comes directly from `config/boat.toml`, `config/radio.toml`, `config/energy.toml`, `config/scene.toml` and `config/run.toml`.

## What Is Modelled

| Aspect | Config Value | One-Sentence Explanation |
|---|---|---|
| **Cruise Speed** | `speed_mps = 2.3` (sensitivity `3.0` m/s) | Every boat propels through the water at 2.3 m/s (~4.5 kn) when patrolling, shadowing or returning home. |
| **Endurance & Reserve** | `endurance_s = 25200` (7 h), `reserve_s = 1800` (30 min), `return_safety = 1.2` | A full battery holds 7 hours of cruise-equivalent energy, and each boat automatically heads home to Korsør when remaining charge reaches 1.2× the current-adjusted return time plus a 30-minute reserve. |
| **Hotel vs. Propulsion Load** | `hotel_load_permille = 100` (10 % of cruise) | Boats drifting with motors off in `SENTINEL` mode pay 10 % of cruise power for sensors and radio, whereas any powered motion (including station-keeping corrections) pays full cruise load. |
| **Camera Radii** | `r_detect_m = {ship_day = 5000, dusk = 2000, small_day = 1500, night_unlit = 500}`, `keep_in_view_m = 2000`, `r_verify_m = 500` | A boat detects targets within its lighting/target-class camera radius (5 km for a ship by day, 2 km at dusk), holds a watched contact in view within 2 km, and credits cable sample visits or close looks within 500 m. |
| **Stand-off Ring** | `standoff_m = 1852` (1 nm), `standoff_floor_m = 500` | Boats stay outside 1 nm (1,852 m) of any contact without AIS until the watch officer approves closing to the 500 m verification floor. |
| **Radio Ranges & Channel** | `boat_m = 8000` (sensitivity `4000` m), `shore_m = 14000` m, `delay_s = [0.25, 1.0]`, `loss = 0.05`, `max_hops = 4` | Boats exchange messages up to 8 km peer-to-peer and 14 km to the Korsør mast (chosen for VHF line-of-sight from a low USV mast vs. a high shore antenna) with 5 % packet loss, 0.25–1.0 s delay per hop and up to 4 hops. |
| **Current & Tide Flip** | `current_mps = 0.5`, `current_dir_deg = 345`, `tide_flip_s = 9000`, `sentinel_radius_m = 300` | A uniform 0.5 m/s current flows toward 345° and reverses once at 9,000 s (2.5 h), pushing drifting `SENTINEL` boats until they exceed 300 m from station and drive back under power. |
| **Great Belt Scene & Samples** | `segment_max_m = 5000`, `sample_step_m = 100`, `lane_half_m = 750`, `revisit_target_s = 12000` | The three Great Belt cables split into 7 segments (23.60 km total, 241 samples spaced every 100 m) with a 12,000 s (3 h 20 m) revisit target and a 750 m half-width shipping-lane keep-out band for stations. |
| **AIS Reception Radii** | `ais_class_a_m = 20000` (20 km), `ais_class_b_m = 8000` (8 km) | Class A and Class B AIS reception ranges are configured at 20 km and 8 km (evaluator-only in the core baseline; boat-side replay is gated under #52). |
| **Shore launch** | `launch_gap_s = 60` | With `World(launch=True)` (the console default) every boat starts docked at Korsør with no task and is switched on 60 s after the previous one, in a seeded order; the agents decide who goes where. |
| **Battery swap** | `swap_s = 600`, `dock_m = 50` | A boat docked at Korsør (within 50 m, agent mode `UNAVAILABLE`) gets a full battery after 10 min; logged as `swap_start` and `battery_swap`. A team assumption, not a measured time. |

## What Is NOT Modelled

- **Waves, wind and sea state:** Motion integrates velocity through water plus the uniform current vector in integer millimetres; hull slamming, wave-induced camera stabilization loss and windage are not simulated.
- **Dynamic COLREGs / ship-to-boat collision avoidance:** Boats steer around the 1 nm stand-off ring of dark contacts and keep stations outside the 750 m shipping-lane band, but do not perform dynamic manoeuvring around passing merchant traffic.
- **Land in the physics:** the world does not stop a boat at the coast and has no bathymetry in routing. Land avoidance is the agent's job: boats route around the real coastline with a 50 m margin (agent/RULES.md 12f, `agent/water.py`); `tests/agent/test_water.py` checks no boat is on land in 4-hour runs.
- **Calibrated hull power curves:** Battery drain uses a two-state linear model (100 % cruise load when moving, 10 % hotel load when drifting with motors off) rather than a speed-cubed propeller curve.
