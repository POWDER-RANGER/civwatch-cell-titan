from pathlib import Path

from titan.evidence import EvidenceChain


def test_chain_append_and_verify(tmp_path: Path):
    chain = EvidenceChain(tmp_path, "test-sensor")
    a = chain.append("boot", {"v": 1})
    b = chain.append("telemetry", {"domain": "wifi", "rssi": -60})
    assert a.seq == 1 and b.seq == 2
    assert b.prev_hash == a.hash
    assert chain.verify() == {"ok": True, "length": 2, "broken_at": None}
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
