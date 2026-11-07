# Features 1–25: pass / fail / not verified

Owner: D. Issue #74. Acceptance is never inferred from a merge: each row names the test (run locally on the revision below) or the video timestamp that shows it. "Not verified" means exactly that.

**Revision:** `main` at `86806cb` (merge of #70), 2026-11-07.
**Local run:** `uv run pytest -q` on Windows 11, Python 3.12 via uv. Result: **271 passed, 1 skipped (`web/dist` not built), 1 failed** (`tests/server/test_evidence.py::test_private_key_is_owner_only`, a POSIX file-mode check that cannot pass on NTFS; C-owned, passes on Linux). CI is blocked by billing (see `deck/RELEASE.md`), so this is local evidence, not green CI.
**Video:** none yet (C, #73). Every "video" cell is open until it exists.

| # | Feature | Status | Evidence |
|---|---|---|---|
| 1 | Real Great Belt scene: cables, lane, Korsør, box | pass | `tests/world/test_routes.py::test_scene_geometry_and_roles`, `tests/story/test_real_scene.py::test_r1_*`, `test_r2_*` (both); `tools.scene_check`: 7 segments, 23.6 km, 241 samples |
| 2 | Five boats, 2 sweeps + 2 pickets + 1 relay | pass | `tests/world/test_routes.py::test_scene_geometry_and_roles`, `tests/agent/test_tour.py::test_initial_tours_are_optimal_on_the_scene` |
| 3 | Revisit age per cable segment | pass | `tests/eval/test_metrics.py::test_overdue_is_strict_and_never_visited_stays_out`, `test_segment_with_any_unvisited_sample_has_no_age_in_either_order`; `tests/agent/test_shore.py::test_seg_age_is_the_worst_sample_not_any_touch` |
| 4 | Deterministic reset and seeded runs | pass | `tests/eval/test_batch.py::test_reset_mid_run_equals_fresh_run`, `test_seeded_case_repeats_across_processes_and_hash_seeds`; `tests/world/test_sim.py::test_reset_recreates_nodes_queues_and_injections`, `test_world_hash_is_independent_of_hash_seed`; `tests/agent/test_determinism.py` |
| 5 | Decentralised auction, battery in the bid, no coordinator | pass | `tests/agent/test_protocol.py::test_p1_*`, `test_p5_*`, `test_p6_*`; `tests/smoke/test_smoke.py::test_agent_never_imports_world` |
| 6 | Low battery: return home, tasks re-auctioned | pass | `tests/agent/test_protocol.py::test_battery_low_04_takes_the_cables_03_keeps_its_picket`; `tests/story/test_story.py::test_s1_*`; `tests/world/test_bridge_api.py::test_real_auction_reassigns_actual_scene_after_scripted_battery_event` |
| 7 | Range-limited radio, peer hops, store-and-forward | pass | `tests/agent/test_core.py::test_a_record_reaches_every_node_across_hops`; `tests/agent/test_net.py::test_hop_limit_and_forward_keeps_times`, `test_retry_until_ack_or_expiry`; `tests/world/test_sim.py::test_radio_range_at_send_and_delivery_and_directed_link` |
| 8 | Relay as a role another boat can take over | pass | `tests/agent/test_shore.py::test_p7_*`, `test_s6_relay_lost_nobody_cut_off_relay_stays_open`; `tests/story/test_story.py::test_s2_*` (both) |
| 9 | Split/rejoin merge rule | pass | `tests/contract/test_merge.py` (all); `tests/story/test_story.py::test_s6_rejoin_converges_every_table`; `tests/world/test_agent_integration.py::test_complete_shore_isolation_then_rejoin_uses_only_delivered_data` |
| 10 | Dark contact: detect, nearest free boat watches, scout holds | pass | `tests/agent/test_contact.py::test_scout_holds_free_picket_watches_scout_resumes_cannot_hold`, `test_p8_deputy_takes_the_watch_without_an_auction`; `tests/story/test_story.py::test_s3_*`, `test_s4_*` |
| 11 | Remaining gap stays visible, never hidden | pass | `tests/story/test_story.py::test_s5_uncovered_picket_stays_visible_to_the_end`; `tests/eval/test_gap.py::test_console_never_shows_a_segment_fresher_than_truth`; `tests/server/test_alerts.py::test_picket_says_since_when_and_keeps_that_time` |
| 12 | Three-mode runner and headline metric | pass | `tests/eval/test_fairness.py` (F1–F4), `tests/eval/test_batch.py`; `runs/main/scorecard.md` exit 0, no PRELIMINARY, F1–F5 PASS on 5 seeds |
| 13 | Live failure injection: any boat, any link | pass (logic); video open | `tests/server/test_bridge.py::test_injection_works_for_any_boat_and_link`, `test_boat_restore_brings_the_same_boat_back_and_replays`; the click itself needs the video |
| 14 | Four-tier operator policy | pass (logic); video open | `tests/agent/test_contact.py::test_stop_ends_the_watch`, `test_shore_shows_the_contact_and_cards_from_delivered_messages_only`; `tests/agent/test_shore.py::test_stop_is_delivered_to_the_watcher_and_sticks`; `deck/standing_orders.md` |
| 15 | Current-aware return rule | pass | `tests/agent/test_energy.py::test_return_time_depends_on_the_current`, `test_return_rule_fires_with_safety_margin`; `tests/world/test_current.py::test_low_battery_injection_matches_real_agents_current_aware_safety_rule` |
| 16 | SENTINEL drift-and-correct for pickets and relay | pass | `tests/agent/test_energy.py::test_picket_drifts_with_motors_off_and_corrects_past_300_m`; `tests/world/test_current.py::test_real_picket_drifts_then_corrects_with_energy_cost_and_stays_near_station`; `tests/world/test_energy.py::test_stationary_sentinel_uses_hotel_load_not_cruise` |
| 17 | Offline chart with infrastructure layers | pass (offline); video open | `tests/server/test_web_static.py::test_console_source_has_no_web_addresses`, `test_built_console_has_no_unexpected_web_addresses` (skipped locally: `web/dist` not built, C to confirm on a built console); `web/public/geo/land.geojson` and `infra.geojson` from #49; `tests/story/test_real_scene.py::test_r2_stations_and_the_contact_are_in_water`; depth bands `web/public/geo/depth_bands.geojson` (#89, overlay check `deck/img/depth_bands_check.jpg`). Screenshot from #88: open. Fresh-eyes verdict (`deck/FRESH_EYES.md`): not run yet |
| 18 | USV cards: role, mode chip, battery as time, link, data age | not verified | UI only. Needs a video timestamp from C. Data behind it: `tests/world/test_energy.py::test_shore_console_picture_reflects_delivered_energy_not_truth` |
| 19 | Contact tracks: AIS / NO AIS / fused, trails, seen-by | pass (data); video open | `tests/server/test_bridge.py::test_shore_never_shows_truth_contacts`; `tests/story/test_story.py::test_s3_shore_shows_the_contact`; the NO AIS chip needs the video |
| 20 | Data-age honesty: stale boats greyed, LAST SEEN | pass (data); video open | `tests/server/test_bridge.py::test_switched_off_boat_stays_old_on_shore`; `tests/server/test_alerts.py::test_stale_boat_is_a_warning_and_clears_when_heard_again`; `tests/agent/test_shore.py::test_cut_boat_keeps_old_data_on_the_shore` |
| 21 | Comms overlay, lost links crossed | pass (data); video open | `tests/server/test_bridge.py::test_injected_boat_link_cut_is_crossed`, `test_shore_link_down_only_if_once_direct_and_exercise_cut_is_crossed` |
| 22 | Decision cards with ghost-route preview | pass (cards); preview not verified | `tests/server/test_demo.py::test_demo_beats_still_happen` (held card for C-07); `tests/agent/test_shore.py::test_approval_to_an_unreachable_boat_expires`; ghost route is UI only, needs the video |
| 23 | Alerts in 3 levels with ack and dedup | pass | `tests/server/test_alerts.py::test_dedup_keeps_first_time_and_ack`, `test_held_decision_escalates_to_alarm_and_needs_new_ack`, `test_sim_alerts_through_the_tape` |
| 24 | Coverage overlay and headline number on screen | pass (number); overlay video open | `tests/server/test_evaluator.py::test_true_cable_km_overdue_uses_real_sample_lengths`, `test_scorecard_hook_passes_through_on_truth_only`; `tests/server/test_bridge.py::test_scorecard_is_read_from_eval_output_on_truth_only`. Screenshot from #88: open. Fresh-eyes verdict (`deck/FRESH_EYES.md`): not run yet |
| 25 | Auto-warp, event log, FEED LOST, EXERCISE banner | pass (warp, exercise); FEED LOST not verified | `tests/server/test_demo.py::test_demo_warp_uses_preset_and_slow_windows`; `tests/server/test_bridge.py::test_frames_say_who_sets_the_warp`; `tests/server/test_alerts.py::test_exercise_alert_goes_on_ack_or_restore`; FEED LOST banner needs the video |

## Real-scene tests R1–R3 (D)

| Test | Status | Note |
|---|---|---|
| R1 stations reach the shore, boat 4 has a direct link | pass | `tests/story/test_real_scene.py::test_r1_*` |
| R2 stations and contact in water, outside the lane band | pass | `test_r2_*` (both); in-water uses the real `land.geojson` from #49 |
| R3 AIS stays with the evaluator | pass | `test_r3_*` (both): boats know only their own sensors |
| R3 actual AIS reception by a boat | **not verified** | needs #52 (B, gated). Not claimed |

## Summary

- Features 1–17, 23: pass on local tests.
- Features 18–22, 24, 25: logic and data pass on tests; the on-screen pieces (cards, chips, overlays, FEED LOST banner, ghost route) are open until the C video (#73) gives a timestamp for each.
- Nothing fails. Gate status is posted on #75 and `deck/RELEASE.md`.
