"""Tests for platform detection with mocked environment."""

from __future__ import annotations

from unittest.mock import patch

from fmapi_opskit.core.platform import PlatformInfo, detect_platform


class TestPlatformInfo:
    def test_is_headless_with_ssh(self):
        info = PlatformInfo(
            os_type="linux", is_wsl=False, wsl_version="", wsl_distro=""
        )
        with patch.dict("os.environ", {"SSH_CONNECTION": "1.2.3.4 5678 9.10.11.12 22"}):
            assert info.is_headless is True

    def test_is_headless_without_ssh(self):
        info = PlatformInfo(
            os_type="linux", is_wsl=False, wsl_version="", wsl_distro=""
        )
        with patch.dict("os.environ", {}, clear=True):
            assert info.is_headless is False

    def test_is_headless_with_ssh_tty(self):
        info = PlatformInfo(
            os_type="linux", is_wsl=False, wsl_version="", wsl_distro=""
        )
        with patch.dict("os.environ", {"SSH_TTY": "/dev/pts/0"}):
            assert info.is_headless is True


class TestDetectPlatform:
    @patch("platform.system", return_value="Darwin")
    def test_detects_macos(self, mock_sys):
        info = detect_platform()
        assert info.os_type == "Darwin"
        assert info.is_wsl is False
