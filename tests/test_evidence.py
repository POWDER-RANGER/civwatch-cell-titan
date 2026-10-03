import json
import threading
from pathlib import Path

import pytest

from titan.evidence import EvidenceChain, GENESIS_HASH, canonical_material, digest


def test_chain_append_and_verify(tmp_path: Path):
    chain = EvidenceChain(tmp_path, "test-sensor")
    a = chain.append("boot", {"v": 1})
    b = chain.append("telemetry", {"domain": "wifi", "rssi": -60})
    assert a.seq == 1 and b.seq == 2
    assert a.prev_hash == GENESIS_HASH
    assert b.prev_hash == a.hash
    assert chain.verify()["ok"] is True
    assert chain.verify()["length"] == 2
    assert len(chain.tail(10)) == 2


def test_tamper_detected(tmp_path: Path):
    chain = EvidenceChain(tmp_path, "t")
    chain.append("boot", {})
    chain.append("telemetry", {"x": 1})
    text = chain.path.read_text(encoding="utf-8")
    lines = text.splitlines()
    lines[1] = lines[1].replace('"x":1', '"x":99')
    chain.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = chain.verify()
    assert result["ok"] is False
    assert result["broken_at"] == 2


def test_canonical_is_stable():
    m1 = canonical_material(
        seq=1,
        ts="2026-01-01T00:00:00+00:00",
        kind="boot",
        sensor_id="s",
        body={"b": 1, "a": 2},
        prev_hash=GENESIS_HASH,
    )
    m2 = canonical_material(
        seq=1,
        ts="2026-01-01T00:00:00+00:00",
        kind="boot",
        sensor_id="s",
        body={"a": 2, "b": 1},
        prev_hash=GENESIS_HASH,
    )
    assert m1 == m2
    assert digest(m1) == digest(m2)


def test_reject_bad_sensor_id(tmp_path: Path):
    with pytest.raises(ValueError):
        EvidenceChain(tmp_path, "../evil")


def test_concurrent_appends(tmp_path: Path):
    chain = EvidenceChain(tmp_path, "concurrent")
    errors: list[BaseException] = []

    def worker(n: int) -> None:
        try:
            for i in range(25):
                chain.append("t", {"n": n, "i": i})
        except BaseException as ex:  # noqa: BLE001
            errors.append(ex)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    v = chain.verify()
    assert v["ok"] is True
    assert v["length"] == 100


def test_seq_must_be_dense(tmp_path: Path):
    chain = EvidenceChain(tmp_path, "dense")
    chain.append("a", {})
    chain.append("b", {})
    lines = chain.path.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[1])
    rec["seq"] = 99
    lines[1] = json.dumps(rec, separators=(",", ":"))
    chain.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert chain.verify()["ok"] is False
