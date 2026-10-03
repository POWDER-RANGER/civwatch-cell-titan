from titan.adb_collect import collect_cellular, collect_wifi, collect_device_props


def test_collect_without_device_is_safe():
    c = collect_cellular("no-such-serial")
    assert c.get("demo") is False
    assert "available" in c or "note" in c or "source" in c
    w = collect_wifi("no-such-serial")
    assert w.get("source") == "adb"
    p = collect_device_props("no-such-serial")
    assert "serial" in p
