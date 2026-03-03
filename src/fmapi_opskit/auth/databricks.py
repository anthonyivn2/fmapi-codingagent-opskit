"""Typed subprocess wrappers for the databricks CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


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
