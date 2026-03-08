"""Status dashboard panels."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth import check_oauth_status
from fmapi_opskit.config.models import FmapiConfig
from fmapi_opskit.core import get_version
from fmapi_opskit.network import build_base_url
from fmapi_opskit.ui.console import get_console


def _parse_expiry_epoch(expiry_value: str) -> int | None:
    """Parse an ISO-8601 expiry timestamp into epoch seconds."""
    text = expiry_value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _read_token_cache_status(cache_file: Path, profile: str | None = None) -> tuple[str, str]:
    """Return (state, detail) for Databricks token-cache.json state."""
    if not cache_file.is_file():
        return "PENDING", "No Databricks token cache yet"

    try:
        payload = json.loads(cache_file.read_text())
    except OSError:
        return "WARN", "Cannot read Databricks token cache"
    except json.JSONDecodeError:
        return "WARN", "Databricks token cache is malformed"

    entries = payload.get("tokens") or payload.get("Tokens")
    if not isinstance(entries, dict) or not entries:
        return "PENDING", "No cached OAuth sessions yet"

    entry_key = profile if profile and profile in entries else next(iter(entries.keys()))
    entry = entries.get(entry_key)
    if not isinstance(entry, dict):
        return "WARN", "Databricks token cache entry is malformed"

    now = int(time.time())
    expiry_epoch = None
    expiry_value = entry.get("expiry")
    if isinstance(expiry_value, str):
        expiry_epoch = _parse_expiry_epoch(expiry_value)

    if expiry_epoch is None:
        return "ACTIVE", f"Cached token for '{entry_key}' (expiry unknown)"

    remaining = expiry_epoch - now
    if remaining <= 0:
        return "STALE", f"Cached token for '{entry_key}' expired ({-remaining}s ago)"
    if remaining <= 300:
        return "STALE", f"Cached token for '{entry_key}' near expiry ({remaining}s remaining)"
    return "ACTIVE", f"Cached token for '{entry_key}' ({remaining}s remaining)"


def _read_token_lock_status(lock_dir: Path) -> tuple[str, str] | None:
    """Return (state, detail) for cache-expire lock directory, or None when absent."""
    if not lock_dir.is_dir():
        return None

    pid_file = lock_dir / "pid"
    if pid_file.is_file():
        try:
            pid_str = pid_file.read_text().strip()
            if pid_str.isdigit():
                pid = int(pid_str)
                os.kill(pid, 0)
                return "INFO", f"Cache-expire lock active (PID {pid})"
        except OSError:
            pass

    return "WARN", "Stale cache-expire lock detected"


def display_status_dashboard(cfg: FmapiConfig, adapter: AgentAdapter) -> None:
    """Display the full FMAPI status dashboard."""
    console = get_console()

    console.print("\n[bold]  FMAPI Status[/bold]\n")
    console.print(f"  [dim]Version[/dim]    [bold]{get_version()}[/bold]")
    console.print()

    # Configuration
    console.print("  [bold]Configuration[/bold]")
    console.print(f"  [dim]Workspace[/dim]  [bold]{cfg.host or 'unknown'}[/bold]")
    console.print(f"  [dim]Profile[/dim]    [bold]{cfg.profile or 'unknown'}[/bold]")
    console.print(f"  [dim]Model[/dim]      [bold]{cfg.model or 'unknown'}[/bold]")
    console.print(f"  [dim]Opus[/dim]       [bold]{cfg.opus or 'unknown'}[/bold]")
    console.print(f"  [dim]Sonnet[/dim]     [bold]{cfg.sonnet or 'unknown'}[/bold]")
    console.print(f"  [dim]Haiku[/dim]      [bold]{cfg.haiku or 'unknown'}[/bold]")
    if cfg.ttl:
        console.print(f"  [dim]TTL[/dim]        [bold]{cfg.ttl}m[/bold]")
    if cfg.ai_gateway == "true":
        console.print("  [dim]Routing[/dim]    [bold]AI Gateway v2 (beta)[/bold]")
        console.print(f"  [dim]Workspace ID[/dim] [bold]{cfg.workspace_id or 'unknown'}[/bold]")
        base_url = build_base_url(cfg.host, True, cfg.workspace_id)
        console.print(f"  [dim]Base URL[/dim]   [bold]{base_url}[/bold]")
    else:
        console.print("  [dim]Routing[/dim]    [bold]Serving Endpoints (v1)[/bold]")
    console.print()

    # Auth
    console.print("  [bold]Auth[/bold]")
    from fmapi_opskit.auth import has_databricks_cli

    if cfg.profile and has_databricks_cli():
        if check_oauth_status(cfg.profile):
            console.print("  [success]ACTIVE[/success]   OAuth session valid")
        else:
            console.print(
                f"  [error]EXPIRED[/error]  Run: [info]databricks auth login "
                f"--host {cfg.host} --profile {cfg.profile}[/info]"
            )
    else:
        console.print("  [dim]UNKNOWN[/dim]  Cannot check (databricks CLI not found or no profile)")
    console.print()

    # Token Cache
    console.print("  [bold]Token Cache[/bold]")
    cache_file = Path.home() / ".databricks" / "token-cache.json"
    lock_dir = Path.home() / ".databricks" / ".fmapi-token-cache-expire-lock"

    cache_state, cache_detail = _read_token_cache_status(cache_file, cfg.profile)
    state_tag = {
        "ACTIVE": f"[success]{cache_state}[/success]",
        "PENDING": f"[dim]{cache_state}[/dim]",
        "STALE": f"[dim]{cache_state}[/dim]",
        "WARN": f"[warning]{cache_state}[/warning]",
    }.get(cache_state, f"[dim]{cache_state}[/dim]")
    console.print(f"  {state_tag}   {cache_detail}")

    lock_status = _read_token_lock_status(lock_dir)
    if lock_status is not None:
        lock_state, lock_detail = lock_status
        if lock_state == "INFO":
            console.print(f"  [dim]{lock_state}[/dim]     {lock_detail}")
        else:
            console.print(f"  [warning]{lock_state}[/warning]     {lock_detail}")
    console.print()

    # Files
    console.print("  [bold]Files[/bold]")
    console.print(f"  [dim]Settings[/dim]   {cfg.settings_file}")
    console.print(f"  [dim]Helper[/dim]     {cfg.helper_file}")
    console.print()
