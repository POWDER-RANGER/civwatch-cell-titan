import pytest
from pydantic import ValidationError

from titan.schemas.api import CaptureIn, SampleIn


def test_sample_rejects_extra_fields():
    with pytest.raises(ValidationError):
        SampleIn(domain="wifi", metrics={}, unexpected=True)


def test_sample_rejects_nested_metrics():
    with pytest.raises(ValidationError):
        SampleIn(domain="wifi", metrics={"x": {"nested": 1}})


def test_sample_ok():
    s = SampleIn(domain="cellular", metrics={"rsrp_dbm": -90, "observed": True})
    assert s.domain == "cellular"


def test_capture_bounds():
    c = CaptureIn(sensor_id="adb-x")
    assert c.domains == ["cellular", "wifi"]
