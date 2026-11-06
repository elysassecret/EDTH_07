"""Shore console node (node 0). Passive picture built only from delivered radio data.

It is not a coordinator: it never assigns work. It merges records like a boat,
sends heartbeats so boats can measure shore age, and carries the operator's
decisions (Stop, Approve, Decline, Confirm) as records and commands.
"""
from __future__ import annotations

from contract.constants import CLAIMED, CLOSED, HEARTBEAT, PEER_STALE, RELEASED, SHORE_ID, VETOED
from contract.messages import Envelope, make
from contract.tasks import Mission, Rec, merge


class Shore:
    def __init__(self, mission: Mission, cfg: dict):
        self.me = SHORE_ID
        self.mission = mission
        self.max_hops = int(cfg["radio"]["max_hops"])
        self.seq = 0
        self.t = 0
        self.table: dict[str, Rec] = {r.task: r for r in mission.initial_records()}
        self.boats: dict[int, dict] = {}      # fused picture: last known state per boat
        self.direct: dict[int, int] = {}      # last direct heartbeat time per boat
        self.contacts: dict[str, dict] = {}
        self.cues: dict[str, dict] = {}
        self.ais: dict[str, dict] = {}
        self.seen: dict[str, int] = {}
        self.events: list[dict] = []
        self.cards: dict[str, dict] = {}       # pending operator decisions
        self.actions: list[dict] = []          # operator actions taken
        self.outbox: list[bytes] = []
        self.close_ok: set[str] = set()
        self.reports: dict[str, dict] = {}
        self.stats = {"msgs_in": 0}

    def _send(self, kind: str, payload: dict, t: int) -> None:
        self.seq += 1
        env = make(self.me, self.seq, t, kind, payload)
        self.seen[env.msg_id] = env.t_expire
        self.outbox.append(env.encode())

    def event(self, t: int, kind: str, text: str, **extra) -> None:
        self.events.append({"t": t, "kind": kind, "text": text, **extra})
        if len(self.events) > 400:
            self.events = self.events[-400:]

    def _merge(self, r: Rec, t: int) -> None:
        cur = self.table.get(r.task)
        new = r if cur is None else merge(cur, r)
        if cur is not new:
            self.table[r.task] = new
            if r.task.startswith("contact:") and new.state == RELEASED and (cur is None):
                self.cards[r.task] = {"id": r.task, "tier": "delegated", "title": "Contact opened: keeping in view",
                                      "text": "Standing Order 2. Watching is pre-approved.",
                                      "options": ["Confirm", "Stop"], "t": t}
                self.event(t, "contact", f"{r.task} opened by boat {self.contacts.get(r.task, {}).get('by', '?')}: no AIS match, loitering over a cable")
            elif r.task.startswith("contact:") and new.state == CLAIMED and (cur is None or cur.state != CLAIMED):
                self.event(t, "contact", f"boat {new.owner} keeps {r.task} in view at stand-off; deputy {new.deputy or 'none'}")
                self.cards[r.task + ":close"] = {"id": r.task + ":close", "tier": "held",
                                                 "title": "Approve: close to 500 m, photograph both bows",
                                                 "text": "Held for approval. No answer means no action; the boat keeps watching.",
                                                 "options": ["Approve", "Decline"], "t": t, "cid": r.task}
            elif r.task.startswith("contact:") and new.state == CLOSED:
                self.cards.pop(r.task, None)
                self.cards.pop(r.task + ":close", None)
                self.event(t, "contact", f"{r.task} closed")
            elif r.task.startswith("pick:") and new.state == RELEASED and cur is not None and cur.state == CLAIMED:
                self.event(t, "gap", f"Lane picket {r.task[-1]} uncovered (boat {cur.owner} released it)", task=r.task)
            elif r.task.startswith("seg:") and new.state == RELEASED and cur is not None and cur.state == CLAIMED:
                self.event(t, "gap", f"{r.task} open: boat {cur.owner} released it", task=r.task)
            elif new.state == CLAIMED and (cur is None or cur.owner != new.owner):
                self.event(t, "claim", f"boat {new.owner} took {r.task}", task=r.task)

    def handle(self, raw: bytes, t: int) -> None:
        env = Envelope.decode(raw)
        self.stats["msgs_in"] += 1
        if t > env.t_expire or env.msg_id in self.seen:
            return
        self.seen[env.msg_id] = env.t_expire
        p = env.payload
        if env.kind == "HB":
            b = env.src
            self.direct[b] = env.t_created
            self.boats[b] = {"x": p["x"], "y": p["y"], "mode": p["mode"], "batt": p["batt"], "tour": p["tour"],
                             "pick": p["pick"], "relay": p["relay"], "path": p.get("path", "?"),
                             "t": env.t_created, "via": "direct", "head": p.get("head"),
                             "reports": p.get("reports", [])}
            for q, (x, y, mode, batt, age, cycle, pick, relay, tour) in sorted(p.get("peers", {}).items()):
                q = int(q)
                t_obs = env.t_created - age
                if q not in self.boats or self.boats[q]["t"] < t_obs:
                    self.boats[q] = {"x": x, "y": y, "mode": mode, "batt": batt, "tour": tour, "pick": pick,
                                     "relay": relay, "path": "relay", "t": t_obs, "via": f"boat {b}", "head": None,
                                     "reports": []}
            for tup in p.get("recs", []):
                self._merge(Rec.from_tup(tup), t)
            for cid, obs in sorted(p.get("contacts", {}).items()):
                cur = self.contacts.get(cid)
                if cur is None or obs["t"] > cur["t"]:
                    self.contacts[cid] = obs
            for task, g in sorted(p.get("cues", {}).items()):
                if task not in self.cues:
                    self.cues[task] = g
                    self.event(t, "cue", f"Cue for a look: track {g['track']} ({g['type']}) toward cable {task.split(':')[-1]}", task=task)
            for k, v in sorted(p.get("ais", {}).items()):
                if k not in self.ais or v["t"] > self.ais[k]["t"]:
                    self.ais[k] = v
            for rp in p.get("reports", []):
                key = f"{rp['cid']}:{rp['t']}"
                if key not in self.reports:
                    self.reports[key] = rp
                    self.event(t, "report", f"Report from boat {b}: {rp['cid']} {rp['reason']}"
                               + (" (was queued offline)" if rp.get("queued") else ""))
            for et, ek, eb in p.get("ev", []):
                key = f"ev:{b}:{et}:{ek}"
                if key not in self.seen:
                    self.seen[key] = t + 10**9
                    if ek in ("return", "cannot_hold", "report_only", "hold_start", "hold_end", "deputy_takeover",
                              "deputy_decline", "rebalance_release", "cue_look", "contact_close", "docked"):
                        self.event(et, ek, f"boat {b}: {ek} {eb}")
        elif env.kind in ("REC", "VETO"):
            self._merge(Rec.from_tup(p["rec"]), t)
        elif env.kind == "OBS":
            cur = self.contacts.get(p["cid"])
            if cur is None or p["obs"]["t"] > cur["t"]:
                self.contacts[p["cid"]] = p["obs"]
        elif env.kind == "CONTACT":
            if "cid" in p:
                self.contacts.setdefault(p["cid"], p["obs"])
                self._merge(Rec(p["cid"], 1, RELEASED, 0, 0, 0), t)
            elif "cue" in p:
                if p["cue"] not in self.cues:
                    self.cues[p["cue"]] = p["geom"]
                    self.event(t, "cue", f"Cue for a look: track {p['geom']['track']} ({p['geom']['type']})", task=p["cue"])
                self._merge(Rec(p["cue"], 1, RELEASED, 0, 0, 0), t)

    def command(self, cmd: dict, t: int) -> dict:
        """Operator action. Returns a log entry."""
        action = cmd.get("action")
        cid = cmd.get("cid")
        entry = {"t": t, "action": action, "cid": cid}
        if action == "stop" and cid:
            r = self.table.get(cid)
            ver = (r.ver if r else 0) + 1
            rec = Rec(cid, ver, VETOED, 0, 0, 0)
            self._merge(rec, t)
            self._send("VETO", {"rec": rec.tup()}, t)
            self.cards.pop(cid, None)
            self.cards.pop(cid + ":close", None)
            self.event(t, "operator", f"Operator: STOP watching {cid}")
        elif action == "confirm" and cid:
            self.cards.pop(cid, None)
            self.event(t, "operator", f"Operator: confirmed watching {cid}")
        elif action == "approve" and cid:
            self.close_ok.add(cid)
            self._send("CMD", {"cid": cid, "action": "close"}, t)
            self.cards.pop(cid + ":close", None)
            self.event(t, "operator", f"Operator: approved close to 500 m on {cid}")
        elif action == "decline" and cid:
            self.cards.pop(cid + ":close", None)
            self.event(t, "operator", f"Operator: declined close approach on {cid}")
        else:
            entry["ignored"] = True
            return entry
        self.actions.append(entry)
        return entry

    def step(self, t: int, inbox: list[bytes]) -> list[bytes]:
        self.t = t
        self.outbox = []
        for raw in inbox:
            self.handle(raw, t)
        if t % 60_000 == 0:
            self.seen = {k: v for k, v in self.seen.items() if v >= t}
        if t % HEARTBEAT == 0:
            peers = {str(b): [q["x"], q["y"], q["mode"], q["batt"], t - q["t"], 0, q["pick"], q["relay"], q["tour"]]
                     for b, q in sorted(self.boats.items()) if t - q["t"] <= 600_000}
            self._send("HB", {"peers": peers, "x": round(self.mission.shore_xy[0]), "y": round(self.mission.shore_xy[1]),
                              "mode": "SHORE", "batt": 1000, "cycle": 0, "tour": [], "pick": "", "relay": False,
                              "shore_age": 0, "path": "direct",
                              "recs": [r.tup() for _, r in sorted(self.table.items())],
                              "close_ok": sorted(self.close_ok)}, t)
        return self.outbox

    def link_of(self, b: int, t: int) -> str:
        d = self.direct.get(b)
        if d is not None and t - d <= PEER_STALE:
            return "direct"
        q = self.boats.get(b)
        if q is not None and t - q["t"] <= 60_000:
            return "relay"
        return "none"

    def view(self, t: int) -> dict:
        boats = []
        for b in sorted(self.boats):
            q = self.boats[b]
            boats.append({"id": b, "x": q["x"], "y": q["y"], "mode": q["mode"], "batt": q["batt"], "tour": q["tour"],
                          "pick": q["pick"], "relay": q["relay"], "link": self.link_of(b, t), "age_s": (t - q["t"]) // 1000,
                          "via": q["via"], "path": q["path"]})
        tasks = {k: {"v": r.ver, "owner": r.owner, "deputy": r.deputy, "state": r.state} for k, r in sorted(self.table.items())}
        contacts = [{"id": cid, **o, "age_s": (t - o["t"]) // 1000, "state": self.table[cid].state if cid in self.table else -1}
                    for cid, o in sorted(self.contacts.items())]
        return {"boats": boats, "tasks": tasks, "contacts": contacts, "cues": self.cues,
                "ais": [{"track": k, **v, "age_s": (t - v["t"]) // 1000} for k, v in sorted(self.ais.items()) if t - v["t"] <= 600_000],
                "events": self.events[-60:], "cards": [c for _, c in sorted(self.cards.items())],
                "actions": len(self.actions)}
