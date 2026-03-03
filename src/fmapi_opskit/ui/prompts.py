"""Interactive prompts — prompt_value and select_option using Rich."""

from __future__ import annotations

from rich.prompt import Prompt

from fmapi_opskit.ui.console import get_console


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


def select_option(
    prompt: str,
    options: list[tuple[str, str]],
    non_interactive: bool = False,
    default_index: int = 0,
) -> int:
    """Interactive selector using Rich numbered menu.

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
    console.print(f"  [info]?[/info] {prompt}")
    for i, (label, desc) in enumerate(options):
        marker = "[bold]>[/bold]" if i == default_index else " "
        console.print(f"    {marker} {i + 1}) [bold]{label}[/bold]  [dim]{desc}[/dim]")

    choices = [str(i + 1) for i in range(len(options))]
    result = Prompt.ask(
        "  Choice",
        choices=choices,
        default=str(default_index + 1),
        console=console,
    )
    return int(result) - 1


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
