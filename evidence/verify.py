"""Check an evidence log. Owner: C. BUILD_PLAN step 30 (feature 28).

    uv run python -m evidence.verify runs/<run>.evidence.jsonl [--key-id <16 hex>]

Checks every chain: record numbers in order, each record linked to the one before, each
record's hash, and the signed head. Names the first bad record of each broken chain.
With --key-id, also checks the file was signed by the key you expect (not just any key).
Exit code 0 only if every chain is intact.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evidence.chain import check_chain
from evidence.keys import key_id, pub_from_hex


def verify(path: Path, expect_key_id: str | None = None) -> tuple[bool, list[str]]:
    msgs: list[str] = []
    try:
        lines = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln]
    except (OSError, ValueError) as e:
        return False, [f"cannot read {path}: {e}"]
    if not lines or lines[0].get("type") != "header":
        return False, ["not an evidence log: first line is not a header"]
    head = lines[0]
    try:
        pub = pub_from_hex(head["pub"])
    except (KeyError, ValueError):
        return False, ["header has no valid public key"]
    if key_id(head["pub"]) != head.get("key_id"):
        msgs.append("header key id does not match its public key")
    if expect_key_id and key_id(head["pub"]) != expect_key_id:
        msgs.append(f"signed by key {key_id(head['pub'])}, not the expected {expect_key_id}")
    records: dict[str, list[dict]] = {}
    heads: dict[str, dict] = {}
    for rec in lines[1:]:
        if rec.get("type") == "record":
            records.setdefault(str(rec.get("chain")), []).append(rec)
        elif rec.get("type") == "head":
            heads[str(rec.get("chain"))] = rec
    for name in sorted(set(records) | set(heads)):
        problem = check_chain(name, records.get(name, []), heads.get(name), pub)
        if problem:
            msgs.append(problem)
    ok = not msgs
    if ok:
        n = sum(len(v) for v in records.values())
        msgs.append(f"chain OK: {len(records)} chains, {n} records, key id {head['key_id']}")
    return ok, msgs


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify an evidence log.")
    ap.add_argument("evidence", type=Path)
    ap.add_argument("--key-id", help="expected signing key id (16 hex characters)")
    args = ap.parse_args()
    ok, msgs = verify(args.evidence, args.key_id)
    for m in msgs:
        print(m)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
