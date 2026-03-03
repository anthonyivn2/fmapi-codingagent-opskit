"""Tests for dependency detection helpers (Xcode CLT, Python version)."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

from fmapi_opskit.core.deps import (
    check_xcode_clt_installed,
    detect_python_version,
    get_xcode_clt_path,
)


class TestCheckXcodeCltInstalled:
    def test_returns_true_when_installed(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="/Library/Developer\n")
        with patch("fmapi_opskit.core.deps.subprocess.run", return_value=fake):
            assert check_xcode_clt_installed() is True

    def test_returns_false_when_not_installed(self):
        fake = subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="")
        with patch("fmapi_opskit.core.deps.subprocess.run", return_value=fake):
            assert check_xcode_clt_installed() is False

    def test_returns_false_on_file_not_found(self):
        with patch("fmapi_opskit.core.deps.subprocess.run", side_effect=FileNotFoundError):
            assert check_xcode_clt_installed() is False

    def test_returns_false_on_timeout(self):
        with patch(
            "fmapi_opskit.core.deps.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="xcode-select", timeout=5),
        ):
            assert check_xcode_clt_installed() is False


class TestGetXcodeCltPath:
    def test_returns_path_when_installed(self):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="/Library/Developer/CommandLineTools\n"
        )
        with patch("fmapi_opskit.core.deps.subprocess.run", return_value=fake):
            assert get_xcode_clt_path() == "/Library/Developer/CommandLineTools"

    def test_returns_empty_when_not_installed(self):
        fake = subprocess.CompletedProcess(args=[], returncode=2, stdout="", stderr="")
        with patch("fmapi_opskit.core.deps.subprocess.run", return_value=fake):
            assert get_xcode_clt_path() == ""

    def test_returns_empty_on_file_not_found(self):
        with patch("fmapi_opskit.core.deps.subprocess.run", side_effect=FileNotFoundError):
            assert get_xcode_clt_path() == ""

    def test_returns_empty_on_timeout(self):
        with patch(
            "fmapi_opskit.core.deps.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="xcode-select", timeout=5),
        ):
            assert get_xcode_clt_path() == ""


class TestDetectPythonVersion:
    def test_returns_current_version(self):
        version, _source, _adequate = detect_python_version()
        vi = sys.version_info
        assert version == f"{vi.major}.{vi.minor}.{vi.micro}"

    def test_source_is_system_for_standard_path(self):
        with patch.object(sys, "executable", "/usr/bin/python3"):
            _version, source, _adequate = detect_python_version()
            assert source == "system"

    def test_source_is_uv_managed_for_uv_path(self):
        with patch.object(
            sys, "executable", "/home/user/.local/share/uv/python/cpython-3.12/bin/python3"
        ):
            _version, source, _adequate = detect_python_version()
            assert source == "uv-managed"

    def test_adequate_for_310_plus(self):
        """The running interpreter should be >= 3.10 (required by this project)."""
        _version, _source, is_adequate = detect_python_version()
        assert is_adequate is True
