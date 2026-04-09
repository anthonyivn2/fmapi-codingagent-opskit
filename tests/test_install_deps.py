"""Tests for platform-specific dependency installation."""

from __future__ import annotations

from types import SimpleNamespace

from fmapi_opskit.core import PlatformInfo
from fmapi_opskit.setup import install_deps


class DummyAdapter:
    def install_cli(self) -> None:
        pass


def test_install_dependencies_macos_pins_databricks_only_when_missing(monkeypatch):
    calls: list[object] = []

    def fake_which(cmd: str):
        mapping = {"brew": "/opt/homebrew/bin/brew", "jq": "/usr/bin/jq", "databricks": None}
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)

    install_deps.install_dependencies(DummyAdapter(), PlatformInfo("Darwin", False, "", ""))

    assert ["brew", "tap", "databricks/tap"] in calls
    assert ["brew", "install", "databricks@0.296.0"] in calls


def test_install_dependencies_macos_leaves_newer_databricks_installed(monkeypatch):
    calls: list[object] = []

    def fake_which(cmd: str):
        mapping = {
            "brew": "/opt/homebrew/bin/brew",
            "jq": "/usr/bin/jq",
            "databricks": "/opt/homebrew/bin/databricks",
        }
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append(cmd)
        if cmd == ["databricks", "--version"]:
            return SimpleNamespace(returncode=0, stdout="Databricks CLI v0.300.0\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)
    monkeypatch.setattr(install_deps, "confirm", lambda prompt, default=True: True)

    install_deps.install_dependencies(DummyAdapter(), PlatformInfo("Darwin", False, "", ""))

    assert ["brew", "tap", "databricks/tap"] not in calls
    assert ["brew", "install", "databricks@0.296.0"] not in calls
    assert ["brew", "upgrade", "databricks@0.296.0"] not in calls


def test_install_dependencies_macos_upgrades_older_databricks_when_confirmed(monkeypatch):
    calls: list[object] = []

    def fake_which(cmd: str):
        mapping = {
            "brew": "/opt/homebrew/bin/brew",
            "jq": "/usr/bin/jq",
            "databricks": "/opt/homebrew/bin/databricks",
        }
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append(cmd)
        if cmd == ["databricks", "--version"]:
            return SimpleNamespace(returncode=0, stdout="Databricks CLI v0.295.0\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)
    monkeypatch.setattr(install_deps, "confirm", lambda prompt, default=True: True)

    install_deps.install_dependencies(DummyAdapter(), PlatformInfo("Darwin", False, "", ""))

    assert ["brew", "tap", "databricks/tap"] in calls
    assert ["brew", "upgrade", "databricks@0.296.0"] in calls


def test_install_dependencies_macos_skips_upgrade_when_declined(monkeypatch):
    calls: list[object] = []

    def fake_which(cmd: str):
        mapping = {
            "brew": "/opt/homebrew/bin/brew",
            "jq": "/usr/bin/jq",
            "databricks": "/opt/homebrew/bin/databricks",
        }
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append(cmd)
        if cmd == ["databricks", "--version"]:
            return SimpleNamespace(returncode=0, stdout="Databricks CLI v0.295.0\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)
    monkeypatch.setattr(install_deps, "confirm", lambda prompt, default=True: False)

    install_deps.install_dependencies(DummyAdapter(), PlatformInfo("Darwin", False, "", ""))

    assert ["brew", "upgrade", "databricks@0.296.0"] not in calls


def test_install_dependencies_linux_pins_databricks_only_when_missing(monkeypatch):
    calls: list[tuple[object, bool]] = []

    def fake_which(cmd: str):
        mapping = {
            "jq": "/usr/bin/jq",
            "databricks": None,
            "apt-get": "/usr/bin/apt-get",
            "yum": None,
        }
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append((cmd, shell))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)

    install_deps.install_dependencies(DummyAdapter(), PlatformInfo("Linux", False, "", ""))

    assert any(shell and "install.sh | sh -s -- --version 0.296.0" in cmd for cmd, shell in calls)


def test_install_dependencies_linux_upgrades_older_databricks_when_confirmed(monkeypatch):
    calls: list[tuple[object, bool]] = []

    def fake_which(cmd: str):
        mapping = {
            "jq": "/usr/bin/jq",
            "databricks": "/usr/local/bin/databricks",
            "apt-get": "/usr/bin/apt-get",
            "yum": None,
        }
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append((cmd, shell))
        if cmd == ["databricks", "--version"]:
            return SimpleNamespace(returncode=0, stdout="Databricks CLI version 0.295.0\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)
    monkeypatch.setattr(install_deps, "confirm", lambda prompt, default=True: True)

    install_deps.install_dependencies(DummyAdapter(), PlatformInfo("Linux", False, "", ""))

    assert any(shell and "install.sh | sh -s -- --version 0.296.0" in cmd for cmd, shell in calls)


def test_install_dependencies_linux_skips_databricks_when_present_and_newer(monkeypatch):
    calls: list[tuple[object, bool]] = []

    def fake_which(cmd: str):
        mapping = {
            "jq": "/usr/bin/jq",
            "databricks": "/usr/local/bin/databricks",
            "apt-get": "/usr/bin/apt-get",
            "yum": None,
        }
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append((cmd, shell))
        if cmd == ["databricks", "--version"]:
            return SimpleNamespace(returncode=0, stdout="Databricks CLI version 0.300.0\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)
    monkeypatch.setattr(install_deps, "confirm", lambda prompt, default=True: True)

    install_deps.install_dependencies(DummyAdapter(), PlatformInfo("Linux", False, "", ""))

    assert not any(
        shell and "databricks/setup-cli" in cmd for cmd, shell in calls if isinstance(cmd, str)
    )


def test_install_dependencies_macos_non_interactive_skips_upgrade(monkeypatch):
    calls: list[object] = []

    def fake_which(cmd: str):
        mapping = {
            "brew": "/opt/homebrew/bin/brew",
            "jq": "/usr/bin/jq",
            "databricks": "/opt/homebrew/bin/databricks",
        }
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append(cmd)
        if cmd == ["databricks", "--version"]:
            return SimpleNamespace(returncode=0, stdout="Databricks CLI v0.295.0\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    confirm_called = False
    warnings: list[str] = []

    def fake_confirm(prompt, default=True):
        nonlocal confirm_called
        confirm_called = True
        return True

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)
    monkeypatch.setattr(install_deps, "confirm", fake_confirm)
    monkeypatch.setattr(install_deps.log, "warn", lambda msg: warnings.append(msg))

    install_deps.install_dependencies(
        DummyAdapter(), PlatformInfo("Darwin", False, "", ""), non_interactive=True
    )

    assert confirm_called is False
    assert ["brew", "upgrade", "databricks@0.296.0"] not in calls
    assert warnings == [
        "Databricks CLI 0.295.0 is below preferred version 0.296.0; leaving existing install unchanged in non-interactive mode. To upgrade manually, run: brew tap databricks/tap && brew upgrade databricks@0.296.0"
    ]


def test_install_dependencies_linux_non_interactive_skips_upgrade(monkeypatch):
    calls: list[tuple[object, bool]] = []

    def fake_which(cmd: str):
        mapping = {
            "jq": "/usr/bin/jq",
            "databricks": "/usr/local/bin/databricks",
            "apt-get": "/usr/bin/apt-get",
            "yum": None,
        }
        return mapping.get(cmd)

    def fake_run(cmd, check=True, shell=False, capture_output=False, text=False, timeout=None):
        calls.append((cmd, shell))
        if cmd == ["databricks", "--version"]:
            return SimpleNamespace(returncode=0, stdout="Databricks CLI version 0.295.0\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    confirm_called = False
    warnings: list[str] = []

    def fake_confirm(prompt, default=True):
        nonlocal confirm_called
        confirm_called = True
        return True

    monkeypatch.setattr(install_deps.shutil, "which", fake_which)
    monkeypatch.setattr(install_deps.subprocess, "run", fake_run)
    monkeypatch.setattr(install_deps, "confirm", fake_confirm)
    monkeypatch.setattr(install_deps.log, "warn", lambda msg: warnings.append(msg))

    install_deps.install_dependencies(
        DummyAdapter(), PlatformInfo("Linux", False, "", ""), non_interactive=True
    )

    assert confirm_called is False
    assert warnings == [
        "Databricks CLI 0.295.0 is below preferred version 0.296.0; leaving existing install unchanged in non-interactive mode. To upgrade manually, run: curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh -s -- --version 0.296.0"
    ]
    assert not any(
        shell and "databricks/setup-cli" in cmd for cmd, shell in calls if isinstance(cmd, str)
    )
