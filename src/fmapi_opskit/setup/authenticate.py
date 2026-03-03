"""OAuth authentication flow and legacy PAT cleanup."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from fmapi_opskit.auth.databricks import auth_login, run_databricks_json
from fmapi_opskit.auth.oauth import get_oauth_token
from fmapi_opskit.core.platform import PlatformInfo
from fmapi_opskit.ui import logging as log


def authenticate(host: str, profile: str, platform_info: PlatformInfo) -> None:
    """Run the OAuth authentication flow."""
    log.heading("Authenticating")

    token = get_oauth_token(profile)
    log.debug(f"authenticate: existing token={'present' if token else 'missing'}")

    if not token:
        if platform_info.is_headless:
            from fmapi_opskit.ui.console import get_console

            get_console().print(
                "  [warning]WARN[/warning]  Headless SSH session detected. "
                "Browser-based OAuth may not work."
            )

        if platform_info.is_wsl and not shutil.which("wslview") and not shutil.which("xdg-open"):
            log.warn("WSL detected but no browser opener found.")
            log.info(
                "If the browser does not open, install wslu: "
                "[info]sudo apt-get install -y wslu[/info]"
            )

        log.info(f"Logging in to {host} ...")
        if not auth_login(host, profile):
            log.error("Failed to authenticate.")
            sys.exit(1)

        token = get_oauth_token(profile)

    if not token:
        log.error("Failed to get OAuth access token.")
        sys.exit(1)

    log.success("OAuth session established.")

    # Clean up legacy FMAPI PATs
    _cleanup_legacy_pats(profile)


def _cleanup_legacy_pats(profile: str) -> None:
    """Revoke any legacy FMAPI PATs from prior installations."""
    data = run_databricks_json("tokens", "list", profile=profile)
    if not isinstance(data, list):
        return

    old_ids = [
        t["token_id"]
        for t in data
        if isinstance(t, dict)
        and (t.get("comment") or "").startswith("Claude Code FMAPI")
        and "token_id" in t
    ]

    if old_ids:
        log.info("Cleaning up legacy FMAPI PATs ...")
        from fmapi_opskit.auth.databricks import run_databricks

        for tid in old_ids:
            run_databricks("tokens", "delete", tid, profile=profile)
        log.success("Legacy PATs revoked.")


def cleanup_legacy_cache(settings_base: str) -> None:
    """Remove legacy PAT cache file if present."""
    legacy_cache = Path(settings_base) / ".claude" / ".fmapi-pat-cache"
    if legacy_cache.is_file():
        legacy_cache.unlink()
        log.success("Removed legacy PAT cache.")
