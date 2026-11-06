"""Per-boat hash chain. Heads are signed with Ed25519 every 20 entries and on task or contact changes.

It proves records were not edited later, not that a sensor told the truth.
Keys derive from the run seed so a run stays deterministic; a real boat
would hold its own key. Canonical form: JSON with sorted keys, no spaces,
integers only (metres, milliseconds), which matches RFC 8785 for this subset.
Time source: the simulation clock. Zone label: "sim" (a real boat would label GNSS/UTC).
"""
from __future__ import annotations

import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

SIGN_KINDS = {"claim", "release", "contact_open", "contact_close", "shadow_start", "shadow_end", "veto_received",
              "close_approved", "deputy_takeover", "return", "cue_open", "cue_look", "rebalance_release"}


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def derive_key(seed: int, boat: int) -> Ed25519PrivateKey:
    raw = hashlib.sha256(f"edth07-evidence-{seed}-{boat}".encode()).digest()
    return Ed25519PrivateKey.from_private_bytes(raw)


class Chain:
    def __init__(self, boat: int, seed: int):
        self.boat = boat
        self.key = derive_key(seed, boat)
        self.pub = self.key.public_key().public_bytes_raw().hex()
        self.entries: list[dict] = []
        self.heads: list[dict] = []
        self.prev = "0" * 64
        self.seq = 0

    def append(self, t: int, kind: str, body: dict) -> dict:
        self.seq += 1
        body_hash = hashlib.sha256(canon(body)).hexdigest()
        entry = {"seq": self.seq, "t_ms": int(t), "boat": self.boat, "kind": kind, "body_sha256": body_hash,
                 "prev": self.prev, "zone": "sim", "body": body}
        h = hashlib.sha256(canon({k: v for k, v in entry.items() if k != "body"})).hexdigest()
        entry["hash"] = h
        self.entries.append(entry)
        self.prev = h
        if kind in SIGN_KINDS or self.seq % 20 == 0:
            self.sign_head(t)
        return entry

    def sign_head(self, t: int) -> dict:
        head = {"boat": self.boat, "seq": self.seq, "hash": self.prev, "t_ms": int(t)}
        sig = self.key.sign(canon(head)).hex()
        rec = {"head": head, "sig": sig}
        self.heads.append(rec)
        return rec

    def head(self) -> list:
        return [self.seq, self.prev[:16]]

    def dump(self) -> dict:
        return {"boat": self.boat, "pub": self.pub, "entries": self.entries, "heads": self.heads}


def verify_chain(dump: dict, witnessed: list[tuple[int, str]] | None = None) -> tuple[bool, str]:
    """Walk one chain. Returns (ok, message). witnessed: (seq, hash16) pairs seen by peers in heartbeats."""
    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(dump["pub"]))
    prev = "0" * 64
    by_seq: dict[int, str] = {}
    for e in dump["entries"]:
        if e["prev"] != prev:
            return False, f"boat {dump['boat']} seq {e['seq']}: prev hash mismatch"
        body_hash = hashlib.sha256(canon(e["body"])).hexdigest()
        if body_hash != e["body_sha256"]:
            return False, f"boat {dump['boat']} seq {e['seq']}: body edited"
        h = hashlib.sha256(canon({k: v for k, v in e.items() if k not in ("body", "hash")})).hexdigest()
        if h != e["hash"]:
            return False, f"boat {dump['boat']} seq {e['seq']}: entry hash mismatch"
        prev = h
        by_seq[e["seq"]] = h
    for rec in dump["heads"]:
        head = rec["head"]
        try:
            pub.verify(bytes.fromhex(rec["sig"]), canon(head))
        except InvalidSignature:
            return False, f"boat {dump['boat']} head seq {head['seq']}: bad signature"
        if by_seq.get(head["seq"]) != head["hash"]:
            return False, f"boat {dump['boat']} head seq {head['seq']}: head does not match chain"
    for seq, h16 in witnessed or []:
        if seq in by_seq and not by_seq[seq].startswith(h16):
            return False, f"boat {dump['boat']} seq {seq}: peers witnessed a different head"
    return True, f"boat {dump['boat']}: {len(dump['entries'])} entries, {len(dump['heads'])} signed heads, ok"
