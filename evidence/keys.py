"""Ed25519 key for signing chain heads. Owner: C.

The private key lives in runs/ (gitignored), created on first use with owner-only access.
Never commit it. The public key goes into every evidence file; its key id is the first
16 hex characters of SHA-256 over the raw public key.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def load_or_create(path: Path) -> Ed25519PrivateKey:
    if path.is_file():
        key = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError(f"{path} is not an Ed25519 key")
        return key
    key = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(pem)
    return key


def pub_hex(key: Ed25519PrivateKey | Ed25519PublicKey) -> str:
    pub = key.public_key() if isinstance(key, Ed25519PrivateKey) else key
    return pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


def pub_from_hex(h: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(h))


def key_id(pub_hex_str: str) -> str:
    return hashlib.sha256(bytes.fromhex(pub_hex_str)).hexdigest()[:16]
