from titan.telemetry import RfSample, SampleBuffer, _utc


def test_buffer_accepts_observed_samples():
    buf = SampleBuffer(capacity=10)
    for d in ("cellular", "wifi", "d2d", "transport"):
        buf.push(RfSample(domain=d, sensor_id="s1", ts=_utc(), metrics={"observed": True}))
    stats = buf.stats()
    assert stats["buffered"] == 4
    assert set(stats["by_domain"]) == {"cellular", "wifi", "d2d", "transport"}
    wifi = buf.recent(10, domain="wifi")
    assert len(wifi) == 1
    assert wifi[0]["metrics"]["observed"] is True
