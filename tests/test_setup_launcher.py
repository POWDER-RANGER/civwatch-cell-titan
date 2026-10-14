"""One-click launcher behaviour (setup_titan.py), filesystem and processes faked."""
from __future__ import annotations

import subprocess

import pytest

import setup_titan


@pytest.fixture
def launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(setup_titan, "ROOT", tmp_path)
    monkeypatch.setattr(setup_titan, "ENV", tmp_path / ".env")
    monkeypatch.setattr(setup_titan, "VENV", tmp_path / ".titan-venv")
    monkeypatch.setattr(setup_titan, "STAMP", tmp_path / ".titan-venv" / ".titan-requirements.sha256")
    (tmp_path / "requirements.txt").write_text("fastapi==0.115.6\n")
    return tmp_path


def _token(env_text: str) -> str:
    return [l for l in env_text.splitlines() if l.startswith("TITAN_API_TOKEN=")][-1].split("=", 1)[1]


def test_new_env_has_token(launcher):
    setup_titan.ensure_env()
    assert len(_token((launcher / ".env").read_text())) >= 32


def test_env_copied_from_example_is_repaired(launcher):
    (launcher / ".env").write_text("HOST=127.0.0.1\nTITAN_API_TOKEN=\nADB_ENABLED=true\n")
    setup_titan.ensure_env()
    text = (launcher / ".env").read_text()
    assert len(_token(text)) >= 32
    assert "HOST=127.0.0.1" in text and "ADB_ENABLED=true" in text


def test_existing_token_is_preserved(launcher):
    (launcher / ".env").write_text("TITAN_API_TOKEN=keep-me\n")
    setup_titan.ensure_env()
    assert _token((launcher / ".env").read_text()) == "keep-me"


def test_unsupported_python_switches_to_supported(monkeypatch):
    monkeypatch.setattr(setup_titan, "SUPPORTED", ((2, 7),))
    monkeypatch.delenv("TITAN_SETUP_REEXEC", raising=False)
    monkeypatch.setattr(setup_titan, "_find_supported_python", lambda: "/opt/py313/python")
    seen = {}

    def fake_call(args, env=None):
        seen.update(args=args, env=env)
        return 0

    monkeypatch.setattr(subprocess, "call", fake_call)
    with pytest.raises(SystemExit) as ex:
        setup_titan.ensure_python()
    assert ex.value.code == 0
    assert seen["args"][0] == "/opt/py313/python"
    assert seen["env"]["TITAN_SETUP_REEXEC"] == "1"


def test_unsupported_python_without_alternative_explains(monkeypatch, capsys):
    monkeypatch.setattr(setup_titan, "SUPPORTED", ((2, 7),))
    monkeypatch.setattr(setup_titan, "_find_supported_python", lambda: None)
    with pytest.raises(SystemExit):
        setup_titan.ensure_python()
    assert "Python 3.11, 3.12 or 3.13" in capsys.readouterr().out


def test_reexec_loop_is_prevented(monkeypatch):
    monkeypatch.setattr(setup_titan, "SUPPORTED", ((2, 7),))
    monkeypatch.setenv("TITAN_SETUP_REEXEC", "1")
    monkeypatch.setattr(setup_titan, "_find_supported_python", lambda: pytest.fail("must not search again"))
    with pytest.raises(SystemExit):
        setup_titan.ensure_python()


def test_unchanged_requirements_skip_network(launcher, monkeypatch):
    py = setup_titan.pyexe()
    py.parent.mkdir(parents=True)
    py.write_text("")
    setup_titan.STAMP.write_text(setup_titan._requirements_digest())
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("pip must not run"))
    setup_titan.ensure_venv()


def test_offline_install_fails_with_plain_message(launcher, monkeypatch, capsys):
    py = setup_titan.pyexe()
    py.parent.mkdir(parents=True)
    py.write_text("")

    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, a[0])

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(SystemExit):
        setup_titan.ensure_venv()
    out = capsys.readouterr().out
    assert "internet connection" in out and "Traceback" not in out
