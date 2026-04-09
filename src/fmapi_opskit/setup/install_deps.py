"""Platform-specific dependency installation."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.core import PlatformInfo
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.prompts import confirm

DATABRICKS_CLI_VERSION = "0.296.0"


def install_dependencies(
    adapter: AgentAdapter,
    platform_info: PlatformInfo,
    *,
    non_interactive: bool = False,
) -> None:
    """Install required dependencies (jq, databricks CLI, agent CLI)."""
    log.heading("Installing dependencies")

    os_type = platform_info.os_type

    if os_type == "Darwin":
        _install_macos_deps(non_interactive=non_interactive)
    elif os_type == "Linux":
        _install_linux_deps(non_interactive=non_interactive)
    else:
        log.error(f"Unsupported OS: {os_type}. This tool supports macOS (Darwin) and Linux.")
        sys.exit(1)

    adapter.install_cli()


def _install_macos_deps(*, non_interactive: bool) -> None:
    """Install macOS dependencies via Homebrew."""
    if shutil.which("brew"):
        log.success("Homebrew already installed.")
    else:
        log.info("Installing Homebrew ...")
        subprocess.run(
            [
                "/bin/bash",
                "-c",
                "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)",
            ],
            check=True,
        )
        log.success("Homebrew installed.")

    if shutil.which("jq"):
        log.success("jq already installed.")
    else:
        log.info("Installing jq ...")
        subprocess.run(["brew", "install", "jq"], check=True)
        log.success("jq installed.")

    _ensure_databricks_cli("Darwin", non_interactive=non_interactive)


def _install_linux_deps(*, non_interactive: bool) -> None:
    """Install Linux dependencies via apt-get/yum."""
    if shutil.which("jq"):
        log.success("jq already installed.")
    else:
        log.info("Installing jq ...")
        if shutil.which("apt-get"):
            subprocess.run(["sudo", "apt-get", "update", "-qq"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "jq"], check=True)
        elif shutil.which("yum"):
            subprocess.run(["sudo", "yum", "install", "-y", "jq"], check=True)
        else:
            log.error("Cannot install jq: no supported package manager (apt-get or yum) found.")
            sys.exit(1)
        log.success("jq installed.")

    _ensure_databricks_cli("Linux", non_interactive=non_interactive)


def _ensure_databricks_cli(os_type: str, *, non_interactive: bool) -> None:
    current_version = _get_databricks_cli_version()
    if not current_version:
        log.info(f"Installing Databricks CLI {DATABRICKS_CLI_VERSION} ...")
        _install_databricks_cli(os_type)
        log.success("Databricks CLI installed.")
        return

    if _compare_versions(current_version, DATABRICKS_CLI_VERSION) >= 0:
        log.success(f"Databricks CLI {current_version} already installed.")
        return

    if non_interactive:
        hint = _databricks_upgrade_hint(os_type)
        log.warn(
            f"Databricks CLI {current_version} is below preferred version "
            f"{DATABRICKS_CLI_VERSION}; leaving existing install unchanged in non-interactive mode. "
            f"To upgrade manually, run: {hint}"
        )
        return

    if confirm(
        f"Databricks CLI {current_version} is installed. Upgrade to {DATABRICKS_CLI_VERSION}?",
        default=True,
    ):
        log.info(f"Upgrading Databricks CLI to {DATABRICKS_CLI_VERSION} ...")
        _upgrade_databricks_cli(os_type)
        log.success(f"Databricks CLI upgraded to {DATABRICKS_CLI_VERSION}.")
    else:
        log.success(f"Keeping existing Databricks CLI {current_version}.")


def _install_databricks_cli(os_type: str) -> None:
    if os_type == "Darwin":
        subprocess.run(["brew", "tap", "databricks/tap"], check=True)
        subprocess.run(["brew", "install", f"databricks@{DATABRICKS_CLI_VERSION}"], check=True)
        return

    install_url = "https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh"
    subprocess.run(
        f"curl -fsSL {install_url} | sh -s -- --version {DATABRICKS_CLI_VERSION}",
        shell=True,
        check=True,
    )


def _upgrade_databricks_cli(os_type: str) -> None:
    if os_type == "Darwin":
        subprocess.run(["brew", "tap", "databricks/tap"], check=True)
        subprocess.run(["brew", "upgrade", f"databricks@{DATABRICKS_CLI_VERSION}"], check=True)
        return

    _install_databricks_cli(os_type)


def _get_databricks_cli_version() -> str:
    if not shutil.which("databricks"):
        return ""

    try:
        result = subprocess.run(
            ["databricks", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return ""

    output = (result.stdout or result.stderr or "").strip()
    match = re.search(r"(\d+\.\d+\.\d+)", output)
    return match.group(1) if match else ""


def _compare_versions(left: str, right: str) -> int:
    left_parts = tuple(int(part) for part in left.split("."))
    right_parts = tuple(int(part) for part in right.split("."))
    if left_parts < right_parts:
        return -1
    if left_parts > right_parts:
        return 1
    return 0

def _databricks_upgrade_hint(os_type: str) -> str:
    if os_type == "Darwin":
        return f"brew tap databricks/tap && brew upgrade databricks@{DATABRICKS_CLI_VERSION}"

    return (
        "curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh "
        f"| sh -s -- --version {DATABRICKS_CLI_VERSION}"
    )

