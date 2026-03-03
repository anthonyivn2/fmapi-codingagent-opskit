"""Print setup summary."""

from __future__ import annotations

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.network.gateway import build_base_url
from fmapi_opskit.ui.console import get_console, get_verbosity


def print_summary(
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
    hook_file: str,
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
    console.print(f"  [dim]Hook[/dim]       [bold]{hook_file}[/bold]")
    console.print(f"  [dim]Settings[/dim]   [bold]{settings_file}[/bold]")
    console.print(f"\n  Run [info][bold]{c.cli_cmd}[/bold][/info] to start.\n")
