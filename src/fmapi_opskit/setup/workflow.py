"""Setup workflow orchestrator — do_setup."""

from __future__ import annotations

import sys
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth import authenticate, cleanup_legacy_cache
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.config.models import FileConfig, FmapiConfig
from fmapi_opskit.core import PlatformInfo
from fmapi_opskit.network import (
    build_base_url,
    detect_workspace_id,
    fetch_endpoints,
    filter_agent_endpoints,
)
from fmapi_opskit.setup.gather import (
    gather_config_models,
    gather_config_pre_auth,
)
from fmapi_opskit.setup.install_deps import install_dependencies
from fmapi_opskit.setup.smoke_test import run_smoke_test
from fmapi_opskit.setup.writer import (
    cleanup_legacy_hooks,
    migrate_helper_if_needed,
    write_helper,
    write_settings,
)
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console, get_verbosity
from fmapi_opskit.ui.dry_run import display_dry_run_plan
from fmapi_opskit.ui.prompts import select_option
from fmapi_opskit.ui.tables import display_agent_endpoints


def do_setup(
    adapter: AgentAdapter,
    platform_info: PlatformInfo,
    *,
    cli_host: str,
    cli_profile: str,
    cli_model: str,
    cli_opus: str,
    cli_sonnet: str,
    cli_haiku: str,
    cli_ttl: str,
    cli_settings_location: str,
    cli_ai_gateway: str,
    cli_workspace_id: str,
    file_cfg: FileConfig,
    non_interactive: bool,
    dry_run: bool,
    script_dir: Path,
) -> None:
    """Run the full setup workflow."""
    console = get_console()
    c = adapter.config
    console.print(f"\n[bold]  {c.name} x Databricks FMAPI Setup[/bold]\n")

    # Fast-path: existing install can run reinstall flow
    if not non_interactive and not dry_run:
        cfg = discover_config(adapter)
        if cfg.found and cfg.host and _show_reuse_summary(adapter, cfg):
            migrate_helper_if_needed(
                adapter,
                helper_file=cfg.helper_file,
                host=cfg.host,
                profile=cfg.profile or c.default_profile,
                reason="setup (existing installation)",
            )
            non_interactive = True
            cli_host = cli_host or cfg.host
            cli_profile = cli_profile or cfg.profile or c.default_profile
            cli_ttl = cli_ttl or cfg.ttl or "55"
            cli_model = cli_model or cfg.model or c.default_model
            cli_opus = cli_opus or cfg.opus or c.default_opus
            cli_sonnet = cli_sonnet or cfg.sonnet or c.default_sonnet
            cli_haiku = cli_haiku or cfg.haiku or c.default_haiku
            cli_ai_gateway = cli_ai_gateway or cfg.ai_gateway or "false"
            cli_workspace_id = cli_workspace_id or cfg.workspace_id or ""
            if not cli_settings_location and cfg.settings_file:
                cfg_base = cfg.settings_file.rsplit(f"/{c.settings_dir}/{c.settings_filename}", 1)[
                    0
                ]
                cli_settings_location = "home" if cfg_base == str(Path.home()) else cfg_base

    cfg = discover_config(adapter) if not dry_run else FmapiConfig()

    gather = gather_config_pre_auth(
        adapter,
        cfg,
        file_cfg,
        cli_host=cli_host,
        cli_profile=cli_profile,
        cli_ttl=cli_ttl,
        cli_ai_gateway=cli_ai_gateway,
        cli_workspace_id=cli_workspace_id,
        cli_settings_location=cli_settings_location,
        cli_model=cli_model,
        cli_opus=cli_opus,
        cli_sonnet=cli_sonnet,
        cli_haiku=cli_haiku,
        non_interactive=non_interactive,
    )

    if dry_run:
        models = gather_config_models(
            gather,
            cli_model=cli_model,
            cli_opus=cli_opus,
            cli_sonnet=cli_sonnet,
            cli_haiku=cli_haiku,
            non_interactive=True,
        )
        display_dry_run_plan(
            adapter,
            host=gather.host,
            profile=gather.profile,
            model=models.model,
            opus=models.opus,
            sonnet=models.sonnet,
            haiku=models.haiku,
            ttl_ms=gather.ttl_ms,
            settings_file=gather.settings_file,
            helper_file=gather.helper_file,
            ai_gateway_enabled=gather.ai_gateway_enabled,
            pending_workspace_id=gather.pending_workspace_id,
            script_dir=script_dir,
        )
        sys.exit(0)

    install_dependencies(adapter, platform_info)
    authenticate(gather.host, gather.profile, platform_info)
    cleanup_legacy_cache(gather.settings_file.rsplit(f"/{c.settings_dir}", 1)[0])

    # Resolve workspace ID for gateway
    workspace_id = ""
    if gather.ai_gateway_enabled:
        log.heading("Resolving workspace ID")
        if gather.pending_workspace_id:
            workspace_id = gather.pending_workspace_id
            log.success(f"Using workspace ID: {workspace_id}")
        else:
            log.info(f"Detecting workspace ID from {gather.host} ...")
            workspace_id = detect_workspace_id(gather.profile, gather.host)
            if workspace_id:
                log.success(f"Detected workspace ID: {workspace_id}")
            elif non_interactive:
                log.error(
                    "Could not auto-detect workspace ID. Use --workspace-id to provide it manually."
                )
                sys.exit(1)
            else:
                from rich.prompt import Prompt

                console.print("  [warning]WARN[/warning]  Could not auto-detect workspace ID.")
                workspace_id = Prompt.ask(
                    "  [info]?[/info] Databricks workspace ID", console=console
                )
                if not workspace_id:
                    log.error("Workspace ID is required for AI Gateway v2.")
                    sys.exit(1)
                if not workspace_id.isdigit():
                    log.error(f"Workspace ID must be numeric. Got: {workspace_id}")
                    sys.exit(1)

    # Show available endpoints before model selection (interactive only)
    if not non_interactive:
        endpoints = fetch_endpoints(gather.profile)
        if endpoints:
            filtered = filter_agent_endpoints(endpoints, c.endpoint_filter)
            if filtered:
                console.print(f"\n[bold]Available {c.endpoint_title} endpoints[/bold]\n")
                display_agent_endpoints(filtered)
                console.print()

    models = gather_config_models(
        gather,
        cli_model=cli_model,
        cli_opus=cli_opus,
        cli_sonnet=cli_sonnet,
        cli_haiku=cli_haiku,
        non_interactive=non_interactive,
    )

    write_settings(
        adapter,
        settings_file=gather.settings_file,
        helper_file=gather.helper_file,
        host=gather.host,
        model=models.model,
        opus=models.opus,
        sonnet=models.sonnet,
        haiku=models.haiku,
        ttl_ms=gather.ttl_ms,
        ai_gateway_enabled=gather.ai_gateway_enabled,
        workspace_id=workspace_id,
    )

    adapter.ensure_onboarding()

    write_helper(
        adapter,
        helper_file=gather.helper_file,
        host=gather.host,
        profile=gather.profile,
    )

    # Clean up legacy hooks from prior installations (hooks are no longer used)
    cleanup_legacy_hooks(
        settings_file=gather.settings_file,
    )

    run_smoke_test(
        helper_file=gather.helper_file,
        host=gather.host,
        profile=gather.profile,
        model=models.model,
        opus=models.opus,
        sonnet=models.sonnet,
        haiku=models.haiku,
        ai_gateway_enabled=gather.ai_gateway_enabled,
        workspace_id=workspace_id,
    )

    _print_summary(
        adapter,
        host=gather.host,
        profile=gather.profile,
        model=models.model,
        opus=models.opus,
        sonnet=models.sonnet,
        haiku=models.haiku,
        ttl_minutes=gather.ttl_minutes,
        ai_gateway_enabled=gather.ai_gateway_enabled,
        workspace_id=workspace_id,
        helper_file=gather.helper_file,
        settings_file=gather.settings_file,
    )


