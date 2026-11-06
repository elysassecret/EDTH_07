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
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WEB_DIST = ROOT / "web" / "dist"
log = logging.getLogger("feed")


class Feed:
    """Owns one source, steps it at a fixed real rate and broadcasts to clients."""

    def __init__(self, factory: Callable[[int], Any], seed: int, hz: float = 10.0):
        self.factory = factory
        self.seed = seed
        self.hz = hz
        self.world = factory(seed)
        self.clients: dict = {}  # connection -> channel
        self.paused = False
        self.speed_override: int | None = None

    def handle_command(self, msg: dict) -> dict:
        log.info("command t=%.1f %s", self.world.t, json.dumps(msg, sort_keys=True))
        cmd = msg.get("cmd")
        try:
            if cmd == "reset":
                self.seed = int(msg.get("seed", self.seed))
                getattr(self.world, "close", lambda: None)()  # e.g. finish the run log
                self.world = self.factory(self.seed)
                return {"ok": True}
            if cmd == "pause":
                self.paused = bool(msg.get("on", not self.paused))
                return {"ok": True}
            if cmd == "speed":
                v = msg.get("value")
                self.speed_override = None if v in (None, "auto") else max(1, int(v))
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

    def _speed(self) -> int:
        return 0 if self.paused else (self.speed_override or self.world.speed())

    def _frame(self, channel: str, speed: int) -> str:
        out = self.world.snapshot(channel, speed)
        # console extras (feature 25): who sets the warp, and whether auto-warp is slowed
        out["warp_mode"] = ("paused" if self.paused else
                            "manual" if self.speed_override else "auto")
        out["near_event"] = out["warp_mode"] == "auto" and bool(self.world.near_event())
        return json.dumps(out)

    def tick(self) -> dict[str, str]:
        """One frame: advance the source and render both channels (no I/O, testable)."""
        speed = self._speed()
        self.world.step(int(speed * 1000 / self.hz))
        return {ch: self._frame(ch, speed) for ch in ("shore", "truth")}

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


async def serve(factory: Callable[[int], Any], host: str, port: int, seed: int, hz: float = 10.0,
                ready=None, serve_web: bool = False, name: str = "feed") -> None:
    from websockets.asyncio.server import serve as ws_serve

    feed = Feed(factory, seed, hz)
    extra = {"process_request": _static} if serve_web else {}
    async with ws_serve(feed.handler, host, port, **extra) as server:
        bound = server.sockets[0].getsockname()[1]
        log.info("%s on ws://%s:%d/shore and /truth, seed %d", name, host, bound, seed)
        if serve_web:
            log.info("console on http://%s:%d/", host, bound)
        if ready is not None:
            ready.set_result((feed, bound))
        await feed.run()
