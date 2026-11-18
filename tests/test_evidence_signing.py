"""Schema-v2 Ed25519 evidence signatures (roadmap P1-3)."""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from fastapi.testclient import TestClient

from titan.evidence import (
    SIGNED_SCHEMA_VERSION,
    EvidenceChain,
    canonical_material,
    digest,
)
from titan.signing import Signer, load_public_key_b64, verify_signature


def _lines(chain: EvidenceChain) -> list[dict]:
    return [json.loads(x) for x in chain.path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _write(chain: EvidenceChain, records: list[dict]) -> None:
    chain.path.write_text(
        "".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
    )


def _rehash(rec: dict) -> dict:
    rec["hash"] = digest(
        canonical_material(
            seq=rec["seq"],
            ts=rec["ts"],
            kind=rec["kind"],
            sensor_id=rec["sensor_id"],
            body=rec["body"],
            prev_hash=rec["prev_hash"],
            schema_version=rec.get("schema_version", 1),
        )
    )
    return rec


def _forge_rebuilt_chain(records: list[dict], index: int, new_body: dict) -> list[dict]:
    """What an attacker with write access but no key can do: edit and rebuild every hash."""
    out = [dict(r) for r in records]
    out[index]["body"] = new_body
    prev = out[index - 1]["hash"] if index else "0" * 64
    for rec in out[index:]:
        rec["prev_hash"] = prev
        _rehash(rec)
        prev = rec["hash"]
    return out


def test_signed_chain_verifies_and_is_fully_signed(tmp_path: Path):
    signer = Signer.generate()
    chain = EvidenceChain(tmp_path, "s", signer=signer)
    a = chain.append("boot", {"v": 1})
    chain.append("telemetry", {"rssi": -70})
    assert a.schema_version == SIGNED_SCHEMA_VERSION
    assert a.key_id == signer.key_id
    assert verify_signature(signer.public_key, a.hash, a.sig)
    result = chain.verify()
    assert result["ok"] is True
    assert result["signed_records"] == 2
    assert result["signatures"] == "verified"
    assert result["fully_signed"] is True


def test_forged_chain_with_recomputed_hashes_fails_signature(tmp_path: Path):
    signer = Signer.generate()
    chain = EvidenceChain(tmp_path, "s", signer=signer)
    for i in range(3):
        chain.append("telemetry", {"i": i})
    forged = _forge_rebuilt_chain(_lines(chain), 1, {"i": 999})
    _write(chain, forged)
    chain._write_tip(forged[-1]["seq"], forged[-1]["hash"])  # attacker also fixes the tip
    result = chain.verify()
    assert result["ok"] is False
    assert result["broken_at"] == 2
    assert result["detail"] == "invalid signature"
    assert result["fully_signed"] is False


def test_unsigned_chain_rebuild_is_undetectable_without_signatures(tmp_path: Path):
    """Documents why P1-3 exists: a v1 chain can be rewritten consistently."""
    chain = EvidenceChain(tmp_path, "s")
    for i in range(3):
        chain.append("telemetry", {"i": i})
    forged = _forge_rebuilt_chain(_lines(chain), 1, {"i": 999})
    _write(chain, forged)
    chain._write_tip(forged[-1]["seq"], forged[-1]["hash"])
    result = chain.verify()
    assert result["ok"] is True
    assert result["signatures"] == "none"
    assert result["fully_signed"] is False


def test_downgrade_to_unsigned_after_signed_fails(tmp_path: Path):
    signer = Signer.generate()
    chain = EvidenceChain(tmp_path, "s", signer=signer)
    chain.append("boot", {})
    chain.append("telemetry", {"i": 1})
    records = _lines(chain)
    last = records[-1]
    for key in ("sig", "key_id"):
        last.pop(key)
    last["schema_version"] = 1
    _rehash(last)
    _write(chain, records)
    chain._write_tip(last["seq"], last["hash"])
    result = chain.verify()
    assert result["ok"] is False
    assert "downgrade" in result["detail"]


def test_legacy_unsigned_prefix_then_signed_records_verify(tmp_path: Path):
    legacy = EvidenceChain(tmp_path, "s")
    legacy.append("boot", {"legacy": True})
    signer = Signer.generate()
    upgraded = EvidenceChain(tmp_path, "s", signer=signer)
    upgraded.append("boot", {"legacy": False})
    result = upgraded.verify()
    assert result["ok"] is True
    assert result["signed_records"] == 1
    assert result["unsigned_records"] == 1
    assert result["fully_signed"] is False


def test_unknown_key_fails(tmp_path: Path):
    chain = EvidenceChain(tmp_path, "s", signer=Signer.generate())
    chain.append("boot", {})
    other = Signer.generate()
    verifier = EvidenceChain(tmp_path, "s", trusted_keys={other.key_id: other.public_key})
    result = verifier.verify()
    assert result["ok"] is False
    assert "unknown signing key" in result["detail"]


def test_verifier_without_keys_reports_unchecked(tmp_path: Path):
    EvidenceChain(tmp_path, "s", signer=Signer.generate()).append("boot", {})
    result = EvidenceChain(tmp_path, "s").verify()
    assert result["ok"] is True
    assert result["signatures"] == "unchecked"
    assert result["fully_signed"] is False


def test_key_rotation_with_both_keys_trusted(tmp_path: Path):
    old, new = Signer.generate(), Signer.generate()
    EvidenceChain(tmp_path, "s", signer=old).append("boot", {"k": "old"})
    rotated = EvidenceChain(tmp_path, "s", signer=new, trusted_keys={old.key_id: old.public_key})
    rotated.append("boot", {"k": "new"})
    result = rotated.verify()
    assert result["ok"] is True
    assert result["fully_signed"] is True


def test_missing_signature_on_v2_record_fails(tmp_path: Path):
    chain = EvidenceChain(tmp_path, "s", signer=Signer.generate())
    chain.append("boot", {})
    records = _lines(chain)
    records[0].pop("sig")
    _write(chain, records)
    result = chain.verify()
    assert result["ok"] is False
    assert "missing sig" in result["detail"]


def test_key_file_created_with_0600_and_reloaded(tmp_path: Path):
    key_path = tmp_path / "keys" / "k.pem"
    first = Signer.load_or_create(key_path)
    mode = stat.S_IMODE(os.stat(key_path).st_mode)
    assert mode == 0o600
    second = Signer.load_or_create(key_path)
    assert first.key_id == second.key_id


def test_unsigned_record_dict_shape_is_unchanged(tmp_path: Path):
    rec = EvidenceChain(tmp_path, "s").append("boot", {})
    assert set(rec.to_dict()) == {"seq", "ts", "kind", "sensor_id", "body", "prev_hash", "hash", "schema_version"}


def test_pubkey_endpoint_verifies_api_written_records():
    import main

    client = TestClient(main.app)
    pub = client.get("/api/evidence/pubkey").json()
    assert pub["signing"] is True
    assert pub["key_id"] == main.signer.key_id
    rec = main.chain.append("test", {"probe": True})
    key = load_public_key_b64(pub["public_key"])
    assert verify_signature(key, rec.hash, rec.sig)
