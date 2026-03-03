"""Rich Console factory with theme, NO_COLOR, and pipe handling."""

from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.theme import Theme

# Custom theme matching the bash color scheme
FMAPI_THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "yellow",
        "error": "bold red",
        "debug": "dim",
        "label": "dim",
        "value": "bold",
    }
)

# Module-level console — lazy-initialized via get_console()
_console: Console | None = None
_verbosity: int = 1  # 0=quiet, 1=normal, 2=verbose


def init_console(*, no_color: bool = False, quiet: bool = False, verbose: bool = False) -> None:
    """Initialize the global console with the given settings."""
    global _console, _verbosity  # noqa: PLW0603

    if quiet:
        _verbosity = 0
    elif verbose:
        _verbosity = 2
    else:
        _verbosity = 1

    force_no_color = no_color or bool(os.environ.get("NO_COLOR"))
    _console = Console(
        theme=FMAPI_THEME,
        highlight=False,
        no_color=force_no_color,
        stderr=False,
    )


def get_console() -> Console:
    """Get the global console, initializing with defaults if needed."""
    global _console  # noqa: PLW0603
    if _console is None:
        init_console()
    return _console  # type: ignore[return-value]


def get_error_console() -> Console:
    """Get a console that writes to stderr (for error messages)."""
    c = get_console()
    return Console(
        theme=FMAPI_THEME,
        highlight=False,
        no_color=c.no_color,
        stderr=True,
    )


def get_verbosity() -> int:
    """Get the current verbosity level (0=quiet, 1=normal, 2=verbose)."""
    return _verbosity


def is_interactive() -> bool:
    """Check if stdin is connected to a terminal (for interactive prompts)."""
    return sys.stdin.isatty()
