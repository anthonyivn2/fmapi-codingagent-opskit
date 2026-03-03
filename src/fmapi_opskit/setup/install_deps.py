"""Platform-specific dependency installation."""

from __future__ import annotations

import shutil
import subprocess
import sys

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.core import PlatformInfo
from fmapi_opskit.ui import logging as log


def install_dependencies(adapter: AgentAdapter, platform_info: PlatformInfo) -> None:
    """Install required dependencies (jq, databricks CLI, agent CLI)."""
    log.heading("Installing dependencies")

    os_type = platform_info.os_type

    if os_type == "Darwin":
        _install_macos_deps()
    elif os_type == "Linux":
        _install_linux_deps()
    else:
        log.error(f"Unsupported OS: {os_type}. This tool supports macOS (Darwin) and Linux.")
        sys.exit(1)

    # Agent CLI
    adapter.install_cli()


def _install_macos_deps() -> None:
    """Install macOS dependencies via Homebrew."""
    # Homebrew
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

    # jq
    if shutil.which("jq"):
        log.success("jq already installed.")
    else:
        log.info("Installing jq ...")
        subprocess.run(["brew", "install", "jq"], check=True)
        log.success("jq installed.")

    # databricks CLI
    if shutil.which("databricks"):
        log.success("Databricks CLI already installed.")
    else:
        log.info("Installing Databricks CLI ...")
        subprocess.run(["brew", "tap", "databricks/tap"], check=True)
        subprocess.run(["brew", "install", "databricks"], check=True)
        log.success("Databricks CLI installed.")


def _install_linux_deps() -> None:
    """Install Linux dependencies via apt-get/yum."""
    # jq
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

    # databricks CLI
    if shutil.which("databricks"):
        log.success("Databricks CLI already installed.")
    else:
        log.info("Installing Databricks CLI ...")
        install_url = "https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh"
        subprocess.run(
            f"curl -fsSL {install_url} | sh",
            shell=True,
            check=True,
        )
        log.success("Databricks CLI installed.")
