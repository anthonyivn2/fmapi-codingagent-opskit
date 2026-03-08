"""Doctor command — comprehensive diagnostics with 10 sub-checks."""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
from pathlib import Path

from rich.console import Console

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth import check_oauth_status, get_oauth_token, has_databricks_cli
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.config.models import FmapiConfig
from fmapi_opskit.core import (
    PlatformInfo,
    check_xcode_clt_installed,
    detect_python_version,
    get_cmd_version,
    get_version,
    get_xcode_clt_path,
    install_hint,
)
from fmapi_opskit.network import check_http_reachable, fetch_endpoints, validate_model
from fmapi_opskit.settings.hooks import get_fmapi_hook_command
from fmapi_opskit.ui.console import get_console
from fmapi_opskit.ui.tables import display_model_validation


def do_doctor(adapter: AgentAdapter, platform_info: PlatformInfo) -> None:
    """Run comprehensive FMAPI diagnostics."""
    console = get_console()
    console.print("\n[bold]  FMAPI Doctor[/bold]\n")

    cfg = discover_config(adapter)
    any_fail = False

    if not _doctor_dependencies(adapter, platform_info):
        any_fail = True
    _doctor_xcode_clt(platform_info)
    _doctor_python(platform_info)
    _doctor_environment(platform_info)
    if not _doctor_configuration(adapter, cfg):
        any_fail = True
    if not _doctor_profile(cfg):
        any_fail = True
    if not _doctor_auth(cfg, platform_info):
        any_fail = True
    if not _doctor_connectivity(cfg):
        any_fail = True
    if not _doctor_models(adapter, cfg):
        any_fail = True
    _doctor_hooks(cfg)
    if not _doctor_token_cache(cfg):
        any_fail = True

    if any_fail:
        console.print("  [error]Some checks failed.[/error] Review the issues above.\n")
        sys.exit(1)
    else:
        console.print("  [success]All checks passed![/success]\n")
        sys.exit(0)


def _doctor_dependencies(adapter: AgentAdapter, pinfo: PlatformInfo) -> bool:
    console = get_console()
    console.print("  [bold]Dependencies[/bold]")
    ok = True

    for dep_name in ("jq", "databricks", adapter.config.cli_cmd, "curl"):
        if shutil.which(dep_name):
            ver = get_cmd_version(dep_name)
            console.print(f"  [success]PASS[/success]  {dep_name}  [dim]{ver}[/dim]")
        else:
            hint = install_hint(dep_name, pinfo, adapter.config)
            console.print(f"  [error]FAIL[/error]  {dep_name}  [dim]Fix: {hint}[/dim]")
            ok = False

    console.print(f"  [dim]fmapi-codingagent-setup[/dim]  {get_version()}")
    console.print()
    return ok


def _doctor_xcode_clt(pinfo: PlatformInfo) -> bool:
    """Check Xcode Command Line Tools (macOS only, non-blocking)."""
    console = get_console()
    console.print("  [bold]Xcode CLT[/bold]")

    if pinfo.os_type != "Darwin":
        console.print("  [dim]SKIP[/dim]  Not macOS")
        console.print()
        return True

    if check_xcode_clt_installed():
        path = get_xcode_clt_path()
        console.print(f"  [success]PASS[/success]  Xcode CLT installed  [dim]{path}[/dim]")
    else:
        console.print(
            "  [warning]WARN[/warning]  Xcode CLT not installed  "
            "[dim]Fix: xcode-select --install[/dim]"
        )

    console.print()
    return True


def _doctor_python(pinfo: PlatformInfo) -> bool:
    """Show Python version info (all platforms, non-blocking)."""
    console = get_console()
    console.print("  [bold]Python[/bold]")

    version, source, is_adequate = detect_python_version()
    console.print(f"  [dim]INFO[/dim]  Python {version} ({source})")

    if not is_adequate:
        console.print(
            "  [warning]WARN[/warning]  Python >= 3.10 recommended  "
            "[dim]uv will auto-download a compatible version if needed[/dim]"
        )

    console.print()
    return True


