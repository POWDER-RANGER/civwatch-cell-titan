"""Ed25519 signing for evidence records (roadmap P1-3).

A hash chain alone is tamper-evident only against someone who cannot recompute
it: anyone with write access can rewrite records and rebuild every hash. Each
schema-v2 record therefore carries an Ed25519 signature over its record hash,
made with a key the API never exposes. Offline verifiers need only the public
key, published at ``GET /api/evidence/pubkey``.

Scope: signatures detect edits by anyone without the private key (exported
logs, copied data directories, a compromised consumer). They do not protect
against an attacker who can read the key file on the Titan host; keep the key
outside ``EVIDENCE_DIR`` and readable only by the Titan user.
"""
from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def key_id_for(public_key: Ed25519PublicKey) -> str:
    """Stable 16-hex identifier: first 8 bytes of SHA-256 over the raw public key."""
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()[:16]


def public_key_b64(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def load_public_key_b64(value: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(base64.b64decode(value, validate=True))


@dataclass(frozen=True)
class Signer:
    private_key: Ed25519PrivateKey

    @property
    def public_key(self) -> Ed25519PublicKey:
        return self.private_key.public_key()

    @property
    def key_id(self) -> str:
        return key_id_for(self.public_key)

    def sign_hash(self, record_hash: str) -> str:
        return base64.b64encode(self.private_key.sign(record_hash.encode("ascii"))).decode("ascii")

    @classmethod
    def generate(cls) -> "Signer":
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def load_or_create(cls, path: str | Path) -> "Signer":
        """Load a PEM (PKCS#8, unencrypted) key, creating it with mode 0600 if missing."""
        key_path = Path(path)
        if key_path.exists():
            key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise ValueError(f"{key_path} is not an Ed25519 private key")
            return cls(key)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        signer = cls.generate()
        pem = signer.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(pem)
        return signer


def verify_signature(public_key: Ed25519PublicKey, record_hash: str, signature_b64: str) -> bool:
    try:
        public_key.verify(base64.b64decode(signature_b64, validate=True), record_hash.encode("ascii"))
        return True
    except (InvalidSignature, ValueError):
        return False
