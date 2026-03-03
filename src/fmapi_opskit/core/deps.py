"""Dependency checking and platform-specific install hints."""

from __future__ import annotations

import shutil
import subprocess
import sys

from fmapi_opskit.agents.base import AgentConfig
from fmapi_opskit.core.platform import PlatformInfo

# Minimum Python version required by this tool
_MIN_PYTHON = (3, 10)


def check_xcode_clt_installed() -> bool:
    """Check whether Xcode Command Line Tools are installed (macOS only).

    Returns True if ``xcode-select -p`` exits 0, False otherwise.
    On non-macOS systems (FileNotFoundError), returns False.
    """
    try:
        result = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except subprocess.TimeoutExpired:
        return False


def get_xcode_clt_path() -> str:
    """Return the Xcode CLT install path, or empty string if unavailable."""
    try:
        result = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def detect_python_version() -> tuple[str, str, bool]:
    """Detect the running Python version, its source, and adequacy.

    Returns:
        (version, source, is_adequate) where *version* is e.g. "3.12.1",
        *source* is "uv-managed" or "system", and *is_adequate* is True
        when the version >= 3.10.
    """
    vi = sys.version_info
    version = f"{vi.major}.{vi.minor}.{vi.micro}"
    source = "uv-managed" if ".local/share/uv" in sys.executable else "system"
    is_adequate = (vi.major, vi.minor) >= _MIN_PYTHON
    return version, source, is_adequate


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