def _doctor_environment(pinfo: PlatformInfo) -> None:
    console = get_console()
    console.print("  [bold]Environment[/bold]")
    console.print(f"  [dim]INFO[/dim]  OS: {pinfo.os_type}")

    if os.environ.get("DATABRICKS_TOKEN"):
        console.print(
            "  [warning]WARN[/warning]  DATABRICKS_TOKEN is set in your shell env  "
            "[dim]This can override profile-based OAuth and cause Invalid Token errors. "
            "Unset it before launching Claude Code.[/dim]"
        )

    for env_key in ("DATABRICKS_HOST", "DATABRICKS_AUTH_TYPE"):
        if os.environ.get(env_key):
            console.print(
                f"  [warning]WARN[/warning]  {env_key} is set in your shell env  "
                "[dim]It may override profile-based auth behavior.[/dim]"
            )

    if pinfo.is_wsl:
        console.print(
            f"  [dim]INFO[/dim]  WSL version: {pinfo.wsl_version or 'unknown'}  "
            "[yellow](experimental)[/yellow]"
        )
        if pinfo.wsl_distro:
            console.print(f"  [dim]INFO[/dim]  WSL distro: {pinfo.wsl_distro}")

        if shutil.which("wslview"):
            console.print("  [success]PASS[/success]  wslview available (wslu installed)")
        elif shutil.which("xdg-open"):
            console.print("  [success]PASS[/success]  xdg-open available")
        elif os.environ.get("BROWSER"):
            console.print(
                f"  [success]PASS[/success]  BROWSER env var set: {os.environ['BROWSER']}"
            )
        else:
            console.print(
                "  [warning]WARN[/warning]  No browser opener found  "
                "[dim]Fix: sudo apt-get install -y wslu[/dim]"
            )

    console.print()


def _doctor_configuration(adapter: AgentAdapter, cfg: FmapiConfig) -> bool:
    console = get_console()
    console.print("  [bold]Configuration[/bold]")
    ok = True

    if not shutil.which("jq"):
        console.print("  [warning]SKIP[/warning]  Cannot check configuration (jq not installed)")
        console.print()
        return True

    if not cfg.found:
        console.print(
            "  [error]FAIL[/error]  No FMAPI configuration found  [dim]Fix: run setup first[/dim]"
        )
        console.print()
        return False

    # Settings file valid JSON
    settings_path = Path(cfg.settings_file)
    if settings_path.is_file():
        try:
            json.loads(settings_path.read_text())
            console.print(
                f"  [success]PASS[/success]  Settings file is valid JSON  "
                f"[dim]{cfg.settings_file}[/dim]"
            )
        except (json.JSONDecodeError, OSError):
            console.print(
                f"  [error]FAIL[/error]  Settings file is invalid JSON  "
                f"[dim]{cfg.settings_file}[/dim]"
            )
            ok = False
    else:
        console.print(
            f"  [error]FAIL[/error]  Settings file not found  [dim]{cfg.settings_file}[/dim]"
        )
        ok = False

    # Required env keys
    if cfg.settings_file and Path(cfg.settings_file).is_file():
        try:
            settings = json.loads(Path(cfg.settings_file).read_text())
        except (json.JSONDecodeError, OSError):
            settings = {}
        env = settings.get("env", {})
        missing = [k for k in adapter.config.required_env_keys if not env.get(k)]
        if not missing:
            console.print("  [success]PASS[/success]  All required FMAPI env keys present")
        else:
            console.print(
                f"  [error]FAIL[/error]  Missing env keys: {' '.join(missing)}  "
                "[dim]Fix: re-run setup[/dim]"
            )
            ok = False

    # Routing mode
    if cfg.ai_gateway == "true":
        console.print(
            f"  [dim]INFO[/dim]  Routing: AI Gateway v2 (beta), "
            f"workspace ID: {cfg.workspace_id or 'unknown'}"
        )
    else:
        console.print("  [dim]INFO[/dim]  Routing: Serving Endpoints (v1)")

    # Agent-specific checks
    if not adapter.doctor_extra():
        ok = False

    # Helper script
    if cfg.helper_file and Path(cfg.helper_file).is_file():
        if os.access(cfg.helper_file, os.X_OK):
            console.print(
                f"  [success]PASS[/success]  Helper script exists and is executable  "
                f"[dim]{cfg.helper_file}[/dim]"
            )
        else:
            console.print(
                f"  [error]FAIL[/error]  Helper script not executable  "
                f"[dim]Fix: chmod 700 {cfg.helper_file}[/dim]"
            )
            ok = False
    elif cfg.helper_file:
        console.print(
            f"  [error]FAIL[/error]  Helper script not found  [dim]{cfg.helper_file}[/dim]"
        )
        ok = False

    console.print()
    return ok


def _doctor_profile(cfg: FmapiConfig) -> bool:
    console = get_console()
    console.print("  [bold]Profile[/bold]")

    if not cfg.profile:
        console.print("  [warning]SKIP[/warning]  No profile configured")
        console.print()
        return True

    dbcfg = Path.home() / ".databrickscfg"
    if dbcfg.is_file():
        try:
            content = dbcfg.read_text()
            if f"[{cfg.profile}]" in content:
                console.print(
                    f"  [success]PASS[/success]  Profile '{cfg.profile}' exists in ~/.databrickscfg"
                )
                console.print()
                return True
        except OSError:
            pass

    console.print(
        f"  [error]FAIL[/error]  Profile '{cfg.profile}' not found in ~/.databrickscfg  "
        "[dim]Fix: --reauth or re-run setup[/dim]"
    )
    console.print()
    return False


