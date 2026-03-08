"""Tests for platform detection and install hints."""

from __future__ import annotations

from fmapi_opskit.core import PlatformInfo, install_hint


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
