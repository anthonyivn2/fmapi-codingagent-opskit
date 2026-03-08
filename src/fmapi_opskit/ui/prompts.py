"""Interactive prompts — prompt_value and select_option using Rich."""

from __future__ import annotations

import sys

from rich.prompt import Prompt
from simple_term_menu import TerminalMenu

from fmapi_opskit.ui.console import get_console

try:
    import readline
except ImportError:  # pragma: no cover - Windows without readline
    readline = None  # type: ignore[assignment]


def prompt_value(
    label: str,
    cli_val: str,
    default: str,
    non_interactive: bool,
) -> str:
    """Prompt for a value, respecting CLI flags and non-interactive mode.

    Priority: cli_val > interactive input > default.
    """
    if cli_val:
        return cli_val
    if non_interactive:
        return default

    console = get_console()
    if default:
        result = Prompt.ask(f"  [info]?[/info] {label}", default=default, console=console)
    else:
        result = Prompt.ask(f"  [info]?[/info] {label}", console=console)
    return result


def prompt_prefilled_value(label: str, default: str) -> str:
    """Prompt with prefilled editable text when readline is available."""
    console = get_console()

    if not default:
        return Prompt.ask(f"  [info]?[/info] {label}", console=console)

    if readline is None:
        return Prompt.ask(f"  [info]?[/info] {label}", default=default, console=console)

    console.print(f"  [info]?[/info] {label}  [dim](edit and press Enter)[/dim]")

    def _insert_default() -> None:
        readline.insert_text(default)

    readline.set_startup_hook(_insert_default)
    try:
        value = input("  > ").strip()
    finally:
        readline.set_startup_hook(None)

    return value or default


def select_option(
    prompt: str,
    options: list[tuple[str, str]],
    non_interactive: bool = False,
    default_index: int = 0,
) -> int:
    """Interactive selector with arrow-key navigation.

    Args:
        prompt: The question to ask.
        options: List of (label, description) tuples.
        non_interactive: If True, return default_index without prompting.
        default_index: 0-based index of the default choice.

    Returns:
        0-based index of the selected option.
    """
    if non_interactive:
        return default_index

    console = get_console()
    console.print(f"  [info]?[/info] {prompt}  [dim](↑/↓ arrows, Enter to select)[/dim]")

    menu_entries: list[str] = []
    for label, desc in options:
        if desc.strip():
            menu_entries.append(f"  {label}  ({desc})")
        else:
            menu_entries.append(f"  {label}")

    menu = TerminalMenu(
        menu_entries,
        cursor_index=default_index,
        menu_cursor="  ❯ ",
        menu_cursor_style=("fg_cyan", "bold"),
        menu_highlight_style=("fg_cyan", "bold"),
    )
    chosen = menu.show()

    if chosen is None:
        sys.exit(130)  # Ctrl-C / cancelled

    return chosen


def confirm(prompt: str, default: bool = True) -> bool:
    """Simple yes/no confirmation prompt."""
    console = get_console()
    default_str = "y" if default else "n"
    result = Prompt.ask(
        f"  [info]?[/info] {prompt}",
        choices=["y", "n"],
        default=default_str,
        console=console,
    )
    return result.lower() == "y"
