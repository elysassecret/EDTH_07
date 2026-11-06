"""Live bridge: runs the sim at a time-warp and streams snapshots over WebSocket.

    python -m server.bridge [--mode elysa] [--seed 1] [--port 8765] [--http 8000] [--warp auto]

Static files from web/ are served on http://localhost:8000/. WebSocket on ws://localhost:8765/ws.

Channels in every frame ("ch"):
  scene   once per connection: geometry in local metres (x east, y north) and the event tape
  shore   /shore picture: delivered radio data only (what the watch officer may see)
  truth   evaluator panel: ground truth, labelled
  status  warp, paused, t, mode, seed, scorecard when evaluated, applied injections
  ctl     reply to a command
Commands from the client (JSON): see handle_command().
Auto-warp: 240x between events, 5x for 120 sim-s around each scripted event.
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import http.server
import json
import threading
from pathlib import Path

import websockets
from websockets.asyncio.server import serve

from contract.config import MODES, ROOT, load, load_scenario
from eval.metrics import Metrics
from world import geo
from world.sim import Sim

FAST, SLOW = 240, 5
SLOW_BEFORE_S, SLOW_AFTER_S = 60, 60
FPS = 10


class Bridge:
    def __init__(self, mode: str, seed: int, warp: str | int, use_ais: bool = True, record: bool = True):
        self.mode = mode
        self.seed = seed
        self.warp = warp
        self.use_ais = use_ais
        self.record = record
        self.paused = False
        self.clients: set = set()
        self.frame = 0
        self.scene_frame: dict | None = None
        self.speed_override: int | None = None if warp == "auto" else int(warp)
        self.build()

    def build(self) -> None:
        ov = dict(MODES[self.mode])
        cfg = load(overrides=ov)
        log_dir = ROOT / "runs" / "live"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"live_{self.mode}_s{self.seed}.jsonl" if self.record else None
        self.sim = Sim(cfg, mode=self.mode, seed=self.seed, use_ais=self.use_ais, log_path=log_path)
        self.metrics = Metrics(self.sim)
        self.sim.observers.append(self.metrics)
        self.events = [e for e in self.sim.events if e["kind"] not in ("reset",)]
        self.sim.run_warm()
        self.scene_frame = self.make_scene()
        self.evaluated_sent = False

    # ---- frames -------------------------------------------------------------
    def make_scene(self) -> dict:
        sc = self.sim.scene
        cfg = self.sim.cfg
        return {"ch": "scene",
                "box": geo.box_corners_xy(), "center": geo.uv_to_xy(0, 0), "bearing": geo.BOX_BEARING,
                "len_m": geo.BOX_LEN, "wid_m": geo.BOX_WID,
                "cables": {k: v for k, v in sc.cables.items()},
                "scenario_lines": cfg["scene"]["scenario_lines"],
                "segments": [{"task": s.task, "letter": s.letter, "points": s.points, "length_m": round(s.length_m),
                              "samples": s.samples} for s in sc.segments],
                "lane": sc.lane, "lane_p5": sc.lane_p5, "lane_p95": sc.lane_p95, "lane_cross": sc.lane_cross,
                "shore": sc.shore_xy, "relay": sc.relay_xy, "pickets": {"N": sc.picket_n, "S": sc.picket_s},
                "events": self.events, "mode": self.mode, "seed": self.seed,
                "cfg": {"speed_mps": cfg["boat"]["speed_mps"], "r_detect": cfg["boat"]["r_detect_m"],
                        "r_verify": cfg["boat"]["r_verify_m"], "keep_in_view": cfg["boat"]["keep_in_view_m"],
                        "standoff": cfg["boat"]["standoff_m"], "standoff_floor": cfg["boat"]["standoff_floor_m"],
                        "radio_boat": cfg["radio"]["boat_m"], "radio_shore": cfg["radio"]["shore_m"],
                        "revisit_target_s": cfg["run"]["revisit_target_s"], "horizon_s": cfg["run"]["horizon_s"],
                        "evaluate_s": cfg["run"]["evaluate_s"], "config_hash": cfg["_hash"]},
                "initial_owner": self.sim.mission.initial_owner}

    def speed_now(self) -> int:
        if self.speed_override is not None:
            return self.speed_override
        t = self.sim.t / 1000
        for e in self.events:
            if e["t"] - SLOW_BEFORE_S <= t <= e["t"] + SLOW_AFTER_S:
                return SLOW
        return FAST

    def status_frame(self) -> dict:
        f = {"ch": "status", "t": self.sim.t // 1000, "speed": self.speed_now(), "auto": self.speed_override is None,
             "paused": self.paused, "mode": self.mode, "seed": self.seed, "injections": self.sim.injections[-20:],
             "warm_hash": self.sim.warm_hash, "config_hash": self.sim.cfg["_hash"],
             "next_event": next((e for e in self.events if e["t"] * 1000 > self.sim.t), None)}
        if self.metrics.evaluated is not None:
            f["scorecard"] = self.metrics.evaluated
        return f

    def truth_frame(self) -> dict:
        tv = self.sim.truth_view()
        t = self.sim.t
        tv["ch"] = "truth"
        tv["ages_s"] = [int(a) for a in (self.metrics.ages(t) // 1000)]
        tv["seg_age"] = self.metrics.seg_age(t)
        tv["km_overdue"] = round(self.metrics.km_overdue(t), 1)
        tv["worst_age_s"] = self.metrics.worst_age(t)
        tv["crossings"] = len(self.metrics.crossings)
        tv["crossings_in_view"] = sum(1 for c in self.metrics.crossings if c["in_view"])
        tv["detect_s"] = {k: (v - self.metrics.dwell_start.get(k, v)) // 1000 for k, v in self.metrics.detect_t.items()}
        return tv

    def shore_frame(self) -> dict:
        sv = self.sim.shore_view()
        sv["ch"] = "shore"
        return sv

    # ---- commands ---------------------------------------------------------------
    def handle_command(self, cmd: dict) -> dict:
        c = cmd.get("cmd")
        if c == "inject":
            kind = cmd.get("kind")
            allowed = {"boat_fail", "boat_restore", "link_off", "link_on", "battery_low", "contact_start",
                       "contact_depart", "contact_remove"}
            if kind not in allowed:
                return {"ok": False, "error": f"unknown injection {kind}"}
            ev = {k: v for k, v in cmd.items() if k != "cmd"}
            self.sim.inject(ev)
            return {"ok": True, "injected": ev}
        if c == "operator":
            ev = {"kind": "cmd", "action": cmd.get("action"), "cid": cmd.get("cid")}
            self.sim.inject(ev)
            return {"ok": True, "injected": ev}
        if c == "warp":
            v = cmd.get("speed", "auto")
            self.speed_override = None if v == "auto" else max(1, int(v))
            return {"ok": True, "speed": self.speed_now()}
        if c == "pause":
            self.paused = True
            return {"ok": True, "paused": True}
        if c == "resume":
            self.paused = False
            return {"ok": True, "paused": False}
        if c == "step":
            n = int(cmd.get("ticks", 1))
            for _ in range(n):
                self.sim.step()
            return {"ok": True, "t": self.sim.t // 1000}
        if c == "reset":
            self.sim.log.close()
            self.mode = cmd.get("mode", self.mode)
            self.seed = int(cmd.get("seed", self.seed))
            self.build()
            return {"ok": True, "reset": True, "mode": self.mode, "seed": self.seed, "scene": True}
        if c == "evidence":
            bundle = self.sim.evidence_bundle()
            from evidence.verify import verify_bundle
            ok, lines = verify_bundle(bundle)
            tamper = cmd.get("tamper")
            tampered = None
            if tamper:
                import copy
                b2 = copy.deepcopy(bundle)
                ch = b2["chains"].get(str(tamper))
                if ch and ch["entries"]:
                    idx = len(ch["entries"]) // 2
                    ch["entries"][idx]["body"] = {"edited": True, **ch["entries"][idx]["body"]}
                    ok2, lines2 = verify_bundle(b2)
                    tampered = {"ok": ok2, "lines": lines2, "edited_seq": ch["entries"][idx]["seq"]}
            return {"ok": True, "verified": ok, "lines": lines, "tampered": tampered,
                    "entries": {b: len(ch["entries"]) for b, ch in bundle["chains"].items()}}
        return {"ok": False, "error": f"unknown cmd {c}"}

    # ---- loop ---------------------------------------------------------------------
    async def run(self, port: int) -> None:
        async def handler(ws):
            path = ws.request.path if ws.request else "/ws"
            self.clients.add((ws, path))
            try:
                await ws.send(json.dumps(self.scene_frame))
                await ws.send(json.dumps(self.status_frame()))
                async for msg in ws:
                    try:
                        cmd = json.loads(msg)
                    except Exception:
                        continue
                    rep = self.handle_command(cmd)
                    rep["ch"] = "ctl"
                    rep["cmd"] = cmd
                    await ws.send(json.dumps(rep))
                    if rep.get("scene"):
                        await ws.send(json.dumps(self.scene_frame))
            finally:
                self.clients.discard((ws, path))

        async with serve(handler, "localhost", port, max_size=2**22):
            print(f"[bridge] ws://localhost:{port}/ws  mode={self.mode} seed={self.seed} warp={self.warp}")
            while True:
                await self.tick()
                await asyncio.sleep(1.0 / FPS)

    async def tick(self) -> None:
        if not self.paused:
            n = max(1, self.speed_now() // FPS)
            for _ in range(n):
                self.sim.step()
                if self.sim.t >= self.sim.horizon_ms + 3_600_000:
                    self.paused = True
                    break
        self.frame += 1
        if not self.clients:
            return
        status = json.dumps(self.status_frame())
        shore = json.dumps(self.shore_frame())
        truth = json.dumps(self.truth_frame()) if self.frame % 2 == 0 else None
        dead = []
        for ws, path in list(self.clients):
            try:
                if path.startswith("/shore"):
                    await ws.send(shore)
                elif path.startswith("/truth"):
                    if truth:
                        await ws.send(truth)
                else:
                    await ws.send(shore)
                    if truth:
                        await ws.send(truth)
                await ws.send(status)
            except websockets.ConnectionClosed:
                dead.append((ws, path))
        for d in dead:
            self.clients.discard(d)


def serve_static(port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "web"))
    httpd = http.server.ThreadingHTTPServer(("localhost", port), handler)
    httpd.daemon_threads = True
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    print(f"[bridge] dashboard on http://localhost:{port}/")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="elysa", choices=sorted(MODES))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--http", type=int, default=8000)
    ap.add_argument("--warp", default="auto")
    ap.add_argument("--no-ais", action="store_true")
    ap.add_argument("--no-record", action="store_true")
    args = ap.parse_args(argv)
    serve_static(args.http)
    b = Bridge(args.mode, args.seed, args.warp, use_ais=not args.no_ais, record=not args.no_record)
    try:
        asyncio.run(b.run(args.port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
