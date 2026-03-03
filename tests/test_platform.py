"""Tests for platform detection and install hints."""

from __future__ import annotations

from fmapi_opskit.core import PlatformInfo, install_hint


def test_headless_false_for_wsl():
    pi = PlatformInfo(os_type="Linux", is_wsl=True, wsl_version="2", wsl_distro="Ubuntu")
    assert pi.is_headless is False, (
        "WSL can open a browser via Windows interop, should not be headless"
    )


def test_headless_true_for_ssh_no_display(monkeypatch):
    monkeypatch.setenv("SSH_CONNECTION", "1.2.3.4 5678 5.6.7.8 22")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    pi = PlatformInfo(os_type="Linux", is_wsl=False, wsl_version="", wsl_distro="")
    assert pi.is_headless is True, "SSH without DISPLAY should be headless"


def test_headless_false_for_ssh_with_display(monkeypatch):
    monkeypatch.setenv("SSH_CONNECTION", "1.2.3.4 5678 5.6.7.8 22")
    monkeypatch.setenv("DISPLAY", ":0")
    pi = PlatformInfo(os_type="Linux", is_wsl=False, wsl_version="", wsl_distro="")
    assert pi.is_headless is False, "SSH with X11 forwarding (DISPLAY set) should not be headless"


def test_headless_false_when_no_ssh(monkeypatch):
    monkeypatch.delenv("SSH_CONNECTION", raising=False)
    monkeypatch.delenv("SSH_TTY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    pi = PlatformInfo(os_type="Linux", is_wsl=False, wsl_version="", wsl_distro="")
    assert pi.is_headless is False, "No SSH session means not headless (local terminal)"


def test_install_hint_jq_linux(agent_config):
    pi = PlatformInfo(os_type="Linux", is_wsl=False, wsl_version="", wsl_distro="")
    hint = install_hint("jq", pi, agent_config)
    assert "apt-get" in hint, f"Linux jq hint should include 'apt-get', got: {hint}"


def test_install_hint_jq_darwin(agent_config):
    pi = PlatformInfo(os_type="Darwin", is_wsl=False, wsl_version="", wsl_distro="")
    hint = install_hint("jq", pi, agent_config)
    assert "brew" in hint, f"macOS jq hint should include 'brew', got: {hint}"


def test_install_hint_databricks_linux(agent_config):
    pi = PlatformInfo(os_type="Linux", is_wsl=False, wsl_version="", wsl_distro="")
    hint = install_hint("databricks", pi, agent_config)
    assert "curl" in hint, f"Linux databricks hint should include 'curl', got: {hint}"


def test_install_hint_agent_cli(agent_config):
    pi = PlatformInfo(os_type="Darwin", is_wsl=False, wsl_version="", wsl_distro="")
    hint = install_hint(agent_config.cli_cmd, pi, agent_config)
    assert hint == agent_config.cli_install_cmd, (
        f"Expected '{agent_config.cli_install_cmd}', got '{hint}'"
    )
