"""OAuth re-authentication command."""

from __future__ import annotations

import shutil
import sys

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth import auth_login, check_oauth_status
from fmapi_opskit.commands._common import require_fmapi_config
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.core import PlatformInfo
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console


def do_reauth(adapter: AgentAdapter, platform_info: PlatformInfo) -> None:
    """Re-authenticate Databricks OAuth session."""
    require_fmapi_config(adapter, "reauth")
    cfg = discover_config(adapter)

    if platform_info.is_headless:
        console = get_console()
        console.print(
            "  [warning]WARN[/warning]  Headless SSH session detected. "
            "Browser-based OAuth may not work."
        )

    if platform_info.is_wsl and not shutil.which("wslview") and not shutil.which("xdg-open"):
        log.warn("WSL detected but no browser opener found.")
        log.info(
            "If the browser does not open, install wslu: [info]sudo apt-get install -y wslu[/info]"
        )

    log.info(f"Re-authenticating with Databricks (profile: {cfg.profile}) ...")

    if not auth_login(cfg.host, cfg.profile):
        log.error(
            f"Re-authentication failed. Try manually: "
            f"databricks auth login --host {cfg.host} --profile {cfg.profile}"
        )
        sys.exit(1)

    if check_oauth_status(cfg.profile):
        log.success(f"OAuth session re-established for profile '{cfg.profile}'.")
    else:
        log.error(
            f"Re-authentication failed. Try manually: "
            f"databricks auth login --host {cfg.host} --profile {cfg.profile}"
        )
        sys.exit(1)
