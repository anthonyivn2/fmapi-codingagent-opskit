"""Tests for CLI flag validation using Typer CliRunner."""

from __future__ import annotations

from typer.testing import CliRunner

from fmapi_opskit.cli import app

runner = CliRunner()


def test_help_runs_without_error():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "setup-fmapi-claudecode" in result.output or "Configure" in result.output


def test_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "fmapi-codingagent-opskit" in result.output


def test_verbose_and_quiet_mutually_exclusive():
    result = runner.invoke(app, ["--verbose", "--quiet", "status"])
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output


def test_config_and_config_url_mutually_exclusive():
    result = runner.invoke(app, ["--config", "a.json", "--config-url", "https://x.com/b.json"])
    assert result.exit_code != 0
    assert "Cannot use both" in result.output


def test_workspace_id_without_ai_gateway():
    result = runner.invoke(app, ["--workspace-id", "123"])
    assert result.exit_code != 0
    assert "--ai-gateway" in result.output


def test_workspace_id_non_numeric():
    result = runner.invoke(app, ["--ai-gateway", "--workspace-id", "abc"])
    assert result.exit_code != 0
    assert "numeric" in result.output


def test_dry_run_with_subcommand():
    result = runner.invoke(app, ["--dry-run", "status"])
    assert result.exit_code != 0
    assert "cannot be combined" in result.output


def test_subcommands_listed_in_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("status", "doctor", "reauth", "list-models", "validate-models", "uninstall"):
        assert cmd in result.output
