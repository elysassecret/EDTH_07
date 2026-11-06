"""Timing constants in sim milliseconds. Source: Challenge07BuildPlan.md. Owner: A."""
HEARTBEAT = 5_000
PEER_STALE = 20_000
LEASE = 60_000  # relay and contact; seg and pick use seg_lease_s from config/agent.toml
SLOT = 12_000
DEPUTY_GRACE = 10_000
REBALANCE = 300_000
SHORE_SILENCE = 30_000
CONTACT_STALE = 60_000
SHADOW_CAP = 1_800_000
CUE_TTL = 180_000
CYCLE_MAX = 21_600_000  # 6 h

RELEASED, CLAIMED, VETOED = 0, 1, 2

# Boat modes (energy modes from Challenge07FeaturePriorities.md section 2)
PATROL, ECO, SENTINEL, DORMANT, SHADOWING, RETURNING, UNAVAILABLE = (
    "PATROL", "ECO", "SENTINEL", "DORMANT", "SHADOWING", "RETURNING", "UNAVAILABLE")

# Radio protocol (agent/PLAN.md section 5.1)
SHORE = 0  # node ID of the shore station; boats are 1..5
RETRY = 5_000  # resend period for VETO and CMD until ACK or expiry
MAX_HOPS = 4
REBROADCAST = 30_000  # each node re-advertises its whole task table
CONTACT_DWELL = 180_000  # slow no-AIS track observed this long becomes a contact task
EXPIRY = {"HB": 12_000, "BID": 12_000, "REC": 60_000, "OBS": 60_000,
          "CONTACT": 60_000, "VETO": 30_000, "CMD": 30_000, "ACK": 30_000}
