"""Issue #107 (Gazebo Stage-1 adapter) and Issue #105 (independent per-boat runtimes)."""

from pathlib import Path

from agent.core import Agent
from agent.shore import ShoreNode
from contract.mission import Detection
from world.gazebo import GazeboBoatAdapter, GazeboSurfaceVessel, run_stage1_patrol
from world.runtime_bus import DetachedWorldHarness

ROOT = Path(__file__).resolve().parents[2]


def test_gazebo_doc_lists_pinned_versions_and_offline_start():
    doc = (ROOT / "world" / "GAZEBO.md").read_text(encoding="utf-8")
    assert "Harmonic 8.6.0" in doc
    assert "VRX 2.3.0" in doc
    assert "uv run python -m world.gazebo" in doc
    assert "gz sim -s -r" in doc


def test_gazebo_stage1_adapter_follows_two_waypoint_patrol_and_isolates_truth():
    report = run_stage1_patrol(wp_a=(0, 0), wp_b=(450, 0), ticks=420, tick_ms=1000)
    assert report["backend"] == "gazebo_stage1_adapter"
    assert report["tour"] == ["seg:H:0"]
    assert report["flotation_stable"] is True
    assert report["max_abs_heave_m"] <= 0.15
    assert report["max_abs_pitch_deg"] <= 5.0
    # Both waypoints (0, 0) and (450, 0) are reached and the follower index transitions.
    assert [0, 0] in report["visited_waypoints"]
    assert [450, 0] in report["visited_waypoints"]
    assert len(report["follower_index_transitions"]) >= 2
    assert len(report["trace"]) >= 8

    # Verify strict truth isolation: far contacts outside r_detect_m are never passed to the agent.
    adapter = GazeboBoatAdapter(1, endurance_ms=25_200_000, r_detect_m=2000)
    vessel = GazeboSurfaceVessel((0, 0))
    own = adapter.own_from_telemetry(vessel.telemetry())
    near = Detection("near", 500, 0, 1000, 90, False)
    far = Detection("far", 4500, 0, 1000, 90, False)
    seen = adapter.filter_detections(own, (near, far))
    assert seen == (near,)


def test_detached_world_harness_proves_independent_operation_without_shore_or_peers():
    harness = DetachedWorldHarness(ROOT, seed=1, agent_factory=Agent, shore_factory=ShoreNode)
    # 1. Start supervised patrol for 30 s.
    for _ in range(30):
        harness.step()
    assert harness.shore_endpoint is not None and harness.shore_endpoint.running

    # 2. Stop the shore service, isolate Boat 2 from peers, and stop Boat 1's runtime.
    harness.stop_shore()
    harness.isolate_boat(2)
    harness.stop_boat_runtime(1)

    b2_node_id = id(harness.boat_endpoints[2].node)
    b4_node_id = id(harness.boat_endpoints[4].node)

    # Run through lease expiry so connected peers can share out Boat 1's work while
    # isolated Boat 2 keeps doing only its locally authorized work without claiming new tasks.
    for _ in range(120):
        harness.step()

    b2_held = harness.boat_endpoints[2].node.table.held_by(2)
    assert "seg:H:0" in b2_held
    assert "seg:G:0" not in b2_held  # isolated boat never takes over Boat 1's expired tasks without quorum

    # 3. Restore shore and connectivity without restarting agent instances.
    harness.restore_all()
    for _ in range(20):
        harness.step()

    assert id(harness.boat_endpoints[2].node) == b2_node_id
    assert id(harness.boat_endpoints[4].node) == b4_node_id
    assert harness.shore_endpoint.running is True