def _doctor_auth(cfg: FmapiConfig, pinfo: PlatformInfo) -> bool:
    console = get_console()
    console.print("  [bold]Auth[/bold]")

    if not cfg.profile:
        console.print("  [warning]SKIP[/warning]  No profile configured")
        console.print()
        return True

    if not has_databricks_cli():
        console.print("  [warning]SKIP[/warning]  databricks CLI not installed")
        console.print()
        return True

    ok = True
    if check_oauth_status(cfg.profile):
        console.print("  [success]PASS[/success]  OAuth token is valid")
    else:
        console.print(
            "  [error]FAIL[/error]  OAuth token expired or invalid  [dim]Fix: reauth[/dim]"
        )
        ok = False

    if pinfo.is_headless:
        console.print(
            "  [warning]INFO[/warning]  Headless SSH session detected -- "
            "auto-open browser is unavailable; reauth uses URL copy/paste"
        )

    console.print()
    return ok


def _doctor_connectivity(cfg: FmapiConfig) -> bool:
    console = get_console()
    console.print("  [bold]Connectivity[/bold]")

    if not cfg.host:
        console.print("  [warning]SKIP[/warning]  No host configured")
        console.print()
        return True

    token = get_oauth_token(cfg.profile) if cfg.profile else ""
    if not token:
        console.print("  [warning]SKIP[/warning]  Cannot test connectivity (no valid token)")
        console.print()
        return True

    ok = True
    url = f"{cfg.host}/api/2.0/serving-endpoints"
    code = check_http_reachable(url, token)

    if code == 200:
        console.print(f"  [success]PASS[/success]  Databricks API reachable  [dim]{cfg.host}[/dim]")
    elif code > 0:
        console.print(
            f"  [warning]WARN[/warning]  Databricks API returned HTTP {code}  [dim]{cfg.host}[/dim]"
        )
        ok = False
    else:
        console.print(
            f"  [error]FAIL[/error]  Cannot reach Databricks API  "
            f"[dim]Fix: check network and {cfg.host}[/dim]"
        )
        ok = False

    # Gateway connectivity
    if cfg.ai_gateway == "true" and cfg.workspace_id:
        gw_url = f"https://{cfg.workspace_id}.ai-gateway.cloud.databricks.com/anthropic/v1/messages"
        gw_code = check_http_reachable(gw_url, token)
        if gw_code > 0:
            console.print(
                f"  [success]PASS[/success]  AI Gateway v2 reachable  [dim](HTTP {gw_code})[/dim]"
            )
        else:
            console.print(
                "  [error]FAIL[/error]  Cannot reach AI Gateway v2  "
                "[dim]Fix: check workspace ID and network[/dim]"
            )
            ok = False

    console.print()
    return ok


def _doctor_models(adapter: AgentAdapter, cfg: FmapiConfig) -> bool:
    console = get_console()
    console.print("  [bold]Models[/bold]")

    if not cfg.found:
        console.print("  [warning]SKIP[/warning]  No configuration found")
        console.print()
        return True

    if not cfg.profile or not has_databricks_cli():
        console.print("  [warning]SKIP[/warning]  Cannot validate models (missing profile or CLI)")
        console.print()
        return True

    if not check_oauth_status(cfg.profile):
        console.print("  [warning]SKIP[/warning]  Cannot validate models (auth failed)")
        console.print()
        return True

    endpoints = fetch_endpoints(cfg.profile)

    models_to_check: list[tuple[str, str]] = []
    if cfg.model:
        models_to_check.append(("Model", cfg.model))
    if cfg.opus:
        models_to_check.append(("Opus", cfg.opus))
    if cfg.sonnet:
        models_to_check.append(("Sonnet", cfg.sonnet))
    if cfg.haiku:
        models_to_check.append(("Haiku", cfg.haiku))

    if not models_to_check:
        console.print("  [dim]SKIP[/dim]  No models configured")
        console.print()
        return True

    results: list[tuple[str, str, str, str]] = []
    for label, model_name in models_to_check:
        if endpoints is None:
            results.append((label, model_name, "WARN", "could not fetch endpoints"))
        else:
            status, detail = validate_model(endpoints, model_name)
            results.append((label, model_name, status, detail))

    ok = display_model_validation(results)
    console.print()
    return ok


