"""Databricks CLI wrappers, OAuth token management, and authentication flow."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from base64 import urlsafe_b64decode
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# OAuth URL extraction and polling constants
# ---------------------------------------------------------------------------

_OAUTH_URL_PATTERN = re.compile(r"(https://\S+(?:/oidc/(?:v1/)?authorize|/authorize)\S*)")
_URL_READ_TIMEOUT = 30  # seconds to wait for URL in CLI output
_POLL_TIMEOUT = 300  # seconds to poll for token (5 min)
_POLL_INTERVAL = 3  # seconds between poll attempts

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


def _extract_oauth_url(text: str) -> str | None:
    """Extract an OAuth authorization URL from CLI output text."""
    match = _OAUTH_URL_PATTERN.search(text)
    return match.group(1) if match else None


def _display_oauth_url(url: str) -> None:
    """Display the OAuth URL prominently using a Rich Panel."""
    from rich.panel import Panel

    from fmapi_opskit.ui.console import get_console

    console = get_console()
    console.print()
    console.print(
        Panel(
            f"[bold]{url}[/bold]\n\n"
            "[dim]Open this URL in any browser to authenticate.\n"
            "Tip: If on SSH, open it from your local machine and keep this command running.[/dim]",
            title="[info]OAuth Login URL[/info]",
            border_style="info",
            padding=(1, 2),
        )
    )
    console.print()


def _read_stream_lines(stream: object, lines: list[str]) -> None:
    """Thread target: read a stream line-by-line into a list."""
    try:
        for raw_line in stream:  # type: ignore[union-attr]
            lines.append(raw_line)
    except Exception:  # noqa: BLE001
        pass


def _poll_for_token(profile: str, timeout: int = _POLL_TIMEOUT) -> bool:
    """Poll `databricks auth token` until a valid token appears or timeout.

    Returns True when a token is found, False on timeout.
    """
    from fmapi_opskit.ui import logging as log

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        token = get_oauth_token(profile)
        if token:
            log.debug("poll_for_token: token acquired")
            return True
        time.sleep(_POLL_INTERVAL)
    return False


def _terminate_process(proc: subprocess.Popen) -> None:  # type: ignore[type-arg]
    """Safely terminate a subprocess."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass


def _start_auth_login_process(host: str, profile: str) -> subprocess.Popen | None:  # type: ignore[type-arg]
    """Start `databricks auth login` in URL-print mode."""
    from fmapi_opskit.ui import logging as log

    cmd = ["databricks", "auth", "login", "--host", host, "--profile", profile]
    env = {**os.environ, "BROWSER": "none"}

    try:
        return subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            env=env,
        )
    except FileNotFoundError:
        log.error("databricks CLI not found.")
        return None


def _start_auth_login_readers(
    proc: subprocess.Popen,  # type: ignore[type-arg]
) -> tuple[list[str], list[str], threading.Thread, threading.Thread]:
    """Start background readers for auth-login stdout/stderr."""
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    stdout_thread = threading.Thread(
        target=_read_stream_lines, args=(proc.stdout, stdout_lines), daemon=True
    )
    stderr_thread = threading.Thread(
        target=_read_stream_lines, args=(proc.stderr, stderr_lines), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    return stdout_lines, stderr_lines, stdout_thread, stderr_thread


def _wait_for_oauth_url(
    proc: subprocess.Popen,  # type: ignore[type-arg]
    stdout_lines: list[str],
    stderr_lines: list[str],
    timeout: int = _URL_READ_TIMEOUT,
) -> str | None:
    """Wait briefly for an OAuth URL to appear in process output."""
    url_found: str | None = None
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        for line in stdout_lines + stderr_lines:
            url_found = _extract_oauth_url(line)
            if url_found:
                return url_found

        if proc.poll() is not None:
            return None

        time.sleep(0.3)

    return None


def _collect_auth_login_result(
    proc: subprocess.Popen,  # type: ignore[type-arg]
    stdout_thread: threading.Thread,
    stderr_thread: threading.Thread,
    stderr_lines: list[str],
) -> tuple[bool, str]:
    """Collect process completion details for auth-login without URL path."""
    proc.wait(timeout=30)
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)
    return proc.returncode == 0, "".join(stderr_lines).strip()


def auth_login(host: str, profile: str) -> bool:
    """Run databricks auth login with URL display and auto-polling.

    Launches ``databricks auth login`` as a background process with
    ``BROWSER=none`` to suppress auto-open and force URL printing.
    Extracts the OAuth URL from output, displays it prominently, then
    polls ``databricks auth token`` until authentication completes.

    Returns True if a valid token was obtained.
    """
    from fmapi_opskit.ui import logging as log

    repair_malformed_token_cache()

    proc = _start_auth_login_process(host, profile)
    if proc is None:
        return False

    stdout_lines, stderr_lines, stdout_thread, stderr_thread = _start_auth_login_readers(proc)
    url_found = _wait_for_oauth_url(proc, stdout_lines, stderr_lines)

    if url_found:
        _display_oauth_url(url_found)
        log.info("Waiting for authentication to complete ...")
        success = _poll_for_token(profile)
        _terminate_process(proc)
        return success

    completed_ok, all_stderr = _collect_auth_login_result(
        proc, stdout_thread, stderr_thread, stderr_lines
    )
    if completed_ok:
        return True

    if all_stderr:
        log.debug(f"auth_login stderr: {all_stderr}")

    return False


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
    if isinstance(data, dict) and _is_token_fresh(data):
        return data.get("access_token", "")

    # One retry allows Databricks CLI to auto-refresh a near-expiry token.
    data = run_databricks_json("auth", "token", profile=profile)
    if isinstance(data, dict) and _is_token_fresh(data):
        return data.get("access_token", "")

    return ""


