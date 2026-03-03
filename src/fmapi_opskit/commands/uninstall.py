"""Uninstall command — remove all FMAPI artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.settings.hooks import is_fmapi_hook_entry, remove_fmapi_hooks
from fmapi_opskit.settings.manager import SettingsManager
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console
from fmapi_opskit.ui.prompts import select_option


def do_uninstall(adapter: AgentAdapter) -> None:
    """Remove all FMAPI artifacts and plugin registration."""
    console = get_console()
    c = adapter.config
    console.print(f"\n[bold]  {c.name} x Databricks FMAPI -- Uninstall[/bold]\n")

    default_install_dir = Path.home() / ".fmapi-codingagent-setup"

    # Discover artifacts
    helper_scripts: list[str] = []
    hook_scripts: list[str] = []
    settings_files: list[str] = []

    # Try to discover from existing config
    cfg = discover_config(adapter)
    extra_candidate = cfg.settings_file if cfg.found else ""

    candidates = [str(p) for p in adapter.settings_candidates()]
    if extra_candidate and extra_candidate not in candidates:
        candidates.append(extra_candidate)

    for candidate in candidates:
        if not Path(candidate).is_file():
            continue
        abs_path = str(Path(candidate).resolve())
        if abs_path in settings_files:
            continue

        try:
            settings = json.loads(Path(abs_path).read_text())
        except (json.JSONDecodeError, OSError):
            continue

        has_fmapi = False

        # apiKeyHelper
        helper = settings.get("apiKeyHelper", "")
        if helper:
            has_fmapi = True
            if Path(helper).is_file() and helper not in helper_scripts:
                helper_scripts.append(helper)

        # FMAPI hooks
        hooks = settings.get("hooks", {})
        for hook_type in ("SubagentStart", "UserPromptSubmit"):
            for entry in hooks.get(hook_type, []):
                if is_fmapi_hook_entry(entry):
                    for hook in entry.get("hooks", []):
                        cmd = hook.get("command", "")
                        if cmd and Path(cmd).is_file() and cmd not in hook_scripts:
                            hook_scripts.append(cmd)

        # Legacy _fmapi_meta
        if "_fmapi_meta" in settings:
            has_fmapi = True

        if has_fmapi:
            settings_files.append(abs_path)

    # Early exit if nothing found
    has_install_dir = default_install_dir.is_dir()
    if not helper_scripts and not hook_scripts and not settings_files and not has_install_dir:
        log.info("Nothing to uninstall. No FMAPI artifacts found.")
        sys.exit(0)

    # Display findings
    console.print("  [bold]Found the following FMAPI artifacts:[/bold]\n")

    if helper_scripts:
        console.print("  [info]Helper scripts:[/info]")
        for hs in helper_scripts:
            console.print(f"    [dim]{hs}[/dim]")
        console.print()

    if hook_scripts:
        console.print("  [info]Hook scripts:[/info]")
        for hs in hook_scripts:
            console.print(f"    [dim]{hs}[/dim]")
        console.print()

    if settings_files:
        console.print(
            "  [info]Settings files (FMAPI keys only -- other settings preserved):[/info]"
        )
        for sf in settings_files:
            console.print(f"    [dim]{sf}[/dim]")
        console.print()

    if has_install_dir:
        console.print("  [info]Install directory:[/info]")
        console.print(f"    [dim]{default_install_dir}[/dim]")
        console.print()

    # Confirm
    choice = select_option(
        "Remove FMAPI artifacts?",
        [("Yes", "remove artifacts listed above"), ("No", "cancel and exit")],
    )
    if choice != 0:
        log.info("Cancelled.")
        sys.exit(0)

    console.print()

    # Delete helper scripts
    for hs in helper_scripts:
        Path(hs).unlink(missing_ok=True)
        log.success(f"Deleted {hs}.")

    # Delete hook scripts
    for hs in hook_scripts:
        Path(hs).unlink(missing_ok=True)
        log.success(f"Deleted {hs}.")

    # Clean legacy cache files
    for hs in helper_scripts:
        cache = Path(hs).parent / ".fmapi-pat-cache"
        if cache.is_file():
            cache.unlink()
            log.success(f"Deleted legacy cache {cache}.")

    # Clean settings files
    for sf in settings_files:
        mgr = SettingsManager(Path(sf))
        settings = mgr.read()

        # Remove env keys
        env = settings.get("env", {})
        for key in c.uninstall_env_keys:
            env.pop(key, None)
        if not env:
            settings.pop("env", None)
        else:
            settings["env"] = env

        settings.pop("_fmapi_meta", None)
        settings.pop("apiKeyHelper", None)

        # Remove hooks
        remove_fmapi_hooks(settings)

        if not settings:
            Path(sf).unlink(missing_ok=True)
            log.success(f"Deleted {sf} (no remaining settings).")
        else:
            mgr.write(settings)
            log.success(f"Cleaned FMAPI keys from {sf} (preserved other settings).")

    # Deregister plugin
    adapter.deregister_plugin()

    # Remove install directory
    if has_install_dir:
        import shutil

        shutil.rmtree(default_install_dir, ignore_errors=True)
        log.success(f"Removed install directory {default_install_dir}.")

    console.print("\n[success]  Uninstall complete![/success]\n")
    log.info(
        "To fully remove the CLI tool, run: "
        "[info]uv tool uninstall fmapi-codingagent-opskit[/info]"
    )
