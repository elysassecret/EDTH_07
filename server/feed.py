"""WebSocket feed shared by the mock and the real bridge. Owner: C.

A *source* is anything with this shape (MockWorld in mock_feed.py, SimSource in bridge.py):

    source.t                      sim seconds now
    source.step(dt_ms)            advance the sim by dt_ms of sim time
    source.speed()                auto-warp factor for the current sim time
    source.near_event()           True while auto-warp is slowed for an event
    source.scene_msg()            static geometry, sent once per connection
    source.snapshot(channel, speed) -> dict   channel "shore" or "truth"
    source.command(msg) -> {"ok": bool, "error"?: str}

Feed steps the source at a fixed real rate (hz) times the warp, sends /shore and /truth
frames, and answers every command with an "ack". Feed-level commands: reset, pause, speed.
With serve_web it also serves web/dist over plain HTTP on the same port (one command demo, N3).
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import zlib
from bisect import bisect_right
from collections.abc import Callable
from pathlib import Path
from typing import Any

from server.evaluator import compare
from server.narrator import Narrator

ROOT = Path(__file__).resolve().parents[1]


def sensor_ranges() -> dict:
    """#88 rings: the boat model's ranges from config/boat.toml (B's file), read, never hard-coded.
    Detection depends on target and light; the console draws the ship-by-day camera range."""
    import tomllib

    boat = tomllib.loads((ROOT / "config" / "boat.toml").read_text(encoding="utf-8"))
    return {
        "detect_ship_day_m": int(boat["r_detect_m"]["ship_day"]),
        "keep_in_view_m": int(boat["keep_in_view_m"]),
        "standoff_m": int(boat["standoff_m"]),
    }


def boat_model() -> dict:
    """Model numbers the console needs for estimates (config/boat.toml, B's file), read, never
    hard-coded: cruise speed for "could be within" circles and transit estimates, endurance and
    reserve for the response-cost preview. Model values, not measured on a hull."""
    import tomllib

    boat = tomllib.loads((ROOT / "config" / "boat.toml").read_text(encoding="utf-8"))
    return {"speed_mps": float(boat["speed_mps"]), "endurance_s": int(boat["endurance_s"]),
            "reserve_s": int(boat["reserve_s"])}
WEB_DIST = ROOT / "web" / "dist"
RECORD_EVERY_S = 10  # the replay timeline keeps the shore picture every 10 sim-seconds
MARKS_MAX = 400  # newest timeline marks (events) kept for the replay line
FRAMES_MAX = 400  # most frames one /api/frames answer carries
SPEED_MIN, SPEED_MAX = 0.25, 999.0  # stepless warp range (live run and replay playback)


class History:
    """The officer's picture (/shore) as it was, for the replay timeline: one frame every
    RECORD_EVERY_S sim-seconds since the run started, zlib-compressed JSON (about 10 KB each,
    so a 12 h run is a few tens of MB). Replay only looks at it: the simulation keeps running."""

    def __init__(self) -> None:
        self.times: list[int] = []
        self.frames: list[bytes] = []
        self.marks: list[dict] = []  # events seen on the shore picture, for the timeline
        self._seen: set[tuple[int, str]] = set()

    def add(self, snap: dict) -> None:
        for e in snap.get("events", []):
            key = (int(e["t"]), str(e["text"]))
            if key not in self._seen:
                self._seen.add(key)
                self.marks.append({"t": key[0], "text": key[1], "kind": e.get("kind", ""),
                                   "exercise": bool(e.get("exercise"))})
        if len(self.marks) > MARKS_MAX:
            del self.marks[: len(self.marks) - MARKS_MAX]
        t = int(snap["t"])
        if self.times and t < self.times[-1] + RECORD_EVERY_S:
            return
        self.times.append(t)
        self.frames.append(zlib.compress(json.dumps(snap).encode(), 3))

    def span(self) -> dict:
        return {"from": self.times[0] if self.times else None,
                "to": self.times[-1] if self.times else None, "every_s": RECORD_EVERY_S,
                "frames": len(self.times), "marks": sorted(self.marks, key=lambda m: m["t"])}

    def between(self, t_from: float, t_to: float) -> bytes:
        """The recorded frames from t_from to t_to (at most FRAMES_MAX), as one JSON array, for
        playing the recording back: the frame at or before t_from first, so playback starts on
        what was on screen."""
        i = max(bisect_right(self.times, t_from) - 1, 0)
        j = min(bisect_right(self.times, t_to), i + FRAMES_MAX)
        return b"[" + b",".join(zlib.decompress(f) for f in self.frames[i:j]) + b"]"

    def at(self, t: float) -> bytes | None:
        """The frame recorded at or just before sim time t (the first one if t is earlier)."""
        if not self.times:
            return None
        i = max(bisect_right(self.times, t) - 1, 0)
        return zlib.decompress(self.frames[i])
log = logging.getLogger("feed")


class Feed:
    """Owns one source, steps it at a fixed real rate and broadcasts to clients."""

    def __init__(self, factory: Callable[[int], Any], seed: int, hz: float = 10.0,
                 start_paused: bool = False):
        self.factory = factory
        self.seed = seed
        self.hz = hz
        self.world = factory(seed)
        self.narrator = self._new_narrator()
        self.history = History()
        self.history.add(self.world.snapshot("shore", 0))  # the first state: replay starts here
        self.clients: dict = {}  # connection -> channel
        self.start_paused = start_paused  # demo: every (re)start waits for "Run"
        self.paused = start_paused
        self.speed_override: float | None = None

    def handle_command(self, msg: dict) -> dict:
        log.info("command t=%.1f %s", self.world.t, json.dumps(msg, sort_keys=True))
        cmd = msg.get("cmd")
        try:
            if cmd == "reset":
                self.seed = int(msg.get("seed", self.seed))
                getattr(self.world, "close", lambda: None)()  # e.g. finish the run log
                self.world = self.factory(self.seed)
                self.narrator = self._new_narrator()
                self.history = History()  # a new run: its replay starts again
                self.history.add(self.world.snapshot("shore", 0))
                self.paused = self.paused or self.start_paused
                return {"ok": True}
            if cmd == "pause":
                self.paused = bool(msg.get("on", not self.paused))
                return {"ok": True}
            if cmd == "speed":
                v = msg.get("value")
                if v in (None, "auto"):
                    self.speed_override = None
                else:
                    f = float(v)
                    if not SPEED_MIN <= f <= SPEED_MAX:  # also refuses NaN
                        return {"ok": False, "error": f"speed must be {SPEED_MIN:g}–{SPEED_MAX:g}x"}
                    self.speed_override = f
                return {"ok": True}
        except (TypeError, ValueError) as e:
            return {"ok": False, "error": f"bad command: {e}"}
        return self.world.command(msg)

    async def handler(self, ws) -> None:
        path = ws.request.path.split("?")[0].rstrip("/") or "/shore"
        if path not in ("/shore", "/truth"):
            await ws.close(code=1008, reason="use /shore or /truth")
            return
        channel = path[1:]
        self.clients[ws] = channel
        log.info("client connected on /%s (%d total)", channel, len(self.clients))
        try:
            await ws.send(json.dumps(self.world.scene_msg()))
            await ws.send(self._frame(channel, self._speed()))
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                    if not isinstance(msg, dict):
                        raise TypeError("command must be a JSON object")
                    res = self.handle_command(msg)
                except (ValueError, TypeError) as e:
                    msg, res = {}, {"ok": False, "error": f"bad JSON: {e}"}
                if not res["ok"]:
                    log.warning("rejected %s: %s", msg, res["error"])
                await ws.send(json.dumps({"type": "ack", "cmd": msg.get("cmd"),
                                          "id": msg.get("id"), **res}))
        finally:
            self.clients.pop(ws, None)
            log.info("client left /%s (%d total)", channel, len(self.clients))

    def _speed(self) -> float:
        return 0 if self.paused else (self.speed_override or self.world.speed())

    def _snap(self, channel: str, speed: float) -> dict:
        # the contract's speed is a whole number (0 = paused); the exact warp rides as "warp"
        out = self.world.snapshot(channel, 0 if speed == 0 else max(1, round(speed)))
        out["warp"] = speed
        # console extras (feature 25): who sets the warp, and whether auto-warp is slowed
        out["warp_mode"] = ("paused" if self.paused else
                            "manual" if self.speed_override else "auto")
        out["near_event"] = out["warp_mode"] == "auto" and bool(self.world.near_event())
        # the warp the officer chose, kept while paused so the speed menu does not snap to Auto
        out["warp_set"] = self.speed_override or "auto"
        return out

    def _new_narrator(self) -> Narrator:
        scene = self.world.scene_msg()
        return Narrator(int(scene.get("stale_after_s", 60)))

    def _frames(self, speed: float) -> dict[str, dict]:
        """Both channels. Only /truth carries "eval" (shore belief next to truth): the
        operator's /shore picture never does. /shore carries "narration", made from /shore
        frames alone (server/narrator.py)."""
        shore = self._snap("shore", speed)
        self.narrator.update(shore)
        shore["narration"] = self.narrator.lines[-12:]
        self.history.add(shore)
        truth = self._snap("truth", speed)
        truth["eval"] = compare(shore, truth)
        # hook for D's three-mode scorecard: a source may offer scorecard() -> dict (eval/)
        if hasattr(self.world, "scorecard") and (card := self.world.scorecard()) is not None:
            truth["scorecard"] = card
        return {"shore": shore, "truth": truth}

    def _frame(self, channel: str, speed: float) -> str:
        return json.dumps(self._frames(speed)[channel])

    def tick(self) -> dict[str, str]:
        """One frame: advance the source and render both channels (no I/O, testable)."""
        speed = self._speed()
        self.world.step(round(speed * 1000 / self.hz))
        return {ch: json.dumps(snap) for ch, snap in self._frames(speed).items()}

    async def run(self) -> None:
        period = 1.0 / self.hz
        loop = asyncio.get_running_loop()
        while True:
            started = loop.time()
            frames = self.tick()
            for ws, ch in list(self.clients.items()):
                try:
                    await ws.send(frames[ch])
                except Exception:  # noqa: BLE001 - a dead client must not stop the feed
                    self.clients.pop(ws, None)
            await asyncio.sleep(max(0.0, period - (loop.time() - started)))


def _static(connection, request):
    """Serve web/dist for plain HTTP requests; let WebSocket upgrades through."""
    from websockets.datastructures import Headers
    from websockets.http11 import Response

    if request.headers.get("Upgrade", "").lower() == "websocket":
        return None
    rel = request.path.split("?")[0].lstrip("/") or "index.html"
    path = (WEB_DIST / rel).resolve()
    if not path.is_relative_to(WEB_DIST.resolve()) or not path.is_file():
        path = WEB_DIST / "index.html"
    if not path.is_file():
        return connection.respond(404, "web/dist not built: run pnpm --dir web build\n")
    body = path.read_bytes()
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return Response(200, "OK", Headers([("Content-Type", ctype),
                                        ("Content-Length", str(len(body)))]), body)


async def _api(feed: Feed, connection, request):
    """GET /api/report.md?from=S&to=S (incident report) and /api/tamper-demo (JSON).
    Real sim with a run log only. The work runs in a thread so frames keep flowing."""
    from urllib.parse import parse_qs, urlsplit

    from websockets.datastructures import Headers
    from websockets.http11 import Response

    from evidence.report import report, tamper_demo

    url = urlsplit(request.path)
    if url.path in ("/api/history", "/api/frame", "/api/frames"):  # replay: real sim and mock
        if url.path == "/api/history":
            body = json.dumps(feed.history.span()).encode()
        elif url.path == "/api/frames":
            q = parse_qs(url.query)
            try:
                body = feed.history.between(float(q["from"][0]), float(q["to"][0]))
            except (KeyError, ValueError):
                return connection.respond(400, "need ?from=<sim s>&to=<sim s>\n")
        else:
            q = parse_qs(url.query)
            try:
                frame = feed.history.at(float(q["t"][0]))
            except (KeyError, ValueError):
                return connection.respond(400, "need ?t=<sim seconds>\n")
            if frame is None:
                return connection.respond(404, "nothing recorded yet\n")
            body = frame
        return Response(200, "OK", Headers([("Content-Type", "application/json"),
                                            ("Access-Control-Allow-Origin", "*"),
                                            ("Content-Length", str(len(body)))]), body)
    log_ = getattr(feed.world, "log", None)
    if log_ is None:
        return connection.respond(404, "No run log: real sim only, without --no-log\n")
    log_.flush()
    try:
        if url.path == "/api/report.md":
            q = parse_qs(url.query)
            t_from = int(q["from"][0]) if "from" in q else None
            t_to = int(q["to"][0]) if "to" in q else None
            body = (await asyncio.to_thread(report, log_.path, t_from=t_from, t_to=t_to)).encode()
            name = log_.path.stem + ".report.md"
            headers = [("Content-Type", "text/markdown; charset=utf-8"),
                       ("Content-Disposition", f'attachment; filename="{name}"')]
        elif url.path == "/api/tamper-demo":
            body = json.dumps(await asyncio.to_thread(tamper_demo, log_.path)).encode()
            headers = [("Content-Type", "application/json")]
        else:
            return connection.respond(404, "Unknown API path\n")
    except (ValueError, OSError) as e:
        log.warning("api %s failed: %s", url.path, e)
        return connection.respond(500, f"Could not build it: {e}\n")
    return Response(200, "OK", Headers([*headers, ("Content-Length", str(len(body)))]), body)


async def serve(factory: Callable[[int], Any], host: str, port: int, seed: int, hz: float = 10.0,
                ready=None, serve_web: bool = False, name: str = "feed",
                start_paused: bool = False) -> None:
    from websockets.asyncio.server import serve as ws_serve

    feed = Feed(factory, seed, hz, start_paused)

    async def process_request(connection, request):
        if request.path.startswith("/api/"):
            return await _api(feed, connection, request)
        return _static(connection, request) if serve_web else None

    extra = {"process_request": process_request}
    async with ws_serve(feed.handler, host, port, **extra) as server:
        bound = server.sockets[0].getsockname()[1]
        log.info("%s on ws://%s:%d/shore and /truth, seed %d", name, host, bound, seed)
        if serve_web:
            log.info("console on http://%s:%d/", host, bound)
        if ready is not None:
            ready.set_result((feed, bound))
        await feed.run()
