"""Hash chain and signed heads. Owner: C. BUILD_PLAN step 30 (feature 28).

A chain is a list of records. Each record holds the hash of the one before it, and its own
hash over all its other fields, so changing any record after it was written breaks the chain
from that record on. The latest record's hash (the head) is signed with Ed25519, so the whole
chain cannot be rewritten without the private key either.

What it shows: whether a record was changed after it was written.
What it does not show: that the sensor or the report was right. No claim on admissibility.

Pure functions plus one small class; no file or network access (keys.py loads keys).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

GENESIS = "0" * 64
RECORD_FIELDS = ("chain", "seq", "prev", "kind", "t_obs", "t_log", "time_source", "source",
                 "zone", "data")


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def record_hash(rec: dict) -> str:
    return hashlib.sha256(canonical({k: rec[k] for k in RECORD_FIELDS})).hexdigest()


def head_message(chain: str, seq: int, h: str) -> bytes:
    return f"edth07-evidence-head:{chain}:{seq}:{h}".encode()


@dataclass
class Chain:
    name: str
    records: list[dict] = field(default_factory=list)

    @property
    def head(self) -> tuple[int, str]:
        if not self.records:
            return -1, GENESIS
        last = self.records[-1]
        return last["seq"], last["hash"]

    def append(self, kind: str, t_obs: int | None, t_log: int, time_source: str, source: str,
               zone: list[str], data: dict) -> dict:
        seq, prev = self.head
        rec = {"chain": self.name, "seq": seq + 1, "prev": prev, "kind": kind, "t_obs": t_obs,
               "t_log": t_log, "time_source": time_source, "source": source, "zone": zone,
               "data": data}
        rec["hash"] = record_hash(rec)
        self.records.append(rec)
        return rec

    def sign_head(self, key: Ed25519PrivateKey) -> dict:
        seq, h = self.head
        return {"chain": self.name, "seq": seq, "hash": h,
                "sig": key.sign(head_message(self.name, seq, h)).hex()}


def check_chain(name: str, records: list[dict], head: dict | None,
                pub: Ed25519PublicKey | None) -> str | None:
    """None if the chain is intact, else the first problem in plain words."""
    prev = GENESIS
    for i, rec in enumerate(records):
        seq = rec.get("seq")
        if seq != i:
            return f"{name}: record {i} is missing (found record {seq} in its place)"
        if rec.get("prev") != prev:
            return f"{name}: record {i} does not link to record {i - 1} (prev hash differs)"
        try:
            h = record_hash(rec)
        except KeyError as e:
            return f"{name}: record {i} lacks field {e}"
        if h != rec.get("hash"):
            return f"{name}: record {i} was changed after it was written (hash differs)"
        prev = rec["hash"]
    if head is None:
        return f"{name}: no signed head"
    last_seq = len(records) - 1
    if head.get("seq") != last_seq or head.get("hash") != prev:
        return (f"{name}: signed head is record {head.get('seq')}, but the chain ends at "
                f"record {last_seq}")
    if pub is None:
        return f"{name}: no public key to check the head signature"
    try:
        pub.verify(bytes.fromhex(head["sig"]), head_message(name, last_seq, prev))
    except (InvalidSignature, ValueError, KeyError):
        return f"{name}: head signature does not match the public key"
    return None
