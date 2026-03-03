"""OS, WSL, and headless detection — replaces core.sh platform logic."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path


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
