import pytest


def test_assert_boot_auth_fails_without_token(titan_env):
    titan_env(CELL_TITAN_ENV="production", TITAN_API_TOKEN="", REQUIRE_AUTH="false")
    from titan.auth import assert_boot_auth

    with pytest.raises(RuntimeError, match="refuse-to-start"):
        assert_boot_auth()


def test_assert_boot_auth_passes_with_token(titan_env):
    titan_env(CELL_TITAN_ENV="production", TITAN_API_TOKEN="x" * 32)
    from titan.auth import assert_boot_auth

    assert_boot_auth()


def test_settings_reload_is_in_place(titan_env):
    """Guards the regression: modules holding a settings reference must see changes."""
    import main
    from titan.config import settings

    titan_env(REQUIRE_AUTH="true", TITAN_API_TOKEN="abc")
    assert main.settings is settings
    assert main.settings.require_auth is True
    assert main.settings.api_token == "abc"


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