def _show_reuse_summary(adapter: AgentAdapter, cfg: FmapiConfig) -> bool:
    """Show existing config summary and ask to reuse. Returns True to reuse."""
    console = get_console()
    c = adapter.config

    console.print("\n  [bold]Existing configuration found:[/bold]\n")
    console.print(f"  [dim]Workspace[/dim]  [bold]{cfg.host}[/bold]")
    console.print(f"  [dim]Profile[/dim]    [bold]{cfg.profile or c.default_profile}[/bold]")
    console.print(f"  [dim]TTL[/dim]        [bold]{cfg.ttl or '55'}m[/bold]")
    console.print(f"  [dim]Model[/dim]      [bold]{cfg.model or c.default_model}[/bold]")
    console.print(f"  [dim]Opus[/dim]       [bold]{cfg.opus or c.default_opus}[/bold]")
    console.print(f"  [dim]Sonnet[/dim]     [bold]{cfg.sonnet or c.default_sonnet}[/bold]")
    console.print(f"  [dim]Haiku[/dim]      [bold]{cfg.haiku or c.default_haiku}[/bold]")
    if cfg.ai_gateway == "true":
        console.print("  [dim]Routing[/dim]    [bold]AI Gateway v2 (beta)[/bold]")
        console.print(f"  [dim]Workspace ID[/dim] [bold]{cfg.workspace_id or 'unknown'}[/bold]")
    else:
        console.print("  [dim]Routing[/dim]    [bold]Serving Endpoints (v1)[/bold]")
    console.print(f"  [dim]Settings[/dim]   [bold]{cfg.settings_file}[/bold]")
    console.print()

    choice = select_option(
        "Keep this configuration?",
        [
            ("Yes, reinstall", "re-run setup with existing config"),
            ("No, reconfigure", "start fresh with all prompts"),
        ],
    )
    return choice == 0


