"""Tests for install.sh behavior and compatibility guards."""

from __future__ import annotations

from pathlib import Path


def _install_script_text() -> str:
    return (Path(__file__).resolve().parents[1] / "install.sh").read_text()


def test_install_script_uses_cache_busting_tool_install():
    script = _install_script_text()
    assert 'uv tool install "$INSTALL_DIR" --force --reinstall --no-cache' in script, (
        "install.sh should force a fresh uv tool reinstall to avoid stale cached helper templates"
    )


def test_install_script_does_not_execute_setup_command():
    script = _install_script_text()
    assert "if setup-fmapi-claudecode" not in script, (
        "install.sh should not execute setup-fmapi-claudecode during install/update"
    )
    assert "exec setup-fmapi-claudecode" not in script, (
        "install.sh should not exec setup-fmapi-claudecode automatically"
    )


def test_install_script_does_not_offer_agent_flag():
    script = _install_script_text()
    assert "--agent" not in script, "install.sh should not include an auto-run --agent mode"
