"""Version, platform detection, and dependency checking."""

from __future__ import annotations

import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from fmapi_opskit.agents.base import AgentConfig

# ---------------------------------------------------------------------------
# Clone directory resolution
# ---------------------------------------------------------------------------

_DEFAULT_CLONE_DIR = Path.home() / ".fmapi-codingagent-setup"


def _is_clone_dir(path: Path) -> bool:
    """Return True if *path* looks like the project clone (has .git/ and VERSION)."""
    return (path / ".git").is_dir() and (path / "VERSION").is_file()


def find_clone_dir() -> Path | None:
    """Locate the git clone directory using a 3-tier strategy.

    1. ``FMAPI_HOME`` env var (set by ``install.sh``).
    2. Walk up from ``__file__`` looking for ``.git/`` + ``VERSION``.
    3. Default ``~/.fmapi-codingagent-setup``.

    Returns ``None`` if none of the above resolve to a valid clone.
    """
    # Tier 1: explicit env var
    env_home = os.environ.get("FMAPI_HOME")
    if env_home:
        candidate = Path(env_home).expanduser().resolve()
        if _is_clone_dir(candidate):
            return candidate

    # Tier 2: walk up from this source file
    current = Path(__file__).resolve().parent
    for _ in range(5):  # at most 5 levels up
        if _is_clone_dir(current):
            return current
        if current.parent == current:
            break
        current = current.parent

    # Tier 3: default install location
    if _is_clone_dir(_DEFAULT_CLONE_DIR):
        return _DEFAULT_CLONE_DIR

    return None


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


def get_version() -> str:
    """Return the current package version.

    Tries the clone directory's ``VERSION`` file first, then falls back to
    ``importlib.metadata`` (reads from wheel / pyproject.toml metadata).
    """
    clone_dir = find_clone_dir()
    if clone_dir is not None:
        version_file = clone_dir / "VERSION"
        if version_file.is_file():
            text = version_file.read_text().strip()
            if text:
                return text

    try:
        return importlib.metadata.version("fmapi-codingagent-opskit")
    except importlib.metadata.PackageNotFoundError:
        return "dev"


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlatformInfo:
    """Detected platform information."""

    os_type: str  # "Darwin", "Linux", "Windows", "Unknown"
    is_wsl: bool
    wsl_version: str  # "1", "2", or ""
    wsl_distro: str  # e.g. "Ubuntu" or ""

    @property
    def is_headless(self) -> bool:
        """Detect headless SSH sessions (no browser for OAuth).

        WSL can open a browser via Windows interop, so it's not headless.
        """
        if self.is_wsl:
            return False
        has_ssh = bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"))
        has_display = bool(os.environ.get("DISPLAY"))
        return has_ssh and not has_display


def detect_platform() -> PlatformInfo:
    """Detect the current platform, WSL status, and headless state."""
    os_type = platform.system() or "Unknown"

    is_wsl = False
    wsl_version = ""
    wsl_distro = ""

    if os_type == "Linux":
        # Check WSL_DISTRO_NAME env var (most reliable)
        if os.environ.get("WSL_DISTRO_NAME"):
            is_wsl = True
            wsl_distro = os.environ["WSL_DISTRO_NAME"]
        else:
            # Fallback: check /proc/version for 'microsoft'
            try:
                proc_version = Path("/proc/version").read_text()
                if "microsoft" in proc_version.lower():
                    is_wsl = True
            except OSError:
                pass

        if is_wsl:
            try:
                proc_version = Path("/proc/version").read_text()
                wsl_version = "2" if "microsoft-standard-wsl2" in proc_version.lower() else "1"
            except OSError:
                wsl_version = "1"

    return PlatformInfo(
        os_type=os_type,
        is_wsl=is_wsl,
        wsl_version=wsl_version,
        wsl_distro=wsl_distro,
    )


# ---------------------------------------------------------------------------
# Dependency checking and install hints
# ---------------------------------------------------------------------------

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
