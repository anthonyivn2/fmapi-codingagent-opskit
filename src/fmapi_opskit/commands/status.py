"""Status dashboard command."""

from __future__ import annotations

import sys

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console
from fmapi_opskit.ui.dashboard import display_status_dashboard


def do_status(adapter: AgentAdapter) -> None:
    """Show FMAPI configuration health dashboard."""
    cfg = discover_config(adapter)

    if not cfg.found:
        console = get_console()
        console.print("\n[bold]  FMAPI Status[/bold]\n")
        log.info("No FMAPI configuration found.")
        log.info(f"Run [info]setup-fmapi-{adapter.config.id}[/info] to set up.")
        console.print()
        sys.exit(0)

    display_status_dashboard(cfg, adapter)
