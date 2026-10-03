import importlib

import pytest


def test_assert_boot_auth_fails_without_token(monkeypatch):
    monkeypatch.setenv("CELL_TITAN_ENV", "production")
    monkeypatch.setenv("TITAN_API_TOKEN", "")
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    import titan.config as cfg

    importlib.reload(cfg)
    from titan.auth import assert_boot_auth

    with pytest.raises(RuntimeError, match="refuse-to-start"):
        assert_boot_auth()


def test_tokens_equal_constant_time():
    from titan.auth import tokens_equal

    assert tokens_equal("abcd", "abcd") is True
    assert tokens_equal("abcd", "abce") is False
    assert tokens_equal("short", "longer_token") is False
    assert tokens_equal("", "x") is False


def test_tokens_equal_unicode():
    from titan.auth import tokens_equal

    assert tokens_equal("café-token", "café-token") is True
    assert tokens_equal("café-token", "cafe-token") is False