def _print_summary(
    adapter: AgentAdapter,
    *,
    host: str,
    profile: str,
    model: str,
    opus: str,
    sonnet: str,
    haiku: str,
    ttl_minutes: str,
    ai_gateway_enabled: bool,
    workspace_id: str,
    helper_file: str,
    settings_file: str,
) -> None:
    """Print the post-setup summary."""
    if get_verbosity() < 1:
        return

    console = get_console()
    c = adapter.config

    console.print("\n[success]  Setup complete![/success]")
    console.print(f"  [dim]Workspace[/dim]  [bold]{host}[/bold]")
    console.print(f"  [dim]Profile[/dim]    [bold]{profile}[/bold]")
    console.print(f"  [dim]Model[/dim]      [bold]{model}[/bold]")
    console.print(f"  [dim]Opus[/dim]       [bold]{opus}[/bold]")
    console.print(f"  [dim]Sonnet[/dim]     [bold]{sonnet}[/bold]")
    console.print(f"  [dim]Haiku[/dim]      [bold]{haiku}[/bold]")

    if ai_gateway_enabled:
        gw_url = build_base_url(host, True, workspace_id)
        console.print("  [dim]Routing[/dim]    [bold]AI Gateway v2 (beta)[/bold]")
        console.print(f"  [dim]Workspace ID[/dim] [bold]{workspace_id}[/bold]")
        console.print(f"  [dim]Base URL[/dim]   [bold]{gw_url}[/bold]")
    else:
        console.print("  [dim]Routing[/dim]    [bold]Serving Endpoints (v1)[/bold]")

    console.print(
        f"  [dim]Auth[/dim]       [bold]OAuth (auto-refresh, {ttl_minutes}m check interval)[/bold]"
    )
    console.print(f"  [dim]Helper[/dim]     [bold]{helper_file}[/bold]")
    console.print(f"  [dim]Settings[/dim]   [bold]{settings_file}[/bold]")
    console.print(f"\n  Run [info][bold]{c.cli_cmd}[/bold][/info] to start.")
    console.print(
        f"\n  [dim]To install slash commands: [bold]{c.setup_cmd} install-skills[/bold][/dim]"
    )
    console.print(f"\n  [dim]Installation files: {settings_file}, {helper_file}[/dim]")
    console.print(f"  [dim]To uninstall: [bold]{c.setup_cmd} uninstall[/bold][/dim]\n")
