"""Narrator: plain-language lines about what changed in the shore picture. Owner: C.

Input is only what the operator already has: consecutive /shore snapshots (task owners and
states, boat modes, links, data age). Never truth. It says what changed, not why: the shore does
not see bids, so it says "took", not "won the cheapest bid".

Feed runs one Narrator per source and adds the latest lines to /shore frames as "narration".
Deterministic: same frames in, same lines out.
"""

from __future__ import annotations

MAX_LINES = 40


def _usv(i: int) -> str:
    return f"USV {i:02d}"


def _picket(task: str) -> str:
    return f"lane picket {task.split(':', 1)[1]}"


class Narrator:
    def __init__(self, stale_after_s: int = 60):
        self.stale_after_s = stale_after_s
        self.lines: list[dict] = []
        self._tasks: dict[str, tuple[int, int]] | None = None  # task -> (owner, state)
        self._boats: dict[int, dict] = {}
        self._stale: set[int] = set()
        self._contacts: dict[str, dict] | None = None  # id -> flags last seen

    def update(self, snap: dict) -> list[dict]:
        """Compare with the previous frame; append and return the new lines."""
        t = snap["t"]
        tasks = {k: (v["owner"], v["state"]) for k, v in sorted(snap.get("tasks", {}).items())}
        boats = {b["id"]: b for b in snap.get("boats", [])}
        new: list[str] = []
        contacts = {c["id"]: c for c in snap.get("contacts", [])}
        if self._tasks is not None:
            new += self._task_lines(self._tasks, tasks)
            new += self._boat_lines(boats, t)
            new += self._contact_lines(contacts)
        else:
            self._stale = {i for i, b in boats.items() if t - b["last_heard"] > self.stale_after_s}
        self._tasks = tasks
        self._boats = boats
        self._contacts = {k: dict(c.get("flags", {})) for k, c in contacts.items()}
        out = [{"t": t, "text": s} for s in new]
        self.lines = (self.lines + out)[-MAX_LINES:]
        return out

    def _task_lines(self, old: dict, cur: dict) -> list[str]:
        took: dict[int, list[str]] = {}
        opened: dict[int, list[str]] = {}  # who left it -> pickets now open
        ownerless: list[str] = []
        lines: list[str] = []
        for k in sorted(set(old) | set(cur)):
            o_owner, o_state = old.get(k, (0, 0))
            n_owner, n_state = cur.get(k, (0, 0))
            held_before = o_state == 1 and o_owner
            held_now = n_state == 1 and n_owner
            if held_now and (not held_before or o_owner != n_owner):
                if k.startswith("seg:"):
                    took.setdefault(n_owner, []).append(k)
                elif k.startswith("pick:"):
                    lines.append(f"{_usv(n_owner)} back on {_picket(k)}")
                elif k == "relay":
                    lines.append(f"{_usv(n_owner)} took the relay role")
                elif k.startswith("contact:"):
                    lines.append(f"{_usv(n_owner)} keeping {k.split(':', 1)[1]} in view")
                else:
                    lines.append(f"{_usv(n_owner)} took {k}")
            elif held_before and not held_now:
                if k.startswith("pick:"):
                    opened.setdefault(o_owner, []).append(k)
                elif k.startswith("contact:"):
                    lines.append(f"{_usv(o_owner)} stopped keeping {k.split(':', 1)[1]} in view")
                elif k.startswith("seg:"):
                    ownerless.append(k)
        if ownerless:
            lines.append(f"Cable {', '.join(ownerless)} open: no owner yet")
        for owner, segs in sorted(took.items()):
            text = f"{_usv(owner)} took cable {', '.join(segs)}"
            if owner in opened:
                text += "; " + ", ".join(f"{_picket(p)} now uncovered" for p in opened.pop(owner))
            lines.append(text)
        for _, picks in sorted(opened.items()):
            lines += [f"Lane picket {p.split(':', 1)[1]} now uncovered" for p in picks]
        return lines

    def _contact_lines(self, contacts: dict) -> list[str]:
        lines: list[str] = []
        old = self._contacts or {}
        for k, c in sorted(contacts.items()):
            name = c.get("track") or k
            flags = c.get("flags", {})
            seen = ", ".join(_usv(i) for i in c.get("seen_by", [])) or "no boat now"
            if k not in old:
                kind = "AIS track" if c.get("ais") else "camera only, no AIS match"
                if not c.get("ais"):  # AIS traffic is routine; only no-AIS contacts are news
                    lines.append(f"Shore has contact {name}: {kind}, seen by {seen}")
                continue
            was = old[k]
            if flags.get("name") and not was.get("name"):
                lines.append(f"{name}: look within 500 m done")
            if flags.get("cannot_hold") and not was.get("cannot_hold"):
                lines.append(f"{name} leaving faster than our boats: cannot hold")
        return lines

    def _boat_lines(self, boats: dict, t: int) -> list[str]:
        lines: list[str] = []
        for i, b in sorted(boats.items()):
            prev = self._boats.get(i)
            stale = t - b["last_heard"] > self.stale_after_s
            if stale and i not in self._stale:
                self._stale.add(i)
                lines.append(f"Shore has not heard {_usv(i)} for over {self.stale_after_s} s")
                continue
            if not stale and i in self._stale:
                self._stale.discard(i)
                lines.append(f"Shore hears {_usv(i)} again")
            if prev is None or stale:
                continue
            holds_contact = any(r.startswith("contact:") for r in b.get("roles", []))
            if b["mode"] != prev["mode"] and not (b["mode"] == "SHADOWING" and holds_contact):
                word = {"RETURNING": "returning to Korsør", "SHADOWING": "keeping a contact in view",
                        "UNAVAILABLE": "at Korsør, not available",
                        "PATROL": "patrolling"}.get(b["mode"])
                if word:
                    lines.append(f"{_usv(i)} {word}")
            if b["link"] != prev["link"]:
                if b["link"] == "direct":
                    lines.append(f"{_usv(i)} direct to shore")
                elif b["link"] == "peer":
                    via = b.get("via")
                    lines.append(f"{_usv(i)} reaches shore through "
                                 + (_usv(via) if via else "a peer"))
                else:
                    lines.append(f"{_usv(i)} has no path to shore")
        return lines
