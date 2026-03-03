"""Rich-based logging helpers — info, success, warn, error, debug."""

from __future__ import annotations

from fmapi_opskit.ui.console import get_console, get_error_console, get_verbosity


def info(msg: str) -> None:
    """Print an informational message (hidden in quiet mode)."""
    if get_verbosity() >= 1:
        get_console().print(f"  [info]::[/info] {msg}")


def success(msg: str) -> None:
    """Print a success message (hidden in quiet mode)."""
    if get_verbosity() >= 1:
        get_console().print(f"  [success]ok[/success] {msg}")


def warn(msg: str) -> None:
    """Print a warning message (hidden in quiet mode)."""
    if get_verbosity() >= 1:
        get_console().print(f"  [warning]! {msg}[/warning]")


def error(msg: str) -> None:
    """Print an error message (always shown, goes to stderr)."""
    get_error_console().print(f"\n  [error]!! ERROR[/error] [red]{msg}[/red]\n")


def debug(msg: str) -> None:
    """Print a debug message (only shown in verbose mode)."""
    if get_verbosity() >= 2:
        get_console().print(f"  [debug]\\[debug][/debug] {msg}")


def heading(title: str) -> None:
    """Print a bold section heading."""
    if get_verbosity() >= 1:
        get_console().print(f"\n[bold]  {title}[/bold]\n")


def subheading(title: str) -> None:
    """Print a bold subsection heading."""
    if get_verbosity() >= 1:
        get_console().print(f"  [bold]{title}[/bold]")
