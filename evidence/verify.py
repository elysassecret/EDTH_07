"""Verify an evidence bundle: python -m evidence.verify runs/<run>/evidence.json

Prints pass, or the first bad sequence number per boat.
"""
from __future__ import annotations

import json
import sys

from .chain import verify_chain


def verify_bundle(bundle: dict) -> tuple[bool, list[str]]:
    ok_all = True
    lines = []
    witnessed = bundle.get("witnessed", {})
    for b in sorted(bundle["chains"], key=int):
        w = [(int(s), h) for s, h in witnessed.get(str(b), [])]
        ok, msg = verify_chain(bundle["chains"][b], w)
        ok_all &= ok
        lines.append(("PASS " if ok else "FAIL ") + msg)
    return ok_all, lines


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: python -m evidence.verify <evidence.json>")
        return 2
    bundle = json.load(open(argv[0], encoding="utf-8"))
    ok, lines = verify_bundle(bundle)
    print("\n".join(lines))
    print("VERIFIED" if ok else "TAMPERED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
