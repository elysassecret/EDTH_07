"""Snapshot the dashboard reads, 5-10 Hz over WebSocket, and commands it sends back.
Owner: A + C sign-off (Fri 20:30). Exported to contract/schema.json by
`uv run python -m contract.export`; web/ generates TypeScript from that file.

The same shape goes on /shore (only what the shore has received) and /truth (evaluator view);
`view` says which. Times in the snapshot are sim seconds; positions are int metres plus
lon/lat for the map.

Example:
{"schema_version": 1, "view": "shore", "t": 0, "speed": 240,
 "boats": [{"id": 1, "x": 0, "y": 0, "lon": 11.0, "lat": 55.4, "mode": "PATROL", "batt": 1000,
            "endurance_s": 25200, "must_return_by": 14140, "link": "direct",
            "tour": ["seg:G:0"], "roles": ["seg:G:0"], "last_heard": 0}],
 "tasks": {"seg:G:0": {"v": 1, "owner": 1, "deputy": 0, "state": 1}},
 "seg_age": {}, "links": [], "contacts": [], "decisions": [], "alerts": [], "events": []}

Commands from the dashboard:
{"cmd": "confirm"|"stop"|"approve"|"decline", "id": "..."}
{"cmd": "inject", "kind": "battery_low"|"link_off"|"link_on"|"boat_off", "a": 4, "b": "shore"}
{"cmd": "ack", "id": "<alert id>"}

Fields added for the console (issue #7) are optional with defaults, so older producers still
validate.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


class Boat(BaseModel):
    id: int
    x: int
    y: int
    lon: float
    lat: float
    mode: str
    batt: int  # permille
    endurance_s: int  # remaining at cruise
    must_return_by: int | None = None  # sim s
    link: Literal["direct", "peer", "none"]
    tour: list[str]
    roles: list[str]
    last_heard: int  # sim s of the newest data from this boat
    hdg: int = 0  # degrees true, for the heading line on the chart
    sog: int = 0  # mm/s, same unit as Contact.sog
    via: int | None = None  # next hop toward shore (0 = shore), for the comms overlay


class TaskView(BaseModel):
    v: int
    owner: int
    deputy: int
    state: int  # 0 released, 1 claimed, 2 vetoed
    why: str = ""  # the claiming boat's own reason, as delivered (#86); "" if none received


class Link(BaseModel):
    a: int  # 0 = shore
    b: int
    state: Literal["up", "down", "cut"]  # cut = injected link_off


class ContactFlags(BaseModel):
    dwell: bool = False
    name: bool = False  # a look within 500 m happened
    anchor: bool = False
    cannot_hold: bool = False
    capped: bool = False


class Contact(BaseModel):
    id: str  # contact task ID, e.g. "contact:C-07"
    track: str
    x: int
    y: int
    lon: float
    lat: float
    sog: int  # mm/s
    cog: int
    ais: bool
    first_seen: int  # sim s
    last_seen: int
    seen_by: list[int]
    watcher: int  # 0 = none
    state: int
    flags: ContactFlags
    course: int | None = None  # last course logged when it could not be held
    source: Literal["ais", "camera", "fused"] = "ais"  # "camera" = NO AIS
    name: str | None = None  # AIS name if any
    trail: list[tuple[float, float]] = []  # recent [lon, lat] positions, oldest first
    why: str = ""  # why it is watched, released or stopped, from delivered reports (#86)


class Decision(BaseModel):
    id: str
    task: str
    dec: str  # "close"
    text: str
    state: Literal["pending", "approved", "declined", "delivered", "expired", "confirmed",
                   "stopped"]
    t: int
    tier: Literal["delegated", "held"] = "held"  # delegated = Confirm/Stop, held = Approve/Decline
    actions: list[Literal["confirm", "stop", "approve", "decline"]] = []
    boat: int = 0  # the boat that would act
    route: list[tuple[float, float]] | None = None  # [lon, lat] ghost-route preview
    why: str = ""  # which standing order applies (#86)


class Alert(BaseModel):
    id: str
    level: Literal["alarm", "warning", "caution"]
    text: str
    t: int
    ack: bool = False


class Event(BaseModel):
    t: int
    kind: str
    text: str
    exercise: bool = False  # injected or scripted failure: drives the EXERCISE banner


class Snapshot(BaseModel):
    schema_version: int = SCHEMA_VERSION
    t0_utc: str = "2026-11-03T10:15:00Z"  # wall-clock label for t = 0 (scenarios ais_t0)
    view: Literal["shore", "truth"]
    t: int  # sim s
    speed: int  # time-warp factor
    boats: list[Boat]
    tasks: dict[str, TaskView]
    seg_age: dict[str, int]  # sim s since last sensor visit
    links: list[Link]
    contacts: list[Contact]
    decisions: list[Decision]
    alerts: list[Alert]
    events: list[Event]


class Decide(BaseModel):
    cmd: Literal["confirm", "stop", "approve", "decline"]
    id: str


class Inject(BaseModel):
    cmd: Literal["inject"]
    kind: Literal["battery_low", "link_off", "link_on", "boat_off"]
    a: int
    b: int | Literal["shore"] | None = None


class AckAlert(BaseModel):
    cmd: Literal["ack"]
    id: str  # Alert.id


Command = Annotated[Decide | Inject | AckAlert, Field(discriminator="cmd")]


class Contract(BaseModel):
    """Root of the exported schema, so one file carries every type."""
    snapshot: Snapshot
    command: Command
