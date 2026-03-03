"""Rich tables for endpoint listings and doctor diagnostics."""

from __future__ import annotations

from rich.table import Table

from fmapi_opskit.network.endpoints import get_endpoint_state
from fmapi_opskit.ui.console import get_console


def display_agent_endpoints(
    endpoints: list[dict],
    highlight_models: list[str] | None = None,
) -> bool:
    """Display agent-relevant endpoints as a formatted Rich table.

    Returns False if no endpoints to show, True otherwise.
    """
    if not endpoints:
        return False

    console = get_console()
    highlight = set(highlight_models or [])

    table = Table(show_header=True, show_edge=False, pad_edge=False, box=None, padding=(0, 1))
    table.add_column("", width=3)
    table.add_column("ENDPOINT NAME", min_width=44, style="bold")
    table.add_column("STATE", min_width=12)

    for ep in endpoints:
        name = ep.get("name", "")
        state = get_endpoint_state(ep)

        # Marker and name styling
        if name in highlight:
            marker = "[green]>[/green]"
            name_styled = f"[bold green]{name}[/bold green]"
        else:
            marker = " "
            name_styled = name

        # State styling
        if state == "READY":
            state_styled = f"[green]{state}[/green]"
        elif state == "NOT_READY":
            state_styled = f"[yellow]{state}[/yellow]"
        else:
            state_styled = state

        table.add_row(marker, name_styled, state_styled)

    console.print(table)
    return True


def display_model_validation(
    models: list[tuple[str, str, str, str]],
) -> bool:
    """Display per-model validation results.

    Args:
        models: List of (label, model_name, status, detail) tuples.

    Returns:
        True if all passed, False otherwise.
    """
    console = get_console()
    all_pass = True

    if not models:
        console.print("  [dim]SKIP[/dim]  No models configured")
        return True

    for label, model_name, status, detail in models:
        padded = f"{label:<8}"
        detail_str = f"  [dim]({detail})[/dim]" if detail else ""

        if status == "PASS":
            console.print(f"  [success]PASS[/success]  {padded}{model_name}")
        elif status == "WARN":
            console.print(f"  [warning]WARN[/warning]  {padded}{model_name}{detail_str}")
            all_pass = False
        elif status == "FAIL":
            console.print(f"  [error]FAIL[/error]  {padded}{model_name}{detail_str}")
            all_pass = False
        else:
            console.print(f"  [dim]SKIP[/dim]  {padded}{model_name}{detail_str}")

    return all_pass
