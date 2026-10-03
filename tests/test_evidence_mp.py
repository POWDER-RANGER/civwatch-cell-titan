"""Multi-process lock + truncation detection."""
from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

from titan.evidence import EvidenceChain


def _worker(root: str, sensor: str, n: int, q: mp.Queue) -> None:
    try:
        chain = EvidenceChain(root, sensor)
        for i in range(n):
            chain.append("t", {"i": i})
        q.put(None)
    except Exception as ex:  # noqa: BLE001
        q.put(str(ex))


def test_multiprocess_appends(tmp_path: Path):
    sensor = "mp-sensor"
    q: mp.Queue = mp.Queue()
    procs = [mp.Process(target=_worker, args=(str(tmp_path), sensor, 25, q)) for _ in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)
        assert p.exitcode == 0
    errs = [q.get() for _ in procs]
    assert all(e is None for e in errs)
    chain = EvidenceChain(tmp_path, sensor)
    v = chain.verify()
    assert v["ok"] is True
    assert v["length"] == 100


def test_truncation_detected(tmp_path: Path):
    chain = EvidenceChain(tmp_path, "trunc")
    for i in range(5):
        chain.append("t", {"i": i})
    assert chain.verify()["ok"] is True
    lines = chain.path.read_text(encoding="utf-8").splitlines()
    chain.path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8")
    v = chain.verify()
    assert v["ok"] is False
    assert v.get("broken_at") == "truncated" or v.get("detail")
