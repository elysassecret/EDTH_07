"""Evaluator comparison: what the shore believes next to what is true. Owner: C.

Computed by the feed for /truth frames only (key "eval"), never for /shore, so the operator's
picture and the agents never see it. Works on contract snapshots as JSON dicts, so the real
sim and the mock feed get the same comparison.

    boats     per boat: true and last-known position, offset between them, shore data age,
              true and believed link
    contacts  true contacts, and whether the shore picture has them yet
    links     every pair where the true link state and the shore's belief differ
    seg_age   per cable segment: shore estimate and true revisit age (None = never visited)
"""

from __future__ import annotations

from math import hypot


def _pair(a: int, b: int) -> tuple[int, int]:
    return (min(a, b), max(a, b))


def _kind(state: str) -> str:
    """up and cut are themselves; down, none and not reported all mean "no working link"."""
    return state if state in ("up", "cut") else "no link"


def compare(shore: dict, truth: dict) -> dict:
    t = truth["t"]
    sb = {b["id"]: b for b in shore.get("boats", [])}
    boats = []
    for b in truth.get("boats", []):
        s = sb.get(b["id"])
        boats.append({
            "id": b["id"],
            "true": [b["lon"], b["lat"]],
            "shore": [s["lon"], s["lat"]] if s else None,
            "offset_m": round(hypot(b["x"] - s["x"], b["y"] - s["y"])) if s else None,
            "shore_age_s": t - s["last_heard"] if s else None,
            "true_link": b.get("link"),
            "shore_link": s.get("link") if s else None,
            "true_mode": b.get("mode"),
            "shore_mode": s.get("mode") if s else None,
        })

    seen = {c.get("track") for c in shore.get("contacts", [])}
    contacts = [{
        "id": c["id"], "track": c.get("track"), "pos": [c["lon"], c["lat"]], "ais": c.get("ais"),
        "on_shore": c.get("track") in seen,
    } for c in truth.get("contacts", [])]

    tl = {_pair(lk["a"], lk["b"]): lk["state"] for lk in truth.get("links", [])}
    sl = {_pair(lk["a"], lk["b"]): lk["state"] for lk in shore.get("links", [])}
    links = []
    for p in sorted(set(tl) | set(sl)):
        true_state = tl.get(p, "none")  # none: out of range or switched off
        believed = sl.get(p, "not reported")
        if _kind(true_state) != _kind(believed):
            links.append({"a": p[0], "b": p[1], "true": true_state, "shore": believed})

    ta, sa = truth.get("seg_age", {}), shore.get("seg_age", {})
    seg_age = {k: {"shore": sa.get(k), "true": ta.get(k)} for k in sorted(set(ta) | set(sa))}
    return {"t": t, "boats": boats, "contacts": contacts, "links": links, "seg_age": seg_age,
            # true cable km past the revisit target (real sim only; None on the mock)
            "cable_overdue": truth.get("cable_overdue")}
