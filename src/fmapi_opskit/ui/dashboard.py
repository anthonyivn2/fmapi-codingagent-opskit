"""Status dashboard panels."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth.oauth import check_oauth_status
from fmapi_opskit.config.models import FmapiConfig
from fmapi_opskit.core.version import get_version
from fmapi_opskit.network.gateway import build_base_url
from fmapi_opskit.settings.hooks import get_fmapi_hook_command
from fmapi_opskit.ui.console import get_console


def display_status_dashboard(cfg: FmapiConfig, adapter: AgentAdapter) -> None:
    """Display the full FMAPI status dashboard."""
    console = get_console()

    console.print("\n[bold]  FMAPI Status[/bold]\n")
    console.print(f"  [dim]Version[/dim]    [bold]{get_version()}[/bold]")
    console.print()

    # Configuration
    console.print("  [bold]Configuration[/bold]")
    console.print(f"  [dim]Workspace[/dim]  [bold]{cfg.host or 'unknown'}[/bold]")
    console.print(f"  [dim]Profile[/dim]    [bold]{cfg.profile or 'unknown'}[/bold]")
    console.print(f"  [dim]Model[/dim]      [bold]{cfg.model or 'unknown'}[/bold]")
    console.print(f"  [dim]Opus[/dim]       [bold]{cfg.opus or 'unknown'}[/bold]")
    console.print(f"  [dim]Sonnet[/dim]     [bold]{cfg.sonnet or 'unknown'}[/bold]")
    console.print(f"  [dim]Haiku[/dim]      [bold]{cfg.haiku or 'unknown'}[/bold]")
    if cfg.ttl:
        console.print(f"  [dim]TTL[/dim]        [bold]{cfg.ttl}m[/bold]")
    if cfg.ai_gateway == "true":
        console.print("  [dim]Routing[/dim]    [bold]AI Gateway v2 (beta)[/bold]")
        console.print(f"  [dim]Workspace ID[/dim] [bold]{cfg.workspace_id or 'unknown'}[/bold]")
        base_url = build_base_url(cfg.host, True, cfg.workspace_id)
        console.print(f"  [dim]Base URL[/dim]   [bold]{base_url}[/bold]")
    else:
        console.print("  [dim]Routing[/dim]    [bold]Serving Endpoints (v1)[/bold]")
    console.print()

    # Auth
    console.print("  [bold]Auth[/bold]")
    from fmapi_opskit.auth.databricks import has_databricks_cli

    if cfg.profile and has_databricks_cli():
        if check_oauth_status(cfg.profile):
            console.print("  [success]ACTIVE[/success]   OAuth session valid")
        else:
            console.print(
                f"  [error]EXPIRED[/error]  Run: [info]databricks auth login "
                f"--host {cfg.host} --profile {cfg.profile}[/info]"
            )
    else:
        console.print("  [dim]UNKNOWN[/dim]  Cannot check (databricks CLI not found or no profile)")
    console.print()

    # Hooks
    console.print("  [bold]Hooks[/bold]")
    import json

    settings = {}
    if cfg.settings_file:
        with contextlib.suppress(json.JSONDecodeError, OSError):
            settings = json.loads(Path(cfg.settings_file).read_text())

    hook_file_shown = ""
    for hook_type in ("SubagentStart", "UserPromptSubmit"):
        hook_cmd = get_fmapi_hook_command(settings, hook_type)
        if hook_cmd and Path(hook_cmd).is_file() and os.access(hook_cmd, os.X_OK):
            console.print(f"  [success]ENABLED[/success]  {hook_type} pre-check")
            if not hook_file_shown:
                hook_file_shown = hook_cmd
        elif hook_cmd:
            console.print(
                f"  [warning]WARN[/warning]     {hook_type} hook configured but "
                "script missing or not executable"
            )
        else:
            console.print(
                f"  [dim]DISABLED[/dim] {hook_type} pre-check  [dim](re-run setup to enable)[/dim]"
            )
    console.print()

    # Files
    console.print("  [bold]Files[/bold]")
    console.print(f"  [dim]Settings[/dim]   {cfg.settings_file}")
    console.print(f"  [dim]Helper[/dim]     {cfg.helper_file}")
    if hook_file_shown:
        console.print(f"  [dim]Hook[/dim]       {hook_file_shown}")
    console.print()
