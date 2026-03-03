"""Self-update command — git pull + uv tool reinstall."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fmapi_opskit.core import get_version
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console


def do_self_update(script_dir: Path) -> None:
    """Update to the latest version via git pull, then reinstall the Python package."""
    import shutil

    if not shutil.which("git"):
        log.error("git is required for self-update. Install git first.")
        sys.exit(1)

    console = get_console()
    console.print("\n[bold]  FMAPI Self-Update[/bold]\n")

    current_version = get_version()
    log.info(f"Current version: [bold]{current_version}[/bold]")
    log.info(f"Install path:    [dim]{script_dir}[/dim]")

    # Check git repo
    if not (script_dir / ".git").is_dir():
        log.error(f"Not a git installation (no .git/ directory in {script_dir}).")
        log.info(
            "If you installed to a custom location, set the [bold]FMAPI_HOME[/bold] "
            "environment variable to point to your clone directory."
        )
        log.info("Or re-install with:")
        log.info(
            "  [info]bash <(curl -sL "
            "https://raw.githubusercontent.com/anthonyivn2/fmapi-codingagent-setup/"
            "main/install.sh)[/info]"
        )
        sys.exit(1)

    # Detect current branch
    try:
        branch = subprocess.run(
            ["git", "-C", str(script_dir), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception:
        branch = ""

    if not branch or branch == "HEAD":
        branch = "main"
        log.debug("Detached HEAD detected, defaulting to main.")
    log.debug(f"Branch: {branch}")

    # Fetch
    log.info("Checking for updates...")
    result = subprocess.run(
        ["git", "-C", str(script_dir), "fetch", "--quiet", "origin", branch],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        log.error("Failed to fetch from remote. Check your network connection.")
        sys.exit(1)

    # Compare revisions
    local_rev = subprocess.run(
        ["git", "-C", str(script_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    remote_rev = subprocess.run(
        ["git", "-C", str(script_dir), "rev-parse", f"origin/{branch}"],
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()

    if local_rev == remote_rev:
        log.success(f"Already up to date ({current_version}).")
        console.print()
        sys.exit(0)

    # Count commits
    commit_count = subprocess.run(
        ["git", "-C", str(script_dir), "rev-list", "--count", f"HEAD..origin/{branch}"],
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    log.info(f"{commit_count} new commit(s) available.")

    # Pull
    log.info("Updating...")
    result = subprocess.run(
        ["git", "-C", str(script_dir), "pull", "--quiet", "origin", branch],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        log.error("Failed to pull updates. You may have local changes.")
        log.info(f"Fix with: [info]cd {script_dir} && git stash && git pull origin {branch}[/info]")
        sys.exit(1)

    # Reinstall Python package
    if shutil.which("uv"):
        log.info("Reinstalling Python package...")
        subprocess.run(
            ["uv", "tool", "install", str(script_dir), "--force", "--quiet"],
            capture_output=True,
            timeout=60,
        )

    # Read new version
    version_file = script_dir / "VERSION"
    new_version = version_file.read_text().strip() if version_file.is_file() else "unknown"

    log.success(f"Updated: {current_version} -> {new_version}")
    console.print()
