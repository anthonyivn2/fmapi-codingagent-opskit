"""Tests for CLI flag validation using Typer CliRunner."""

from __future__ import annotations

from typer.testing import CliRunner

from fmapi_opskit.cli import app

runner = CliRunner()


def test_cli_help_shows_subcommands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
    assert "status" in result.output, f"'status' not found in help output: {result.output}"
    assert "doctor" in result.output, f"'doctor' not found in help output: {result.output}"


def test_cli_version_shows_version_string():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, f"Expected exit 0, got {result.exit_code}: {result.output}"
    assert "fmapi-codingagent-opskit" in result.output, (
        f"Version string missing from output: {result.output}"
    )


def test_cli_verbose_and_quiet_mutually_exclusive():
    result = runner.invoke(app, ["--verbose", "--quiet", "status"])
    assert result.exit_code != 0, "--verbose + --quiet should be rejected but exited 0"


def test_cli_config_and_config_url_mutually_exclusive():
    result = runner.invoke(app, ["--config", "a.json", "--config-url", "https://x.com/b.json"])
    assert result.exit_code != 0, "--config + --config-url should be rejected but exited 0"


def test_cli_workspace_id_requires_ai_gateway():
    result = runner.invoke(app, ["--workspace-id", "123"])
    assert result.exit_code != 0, (
        "--workspace-id without --ai-gateway should be rejected but exited 0"
    )


def test_cli_workspace_id_non_numeric_rejected():
    result = runner.invoke(app, ["--workspace-id", "abc", "--ai-gateway"])
    assert result.exit_code != 0, "Non-numeric --workspace-id should be rejected but exited 0"
    assert "numeric" in result.output.lower(), (
        f"Expected 'numeric' in error output, got: {result.output}"
    )


def test_cli_dry_run_with_subcommand_rejected():
    result = runner.invoke(app, ["--dry-run", "status"])
    assert result.exit_code != 0, "--dry-run with subcommand should be rejected but exited 0"
