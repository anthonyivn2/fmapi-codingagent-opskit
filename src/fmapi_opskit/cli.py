"""Typer CLI app — entry point for setup-fmapi-claudecode."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from fmapi_opskit.agents.claudecode import ClaudeCodeAdapter
from fmapi_opskit.config.loader import (
    ConfigError,
    FileConfig,
    load_config_file,
    load_config_url,
)
from fmapi_opskit.core import detect_platform, find_clone_dir, get_version
from fmapi_opskit.ui.console import init_console

app = typer.Typer(
    name="setup-fmapi-claudecode",
    help="Configure Claude Code to use Databricks Foundation Model API (FMAPI).",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)

# Shared state passed between callback and subcommands
_state: dict = {}


def _get_adapter() -> ClaudeCodeAdapter:
    return _state.get("adapter") or ClaudeCodeAdapter()


def _get_platform():
    return _state.get("platform") or detect_platform()


def _get_script_dir() -> Path:
    """Get the repo root (for templates, plugins, etc.)."""
    return find_clone_dir() or Path.home() / ".fmapi-codingagent-setup"


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"fmapi-codingagent-opskit {get_version()}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    # Global flags
    verbose: Annotated[bool, typer.Option("--verbose", help="Show debug-level output.")] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress informational output.")
    ] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output.")] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would happen without making changes."),
    ] = False,
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = None,
    # Setup flags (used when no subcommand)
    host: Annotated[str | None, typer.Option("--host", help="Databricks workspace URL.")] = None,
    profile: Annotated[
        str | None, typer.Option("--profile", help="Databricks CLI profile name.")
    ] = None,
    model: Annotated[str | None, typer.Option("--model", help="Primary model.")] = None,
    opus: Annotated[str | None, typer.Option("--opus", help="Opus model.")] = None,
    sonnet: Annotated[str | None, typer.Option("--sonnet", help="Sonnet model.")] = None,
    haiku: Annotated[str | None, typer.Option("--haiku", help="Haiku model.")] = None,
    ttl: Annotated[
        str | None, typer.Option("--ttl", help="Token refresh interval in minutes.")
    ] = None,
    settings_location: Annotated[
        str | None,
        typer.Option("--settings-location", help="Settings: home, cwd, or path."),
    ] = None,
    ai_gateway: Annotated[
        bool,
        typer.Option("--ai-gateway", help="Use AI Gateway v2 for API routing (beta)."),
    ] = False,
    workspace_id: Annotated[
        str | None,
        typer.Option("--workspace-id", help="Databricks workspace ID for AI Gateway."),
    ] = None,
    config: Annotated[
        str | None, typer.Option("--config", help="Load config from a local JSON file.")
    ] = None,
    config_url: Annotated[
        str | None,
        typer.Option("--config-url", help="Load config from a remote JSON URL."),
    ] = None,
) -> None:
    """Configure Claude Code to use Databricks Foundation Model API."""
    # Validation: mutually exclusive flags
    if verbose and quiet:
        typer.echo("Error: --verbose and --quiet are mutually exclusive.", err=True)
        raise typer.Exit(1)

    if config and config_url:
        typer.echo("Error: Cannot use both --config and --config-url. Choose one.", err=True)
        raise typer.Exit(1)

    if workspace_id and not ai_gateway:
        typer.echo("Error: --workspace-id requires --ai-gateway to be set.", err=True)
        raise typer.Exit(1)

    if workspace_id and not workspace_id.isdigit():
        typer.echo(f"Error: --workspace-id must be numeric. Got: {workspace_id}", err=True)
        raise typer.Exit(1)

    if dry_run and ctx.invoked_subcommand is not None:
        typer.echo(
            f"Error: --dry-run cannot be combined with {ctx.invoked_subcommand}. "
            "It only applies to setup.",
            err=True,
        )
        raise typer.Exit(1)

    # Initialize console
    init_console(no_color=no_color, quiet=quiet, verbose=verbose)

    # Initialize adapter and platform
    adapter = ClaudeCodeAdapter()
    platform_info = detect_platform()

    # Load config file if specified
    file_cfg = FileConfig()
    if config or config_url:
        try:
            file_cfg = (
                load_config_file(config) if config else load_config_url(config_url)  # type: ignore[arg-type]
            )
        except ConfigError as e:
            from fmapi_opskit.ui.logging import error

            error(str(e))
            sys.exit(1)

    # Determine non-interactive mode
    non_interactive = bool(host or config or config_url or dry_run)

    # Store state
    _state.update(
        {
            "adapter": adapter,
            "platform": platform_info,
            "file_cfg": file_cfg,
            "non_interactive": non_interactive,
            "dry_run": dry_run,
            "cli_host": host or "",
            "cli_profile": profile or "",
            "cli_model": model or "",
            "cli_opus": opus or "",
            "cli_sonnet": sonnet or "",
            "cli_haiku": haiku or "",
            "cli_ttl": ttl or "",
            "cli_settings_location": settings_location or "",
            "cli_ai_gateway": "true" if ai_gateway else "",
            "cli_workspace_id": workspace_id or "",
        }
    )

    # If no subcommand, run setup
    if ctx.invoked_subcommand is None:
        from fmapi_opskit.setup.workflow import do_setup

        do_setup(
            adapter,
            platform_info,
            cli_host=host or "",
            cli_profile=profile or "",
            cli_model=model or "",
            cli_opus=opus or "",
            cli_sonnet=sonnet or "",
            cli_haiku=haiku or "",
            cli_ttl=ttl or "",
            cli_settings_location=settings_location or "",
            cli_ai_gateway="true" if ai_gateway else "",
            cli_workspace_id=workspace_id or "",
            file_cfg=file_cfg,
            non_interactive=non_interactive,
            dry_run=dry_run,
            script_dir=_get_script_dir(),
        )


@app.command()
def status() -> None:
    """Show FMAPI configuration health dashboard."""
    from fmapi_opskit.commands.status import do_status

    do_status(_get_adapter())


@app.command()
def doctor() -> None:
    """Run comprehensive diagnostics."""
    from fmapi_opskit.commands.doctor import do_doctor

    do_doctor(_get_adapter(), _get_platform())


@app.command()
def reauth() -> None:
    """Re-authenticate Databricks OAuth session."""
    from fmapi_opskit.commands.reauth import do_reauth

    do_reauth(_get_adapter(), _get_platform())


@app.command(name="list-models")
def list_models() -> None:
    """List all serving endpoints in the workspace."""
    from fmapi_opskit.commands.list_models import do_list_models

    do_list_models(_get_adapter())


@app.command(name="validate-models")
def validate_models() -> None:
    """Validate configured models exist and are ready."""
    from fmapi_opskit.commands.validate_models import do_validate_models

    do_validate_models(_get_adapter())


@app.command()
def uninstall() -> None:
    """Remove all FMAPI artifacts."""
    from fmapi_opskit.commands.uninstall import do_uninstall

    do_uninstall(_get_adapter())


@app.command(name="install-skills")
def install_skills() -> None:
    """Install FMAPI slash command skills to ~/.claude/skills/."""
    from fmapi_opskit.commands.skills import do_install_skills

    do_install_skills(_get_adapter(), _get_script_dir())


@app.command(name="uninstall-skills")
def uninstall_skills() -> None:
    """Remove FMAPI slash command skills from ~/.claude/skills/."""
    from fmapi_opskit.commands.skills import do_uninstall_skills

    do_uninstall_skills(_get_adapter())


@app.command(name="self-update")
def self_update() -> None:
    """Update to the latest version."""
    from fmapi_opskit.commands.self_update import do_self_update

    do_self_update(_get_script_dir())


@app.command()
def reinstall() -> None:
    """Rerun setup using previously saved configuration."""
    adapter = _get_adapter()
    platform_info = _get_platform()

    from fmapi_opskit.auth import has_databricks_cli
    from fmapi_opskit.config.discovery import discover_config
    from fmapi_opskit.setup.workflow import do_setup
    from fmapi_opskit.setup.writer import migrate_helper_if_needed
    from fmapi_opskit.ui import logging as log

    if not has_databricks_cli():
        log.error("Databricks CLI is required for reinstall.")
        sys.exit(1)

    cfg = discover_config(adapter)
    if not cfg.found or not cfg.host:
        log.error("No existing FMAPI configuration found. Run setup first (without reinstall).")
        sys.exit(1)

    c = adapter.config
    log.info(
        f"Re-installing with existing config ({cfg.host}, "
        f"profile: {cfg.profile or c.default_profile})"
    )

    migrate_helper_if_needed(
        adapter,
        helper_file=cfg.helper_file,
        host=cfg.host,
        profile=cfg.profile or c.default_profile,
        reason="reinstall",
    )

    do_setup(
        adapter,
        platform_info,
        cli_host=cfg.host,
        cli_profile=cfg.profile or c.default_profile,
        cli_model=cfg.model or c.default_model,
        cli_opus=cfg.opus or c.default_opus,
        cli_sonnet=cfg.sonnet or c.default_sonnet,
        cli_haiku=cfg.haiku or c.default_haiku,
        cli_ttl=cfg.ttl or "55",
        cli_settings_location="",
        cli_ai_gateway=cfg.ai_gateway or "false",
        cli_workspace_id=cfg.workspace_id or "",
        file_cfg=FileConfig(),
        non_interactive=True,
        dry_run=False,
        script_dir=_get_script_dir(),
    )


def run() -> None:
    """Entry point wrapper for pyproject.toml console_scripts."""
    app()


if __name__ == "__main__":
    run()
