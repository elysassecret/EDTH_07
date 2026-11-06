"""Protocol constants. Integers, milliseconds unless stated."""

HEARTBEAT = 5_000
PEER_STALE = 20_000
LEASE = 60_000
SLOT = 12_000
DEPUTY_GRACE = 10_000
REBALANCE = 300_000
SHORE_SILENCE = 30_000
CONTACT_STALE = 60_000
SHADOW_CAP = 1_800_000
CUE_TTL = 180_000
ACTIVE_SILENCE = 600_000      # a boat silent this long leaves n_active

# Record states. VETOED doubles as "closed" for contact and cue tasks.
RELEASED, CLAIMED, VETOED = 0, 1, 2
CLOSED = VETOED

# Message expiry per kind
EXPIRY_MS = {"HB": 12_000, "BID": 12_000, "REC": 60_000, "OBS": 60_000,
             "CONTACT": 60_000, "VETO": 30_000, "CMD": 60_000, "ACK": 12_000}

# Boat modes
PATROL, RELAY, SHADOWING, HOLDING, RETURNING, UNAVAILABLE, CUE = (
    "PATROL", "RELAY", "SHADOWING", "HOLDING", "RETURNING", "UNAVAILABLE", "CUE")

SHORE_ID = 0
KN_TO_MPS = 0.514444
