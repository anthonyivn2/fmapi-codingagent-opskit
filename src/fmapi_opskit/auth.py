"""Databricks CLI wrappers, OAuth token management, and authentication flow."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Databricks CLI subprocess wrappers
# ---------------------------------------------------------------------------


@dataclass
class DatabricksResult:
    """Result of a databricks CLI command."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0


def has_databricks_cli() -> bool:
    """Check if the databricks CLI is available."""
    return shutil.which("databricks") is not None


def run_databricks(
    *args: str,
    profile: str | None = None,
    capture_output: bool = True,
    timeout: int = 60,
) -> DatabricksResult:
    """Run a databricks CLI command and return the result.

    Args:
        *args: Command arguments (e.g., "auth", "token").
        profile: Optional --profile flag.
        capture_output: Whether to capture stdout/stderr (False for interactive commands).
        timeout: Command timeout in seconds.
    """
    cmd = ["databricks", *args]
    if profile:
        cmd.extend(["--profile", profile])

    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
        )
        return DatabricksResult(
            success=result.returncode == 0,
            stdout=result.stdout if capture_output else "",
            stderr=result.stderr if capture_output else "",
            returncode=result.returncode,
        )
    except subprocess.TimeoutExpired:
        return DatabricksResult(success=False, stderr="Command timed out")
    except FileNotFoundError:
        return DatabricksResult(success=False, stderr="databricks CLI not found")


def run_databricks_json(*args: str, profile: str | None = None) -> dict | list | None:
    """Run a databricks CLI command with --output json and parse the result."""
    all_args = list(args) + ["--output", "json"]
    result = run_databricks(*all_args, profile=profile)
    if not result.success or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def auth_login(host: str, profile: str) -> bool:
    """Run databricks auth login (interactive — inherits terminal).

    Returns True if the command succeeded.
    """
    repair_malformed_token_cache()

    result = run_databricks(
        "auth",
        "login",
        "--host",
        host,
        profile=profile,
        capture_output=False,
        timeout=120,
    )
    return result.success


# ---------------------------------------------------------------------------
# OAuth token management
# ---------------------------------------------------------------------------


def get_oauth_token(profile: str) -> str:
    """Get an OAuth access token for the given profile.

    Returns the token string, or empty string on failure.
    """
    if not profile:
        return ""

    repair_malformed_token_cache()

    data = run_databricks_json("auth", "token", profile=profile)
    if isinstance(data, dict):
        return data.get("access_token", "")
    return ""


def check_oauth_status(profile: str) -> bool:
    """Check if the OAuth token is currently valid."""
    return bool(get_oauth_token(profile))


# ---------------------------------------------------------------------------
# Authentication flow and legacy PAT cleanup
# ---------------------------------------------------------------------------


def authenticate(host: str, profile: str, platform_info: PlatformInfo) -> None:  # noqa: F821
    """Run the OAuth authentication flow."""
    from fmapi_opskit.ui import logging as log

    log.heading("Authenticating")

    if repair_malformed_token_cache():
        log.warn("Detected malformed Databricks CLI token cache; removed it and retrying auth.")

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
    from fmapi_opskit.ui import logging as log

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
        for tid in old_ids:
            run_databricks("tokens", "delete", tid, profile=profile)
        log.success("Legacy PATs revoked.")


def repair_malformed_token_cache() -> bool:
    """Remove malformed Databricks token cache file, if present.

    Returns True if a malformed cache file was removed, else False.
    """
    cache_path = Path.home() / ".databricks" / "token-cache.json"
    if not cache_path.is_file():
        return False

    try:
        with cache_path.open() as f:
            json.load(f)
    except json.JSONDecodeError:
        try:
            cache_path.unlink()
            return True
        except OSError:
            return False
    except OSError:
        return False

    return False


def cleanup_legacy_cache(settings_base: str) -> None:
    """Remove legacy PAT cache file if present."""
    from fmapi_opskit.ui import logging as log

    legacy_cache = Path(settings_base) / ".claude" / ".fmapi-pat-cache"
    if legacy_cache.is_file():
        legacy_cache.unlink()
        log.success("Removed legacy PAT cache.")