def _doctor_hooks(cfg: FmapiConfig) -> None:
    """Check for legacy hooks — informational only (hooks are no longer used)."""
    console = get_console()
    console.print("  [bold]Hooks[/bold]")

    if not cfg.found:
        console.print("  [dim]SKIP[/dim]  No configuration found")
        console.print()
        return

    settings: dict = {}
    if cfg.settings_file:
        with contextlib.suppress(json.JSONDecodeError, OSError):
            settings = json.loads(Path(cfg.settings_file).read_text())

    has_legacy = False
    for hook_type in ("SubagentStart", "UserPromptSubmit"):
        hook_cmd = get_fmapi_hook_command(settings, hook_type)
        if hook_cmd:
            has_legacy = True
            console.print(
                f"  [warning]INFO[/warning]  Legacy {hook_type} hook found  "
                "[dim]Will be removed on next setup run[/dim]"
            )

    if not has_legacy:
        console.print(
            "  [success]PASS[/success]  No legacy hooks  "
            "[dim]Token management handled by apiKeyHelper[/dim]"
        )

    console.print()


def _doctor_token_cache(cfg: FmapiConfig) -> bool:
    """Check token cache and lock health."""
    import time

    console = get_console()
    console.print("  [bold]Token Cache[/bold]")

    if not cfg.found or not cfg.helper_file:
        console.print("  [dim]SKIP[/dim]  No configuration found")
        console.print()
        return True

    cache_dir = Path(cfg.helper_file).parent
    cache_file = cache_dir / ".fmapi-token-cache"
    lock_dir = cache_dir / ".fmapi-token-lock"

    _check_token_cache_file(console, cache_file, int(time.time()))
    _check_token_lock(console, lock_dir)

    console.print()
    return True


def _check_token_cache_file(console: Console, cache_file: Path, now: int) -> None:
    """Display token cache status for the doctor command."""
    if not cache_file.is_file():
        console.print(
            "  [dim]INFO[/dim]  No token cache yet  [dim]Will be created on first API call[/dim]"
        )
        return

    try:
        lines = cache_file.read_text().strip().split("\n")
    except OSError:
        console.print(
            f"  [warning]WARN[/warning]  Cannot read token cache  [dim]Fix: rm {cache_file}[/dim]"
        )
        return

    # v2 format: timestamp, profile, host, expiry_epoch, token
    if len(lines) >= 5 and lines[0].isdigit() and lines[4]:
        age = now - int(lines[0])
        expiry_epoch = int(lines[3]) if lines[3].isdigit() else 0
        if expiry_epoch > 0 and (expiry_epoch - now) <= 300:
            console.print(
                "  [dim]INFO[/dim]  Token cache near expiry  "
                "[dim]Will be refreshed before next use[/dim]"
            )
        _print_cache_age(console, age, label="")
    # Legacy format: timestamp, token
    elif len(lines) >= 2 and lines[0].isdigit() and lines[1]:
        age = now - int(lines[0])
        _print_cache_age(console, age, label=" (legacy format)")
    else:
        console.print(
            f"  [warning]WARN[/warning]  Token cache is malformed  [dim]Fix: rm {cache_file}[/dim]"
        )


def _print_cache_age(console: Console, age: int, *, label: str) -> None:
    """Print cache freshness status based on age."""
    if age < 240:
        console.print(
            f"  [success]PASS[/success]  Token cache is fresh{label}  "
            f"[dim]Age: {age}s (max 240s)[/dim]"
        )
    else:
        console.print(
            f"  [dim]INFO[/dim]  Token cache is stale{label}  "
            f"[dim]Age: {age}s — will refresh on next use[/dim]"
        )


def _check_token_lock(console: Console, lock_dir: Path) -> None:
    """Display token lock status for the doctor command."""
    if not lock_dir.is_dir():
        console.print("  [success]PASS[/success]  No stale token locks")
        return

    if _is_lock_held_by_live_process(lock_dir, console):
        return

    console.print(
        f"  [warning]WARN[/warning]  Stale token lock detected  [dim]Fix: rm -rf {lock_dir}[/dim]"
    )


def _is_lock_held_by_live_process(lock_dir: Path, console: Console) -> bool:
    """Return True if lock is held by a running process."""
    pid_file = lock_dir / "pid"
    if not pid_file.is_file():
        return False

    try:
        pid_str = pid_file.read_text().strip()
    except OSError:
        return False

    if not pid_str.isdigit():
        return False

    pid = int(pid_str)
    try:
        os.kill(pid, 0)
    except OSError:
        return False

    console.print(
        f"  [dim]INFO[/dim]  Token lock held by PID {pid}  [dim]Active refresh in progress[/dim]"
    )
    return True