def check_oauth_status(profile: str) -> bool:
    """Check if the OAuth token is currently valid."""
    return bool(get_oauth_token(profile))


# ---------------------------------------------------------------------------
# Authentication flow and legacy PAT cleanup
# ---------------------------------------------------------------------------


def authenticate(host: str, profile: str) -> None:
    """Run the OAuth authentication flow.

    URL display and auto-polling are handled inside ``auth_login()``,
    so no platform-specific warnings are needed here.
    """
    from fmapi_opskit.ui import logging as log

    log.heading("Authenticating")

    if repair_malformed_token_cache():
        log.warn("Detected malformed Databricks CLI token cache; removed it and retrying auth.")

    token = get_oauth_token(profile)
    log.debug(f"authenticate: existing token={'present' if token else 'missing'}")

    if not token:
        log.info(f"Logging in to {host} ...")
        token = _login_and_fetch_token(host, profile, failure_message="Failed to authenticate.")

        if not token:
            log.warn(
                "OAuth token still unavailable after login; "
                "clearing Databricks token cache and retrying once."
            )
            clear_token_cache()
            token = _login_and_fetch_token(
                host,
                profile,
                failure_message="Failed to authenticate after retry.",
            )

    if not token:
        log.error("Failed to get OAuth access token.")
        sys.exit(1)

    log.success("OAuth session established.")

    # Clean up legacy FMAPI PATs
    _cleanup_legacy_pats(profile)


def _login_and_fetch_token(host: str, profile: str, *, failure_message: str) -> str:
    """Run auth login once and fetch token, exiting on login failure."""
    from fmapi_opskit.ui import logging as log

    if not auth_login(host, profile):
        log.error(failure_message)
        sys.exit(1)

    return get_oauth_token(profile)


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


def _is_token_fresh(token_data: dict, *, min_validity_seconds: int = 300) -> bool:
    """Return True when token exists and is not near expiry.

    If token expiry metadata is unavailable, treat token as fresh.
    """
    token = token_data.get("access_token", "")
    if not token:
        return False

    expires_in = _token_expires_in_seconds(token_data)
    if expires_in is None:
        return True

    return expires_in > min_validity_seconds


def _token_expires_in_seconds(token_data: dict) -> int | None:
    """Extract token lifetime (seconds remaining) from Databricks token JSON."""
    for key in ("expires_in", "expiresIn"):
        value = token_data.get(key)
        if value is None:
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue

    for key in ("expiry", "expires_at", "expiresAt"):
        value = token_data.get(key)
        if not isinstance(value, str) or not value:
            continue

        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        try:
            expires_at = datetime.fromisoformat(normalized)
        except ValueError:
            continue

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        seconds = int(
            (expires_at.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds()
        )
        return seconds

    token = token_data.get("access_token")
    if isinstance(token, str) and token:
        return _jwt_expires_in_seconds(token)

    return None


def _jwt_expires_in_seconds(token: str) -> int | None:
    """Extract seconds remaining from JWT exp claim, when present."""
    parts = token.split(".")
    if len(parts) < 2 or not parts[1]:
        return None

    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return None

    exp = payload.get("exp")
    if exp is None:
        return None

    try:
        return int(float(exp)) - int(datetime.now(timezone.utc).timestamp())
    except (TypeError, ValueError):
        return None


def _databricks_token_cache_path() -> Path:
    """Return the path to the Databricks CLI token cache file."""
    return Path.home() / ".databricks" / "token-cache.json"


def repair_malformed_token_cache() -> bool:
    """Remove malformed Databricks token cache file, if present.

    Returns True if a malformed cache file was removed, else False.
    """
    cache_path = _databricks_token_cache_path()
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


def clear_token_cache() -> bool:
    """Remove Databricks token cache file, if present.

    Returns True if a cache file was removed, else False.
    """
    cache_path = _databricks_token_cache_path()
    if not cache_path.is_file():
        return False

    try:
        cache_path.unlink()
        return True
    except OSError:
        return False


def cleanup_legacy_cache(settings_base: str) -> None:
    """Remove legacy PAT cache file if present."""
    from fmapi_opskit.ui import logging as log

    legacy_cache = Path(settings_base) / ".claude" / ".fmapi-pat-cache"
    if legacy_cache.is_file():
        legacy_cache.unlink()
        log.success("Removed legacy PAT cache.")


def clear_helper_token_cache(helper_file: str) -> bool:
    """Clear local helper token cache/lock files to force fresh token retrieval.

    Returns True if at least one cache artifact was removed.
    """
    if not helper_file:
        return False
    helper_path = Path(helper_file)

    removed = False
    cache_file = helper_path.parent / ".fmapi-token-cache"
    lock_dir = helper_path.parent / ".fmapi-token-lock"

    if cache_file.is_file():
        try:
            cache_file.unlink()
            removed = True
        except OSError:
            pass

    if lock_dir.is_dir():
        try:
            for child in lock_dir.iterdir():
                if child.is_file():
                    child.unlink()
            lock_dir.rmdir()
            removed = True
        except OSError:
            pass

    return removed
