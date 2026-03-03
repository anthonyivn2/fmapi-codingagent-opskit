"""Dependency checking and platform-specific install hints."""

from __future__ import annotations

import shutil
import subprocess
import sys

from fmapi_opskit.agents.base import AgentConfig
from fmapi_opskit.core.platform import PlatformInfo


def require_cmd(cmd: str, error_msg: str) -> None:
    """Require a command to be available, or raise SystemExit with an error message."""
    if not shutil.which(cmd):
        from fmapi_opskit.ui.logging import error

        error(error_msg)
        sys.exit(1)


def install_hint(cmd: str, platform_info: PlatformInfo, agent_config: AgentConfig) -> str:
    """Get a platform-appropriate install hint for a dependency."""
    is_linux = platform_info.os_type == "Linux"

    match cmd:
        case "jq":
            if is_linux:
                return "sudo apt-get install -y jq  (or sudo yum install -y jq)"
            return "brew install jq"
        case "databricks":
            if is_linux:
                return (
                    "curl -fsSL "
                    "https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh"
                )
            return "brew tap databricks/tap && brew install databricks"
        case "curl":
            if is_linux:
                return "sudo apt-get install -y curl  (or sudo yum install -y curl)"
            return "brew install curl"
        case _:
            if cmd == agent_config.cli_cmd:
                return agent_config.cli_install_cmd
            return f"Install {cmd}"


def get_cmd_version(cmd: str) -> str:
    """Get the version string for an installed command."""
    try:
        match cmd:
            case "jq":
                result = subprocess.run(
                    ["jq", "--version"], capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip() or "unknown"
            case "databricks":
                result = subprocess.run(
                    ["databricks", "--version"], capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip().split("\n")[0] or "unknown"
            case "curl":
                result = subprocess.run(
                    ["curl", "--version"], capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip().split("\n")[0] or "unknown"
            case _:
                result = subprocess.run(
                    [cmd, "--version"], capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip().split("\n")[0] or "unknown"
    except Exception:
        return "unknown"
