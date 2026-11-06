"""Snapshot the dashboard reads, 5-10 Hz over WebSocket. Owner: A + C sign-off (Fri 20:30).

Example (fill in exact fields at the 20:30 review, then freeze):
{"t": 0, "speed": 240,
 "boats": [{"id": 1, "x": 0, "y": 0, "mode": "PATROL", "batt": 1000,
            "endurance_s": 25200, "must_return_by": 14140, "link": "direct",
            "tour": ["seg:G:0"], "last_heard": 0}],
 "tasks": {"seg:G:0": {"v": 1, "owner": 1, "deputy": 0, "state": 1}},
 "seg_age": {}, "links": [], "contacts": [], "decisions": [], "alerts": [], "events": []}

Commands from the dashboard:
{"cmd": "confirm"|"stop"|"approve"|"decline", "id": "..."}
{"cmd": "inject", "kind": "battery_low"|"link_off"|"boat_off", "a": 4, "b": "shore"}
"""
SCHEMA_VERSION = 0
