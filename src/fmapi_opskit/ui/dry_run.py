"""Dry-run plan display."""

from __future__ import annotations

import shutil
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.network.gateway import build_base_url
from fmapi_opskit.ui.console import get_console


def display_dry_run_plan(
    adapter: AgentAdapter,
    *,
    host: str,
    profile: str,
    model: str,
    opus: str,
    sonnet: str,
    haiku: str,
    ttl_ms: str,
    settings_file: str,
    helper_file: str,
    hook_file: str,
    ai_gateway_enabled: bool,
    pending_workspace_id: str,
    script_dir: Path,
) -> None:
    """Print the dry-run plan showing what setup would do."""
    console = get_console()
    c = adapter.config

    console.print(f"\n[bold]  {c.name} x Databricks FMAPI -- Dry Run[/bold]\n")
    console.print("  The following actions [bold]would[/bold] be performed:\n")

    # Dependencies
    console.print("  [bold]Dependencies[/bold]")
    for dep_name in ("jq", "databricks", c.cli_cmd):
        if shutil.which(dep_name):
            console.print(f"  [success]ok[/success]  {dep_name} already installed")
        else:
            console.print(f"  [info]::[/info]  {dep_name} would be installed")
    console.print()

    # Authentication
    console.print("  [bold]Authentication[/bold]")
    console.print(f"  [info]::[/info]  OAuth login target: [bold]{host}[/bold]")
    console.print(f"  [info]::[/info]  CLI profile: [bold]{profile}[/bold]")
    console.print()

    # Routing
    console.print("  [bold]Routing[/bold]")
    if ai_gateway_enabled:
        dry_ws_id = pending_workspace_id or "<to be detected>"
        if dry_ws_id != "<to be detected>":
            dry_base_url = build_base_url(host, True, dry_ws_id)
        else:
            dry_base_url = "https://<workspace-id>.ai-gateway.cloud.databricks.com/anthropic"
        console.print("  [info]::[/info]  Mode: [bold]AI Gateway v2 (beta)[/bold]")
        console.print(f"  [info]::[/info]  Workspace ID: [bold]{dry_ws_id}[/bold]")
        console.print(f"  [info]::[/info]  Base URL: [bold]{dry_base_url}[/bold]")
    else:
        console.print("  [info]::[/info]  Mode: [bold]Serving Endpoints (v1)[/bold]")
    console.print()

    # Settings
    if ai_gateway_enabled:
        ws_id_for_url = pending_workspace_id or "<workspace-id>"
        dry_run_base_url = build_base_url(host, True, ws_id_for_url)
    else:
        dry_run_base_url = build_base_url(host, False, "")

    console.print("  [bold]Settings[/bold]")
    console.print(f"  [info]::[/info]  Settings file: [bold]{settings_file}[/bold]")
    if Path(settings_file).is_file():
        console.print("       [dim](exists -- FMAPI keys would be merged)[/dim]")
    else:
        console.print("       [dim](would be created)[/dim]")
    console.print("  [info]::[/info]  Env vars that would be set:")
    adapter.dry_run_env_display(model, dry_run_base_url, opus, sonnet, haiku, ttl_ms)
    console.print()

    # Agent-specific dry-run sections
    adapter.dry_run_extra(script_dir)

    # Helper
    console.print("\n  [bold]Helper script[/bold]")
    console.print(f"  [info]::[/info]  Path: [bold]{helper_file}[/bold]")
    if Path(helper_file).is_file():
        console.print("       [dim](exists -- would be overwritten)[/dim]")
    else:
        console.print("       [dim](would be created)[/dim]")

    # Hooks
    console.print("\n  [bold]Hooks[/bold]")
    console.print(f"  [info]::[/info]  Auth pre-check script: [bold]{hook_file}[/bold]")
    if Path(hook_file).is_file():
        console.print("       [dim](exists -- would be overwritten)[/dim]")
    else:
        console.print("       [dim](would be created)[/dim]")
    console.print(
        "  [info]::[/info]  Registered for: [bold]SubagentStart[/bold], "
        "[bold]UserPromptSubmit[/bold]"
    )

    console.print("\n  [dim]No changes were made. Remove --dry-run to run setup.[/dim]\n")
