"""Tests for CLI flag validation using Typer CliRunner."""

from __future__ import annotations

from typer.testing import CliRunner

from fmapi_opskit.cli import app

runner = CliRunner()


def test_cli_flags():
    # help lists subcommands
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "status" in r.output and "doctor" in r.output

    # mutually exclusive flags rejected
    r = runner.invoke(app, ["--verbose", "--quiet", "status"])
    assert r.exit_code != 0

    r = runner.invoke(app, ["--config", "a.json", "--config-url", "https://x.com/b.json"])
    assert r.exit_code != 0

    # workspace-id requires ai-gateway
    r = runner.invoke(app, ["--workspace-id", "123"])
    assert r.exit_code != 0
