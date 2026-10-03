from titan.telemetry import SampleBuffer, synthetic_sample


def test_synthetic_and_buffer():
    buf = SampleBuffer(capacity=10)
    for d in ("cellular", "wifi", "d2d", "transport"):
        buf.push(synthetic_sample(d, "s1"))
    stats = buf.stats()
    assert stats["buffered"] == 4
    assert set(stats["by_domain"]) == {"cellular", "wifi", "d2d", "transport"}
    wifi = buf.recent(10, domain="wifi")
    assert len(wifi) == 1 and wifi[0]["metrics"]["demo"] is True
