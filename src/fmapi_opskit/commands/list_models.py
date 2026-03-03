"""List serving endpoints command."""

from __future__ import annotations

import sys

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth.oauth import check_oauth_status
from fmapi_opskit.commands._common import require_fmapi_config
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.network.endpoints import fetch_endpoints, filter_agent_endpoints
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console
from fmapi_opskit.ui.tables import display_agent_endpoints


def do_list_models(adapter: AgentAdapter) -> None:
    """List all serving endpoints in the workspace."""
    require_fmapi_config(adapter, "list-models")
    cfg = discover_config(adapter)

    if not cfg.host:
        log.error("Could not determine host from helper script.")
        sys.exit(1)

    if not check_oauth_status(cfg.profile):
        log.error(f"OAuth session expired or invalid. Run: setup-fmapi-{adapter.config.id} reauth")
        sys.exit(1)

    console = get_console()
    c = adapter.config
    console.print(f"\n[bold]  FMAPI {c.endpoint_title} Serving Endpoints[/bold]")
    console.print(f"  [dim]Workspace: {cfg.host}[/dim]\n")

    endpoints = fetch_endpoints(cfg.profile)
    if endpoints is None:
        log.error("Failed to fetch serving endpoints. Check your network and profile.")
        sys.exit(1)

    filtered = filter_agent_endpoints(endpoints, c.endpoint_filter)

    # Build configured models list for highlighting
    configured = [m for m in [cfg.model, cfg.opus, cfg.sonnet, cfg.haiku] if m]

    if not display_agent_endpoints(filtered, configured):
        log.info(f"No {c.endpoint_title} serving endpoints found in this workspace.")
        console.print()
        sys.exit(0)

    # Legend
    console.print()
    console.print("  [green]>[/green] [dim]Currently configured[/dim]")
    console.print()
