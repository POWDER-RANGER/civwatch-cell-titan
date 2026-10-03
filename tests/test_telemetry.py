import random

from titan.telemetry import SampleBuffer, synthetic_sample


def test_synthetic_and_buffer():
    buf = SampleBuffer(capacity=10)
    for d in ("cellular", "wifi", "d2d", "transport"):
        buf.push(synthetic_sample(d, "s1", rng=random.Random(0)))
    stats = buf.stats()
    assert stats["buffered"] == 4
    assert set(stats["by_domain"]) == {"cellular", "wifi", "d2d", "transport"}
    wifi = buf.recent(10, domain="wifi")
    assert len(wifi) == 1 and wifi[0]["metrics"]["demo"] is True


def test_deterministic_rng():
    a = synthetic_sample("wifi", "s", rng=random.Random(42))
    b = synthetic_sample("wifi", "s", rng=random.Random(42))
    assert a.metrics["rssi_dbm"] == b.metrics["rssi_dbm"]
