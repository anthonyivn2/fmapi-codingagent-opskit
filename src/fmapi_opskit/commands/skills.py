"""Skills commands — install and uninstall FMAPI skill files."""

from __future__ import annotations

import sys
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.agents.claudecode import SKILL_NAMES
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console
from fmapi_opskit.ui.prompts import select_option


def do_install_skills(adapter: AgentAdapter, script_dir: Path) -> None:
    """Install FMAPI skill files to ~/.claude/skills/."""
    console = get_console()
    c = adapter.config
    console.print(f"\n[bold]  {c.name} x Databricks FMAPI -- Install Skills[/bold]\n")

    adapter.register_plugin(script_dir)


def do_uninstall_skills(adapter: AgentAdapter) -> None:
    """Remove FMAPI skill files from ~/.claude/skills/."""
    console = get_console()
    c = adapter.config
    console.print(f"\n[bold]  {c.name} x Databricks FMAPI -- Uninstall Skills[/bold]\n")

    # Check if any skills are installed
    skills_base = Path.home() / ".claude" / "skills"
    installed: list[str] = []
    for name in SKILL_NAMES:
        skill_path = skills_base / name
        if skill_path.is_dir():
            installed.append(str(skill_path))

    if not installed:
        log.info("No FMAPI skills installed. Nothing to remove.")
        sys.exit(0)

    console.print("  [bold]Found installed skills:[/bold]\n")
    for sd in installed:
        console.print(f"    [dim]{sd}[/dim]")
    console.print()

    choice = select_option(
        "Remove FMAPI skills?",
        [("Yes", "remove skills listed above"), ("No", "cancel and exit")],
    )
    if choice != 0:
        log.info("Cancelled.")
        sys.exit(0)

    console.print()
    adapter.deregister_plugin()
