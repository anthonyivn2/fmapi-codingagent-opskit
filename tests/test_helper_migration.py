"""Tests for helper migration during reauth/reinstall flows."""

from __future__ import annotations

from types import SimpleNamespace

from fmapi_opskit import cli
from fmapi_opskit.agents.claudecode import ClaudeCodeAdapter
from fmapi_opskit.commands import reauth as reauth_cmd
from fmapi_opskit.config.models import FileConfig, FmapiConfig
from fmapi_opskit.core import PlatformInfo
from fmapi_opskit.setup import workflow
from fmapi_opskit.setup.writer import helper_needs_migration


def _legacy_helper_text(host: str, profile: str) -> str:
    return f"""#!/bin/sh
set -eu
FMAPI_PROFILE=\"{profile}\"
FMAPI_HOST=\"{host}\"
_fetch_token() {{
  _fmapi_last_expires_in=\"\"
  token=abc
  printf '%s' \"$token\"
}}
token=$(_fetch_token) || true
_write_token_cache \"$token\" \"$_fmapi_last_expires_in\"
"""


def test_helper_needs_migration_detects_legacy_pattern(tmp_path):
    helper_file = tmp_path / ".claude" / "fmapi-key-helper.sh"
    helper_file.parent.mkdir(parents=True, exist_ok=True)
    helper_file.write_text(
        _legacy_helper_text(
            host="https://example.cloud.databricks.com",
            profile="test-profile",
        )
    )

    assert helper_needs_migration(str(helper_file)) is True


def test_do_reauth_migrates_legacy_helper(tmp_path, monkeypatch):
    helper_file = tmp_path / ".claude" / "fmapi-key-helper.sh"
    helper_file.parent.mkdir(parents=True, exist_ok=True)
    helper_file.write_text(
        _legacy_helper_text(
            host="https://example.cloud.databricks.com",
            profile="test-profile",
        )
    )

    cfg = FmapiConfig(
        found=True,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
        helper_file=str(helper_file),
    )

    monkeypatch.setattr(reauth_cmd, "require_fmapi_config", lambda adapter, caller: None)
    monkeypatch.setattr(reauth_cmd, "discover_config", lambda adapter: cfg)
    monkeypatch.setattr(reauth_cmd, "auth_login", lambda host, profile: True)
    monkeypatch.setattr(reauth_cmd, "check_oauth_status", lambda profile: True)
    monkeypatch.setattr(reauth_cmd, "clear_helper_token_cache", lambda helper: False)

    reauth_cmd.do_reauth(ClaudeCodeAdapter())

    helper_text = helper_file.read_text()
    assert "token=$(_fetch_token)" not in helper_text
    assert "_fmapi_last_token" in helper_text


def test_reinstall_migrates_legacy_helper_before_setup(tmp_path, monkeypatch):
    helper_file = tmp_path / ".claude" / "fmapi-key-helper.sh"
    helper_file.parent.mkdir(parents=True, exist_ok=True)
    helper_file.write_text(
        _legacy_helper_text(
            host="https://example.cloud.databricks.com",
            profile="test-profile",
        )
    )

    cfg = FmapiConfig(
        found=True,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
        model="databricks-claude-opus-4-6",
        opus="databricks-claude-opus-4-6",
        sonnet="databricks-claude-sonnet-4-6",
        haiku="databricks-claude-haiku-4-5",
        ttl="55",
        ai_gateway="false",
        helper_file=str(helper_file),
        settings_file=str(tmp_path / ".claude" / "settings.json"),
    )

    called = {"do_setup": False}

    def fake_do_setup(*args, **kwargs):
        called["do_setup"] = True

    monkeypatch.setattr("fmapi_opskit.auth.has_databricks_cli", lambda: True)
    monkeypatch.setattr("fmapi_opskit.config.discovery.discover_config", lambda adapter: cfg)
    monkeypatch.setattr("fmapi_opskit.setup.workflow.do_setup", fake_do_setup)
    monkeypatch.setattr(
        cli,
        "_state",
        {
            "adapter": ClaudeCodeAdapter(),
            "platform": PlatformInfo(
                os_type="Linux",
                is_wsl=False,
                wsl_version="",
                wsl_distro="",
            ),
        },
    )

    cli.reinstall()

    helper_text = helper_file.read_text()
    assert called["do_setup"] is True
    assert "token=$(_fetch_token)" not in helper_text
    assert "_fmapi_last_token" in helper_text


def test_reinstall_refresh_only_migrates_without_running_setup(tmp_path, monkeypatch):
    helper_file = tmp_path / ".claude" / "fmapi-key-helper.sh"
    helper_file.parent.mkdir(parents=True, exist_ok=True)
    helper_file.write_text(
        _legacy_helper_text(
            host="https://example.cloud.databricks.com",
            profile="test-profile",
        )
    )

    cfg = FmapiConfig(
        found=True,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
        model="databricks-claude-opus-4-6",
        opus="databricks-claude-opus-4-6",
        sonnet="databricks-claude-sonnet-4-6",
        haiku="databricks-claude-haiku-4-5",
        ttl="55",
        ai_gateway="false",
        helper_file=str(helper_file),
        settings_file=str(tmp_path / ".claude" / "settings.json"),
    )

    called = {"do_setup": False}

    def fake_do_setup(*args, **kwargs):
        called["do_setup"] = True

    monkeypatch.setattr("fmapi_opskit.auth.has_databricks_cli", lambda: True)
    monkeypatch.setattr("fmapi_opskit.config.discovery.discover_config", lambda adapter: cfg)
    monkeypatch.setattr("fmapi_opskit.setup.workflow.do_setup", fake_do_setup)
    monkeypatch.setattr(
        cli,
        "_state",
        {
            "adapter": ClaudeCodeAdapter(),
            "platform": PlatformInfo(
                os_type="Linux",
                is_wsl=False,
                wsl_version="",
                wsl_distro="",
            ),
        },
    )

    cli.reinstall(refresh_only=True)

    helper_text = helper_file.read_text()
    assert called["do_setup"] is False
    assert "token=$(_fetch_token)" not in helper_text
    assert "_fmapi_last_token" in helper_text


def test_setup_existing_install_uses_reinstall_migration(tmp_path, monkeypatch):
    helper_file = tmp_path / ".claude" / "fmapi-key-helper.sh"
    helper_file.parent.mkdir(parents=True, exist_ok=True)
    helper_file.write_text(
        _legacy_helper_text(
            host="https://example.cloud.databricks.com",
            profile="test-profile",
        )
    )

    settings_file = tmp_path / ".claude" / "settings.json"
    cfg = FmapiConfig(
        found=True,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
        model="databricks-claude-opus-4-6",
        opus="databricks-claude-opus-4-6",
        sonnet="databricks-claude-sonnet-4-6",
        haiku="databricks-claude-haiku-4-5",
        ttl="55",
        ai_gateway="false",
        helper_file=str(helper_file),
        settings_file=str(settings_file),
    )

    calls: dict[str, object] = {
        "migrate_reason": None,
        "gather_non_interactive": None,
    }

    def fake_migrate(adapter, *, helper_file, host, profile, reason):
        calls["migrate_reason"] = reason
        return True

    def fake_gather(*args, **kwargs):
        calls["gather_non_interactive"] = kwargs.get("non_interactive")
        return SimpleNamespace(
            host=cfg.host,
            profile=cfg.profile,
            ttl_ms="3300000",
            ttl_minutes="55",
            ai_gateway_enabled=False,
            pending_workspace_id="",
            settings_file=cfg.settings_file,
            helper_file=cfg.helper_file,
            default_model=cfg.model,
            default_opus=cfg.opus,
            default_sonnet=cfg.sonnet,
            default_haiku=cfg.haiku,
        )

    monkeypatch.setattr(workflow, "discover_config", lambda adapter: cfg)
    monkeypatch.setattr(workflow, "_show_reuse_summary", lambda adapter, cfg: True)
    monkeypatch.setattr(workflow, "migrate_helper_if_needed", fake_migrate)
    monkeypatch.setattr(workflow, "gather_config_pre_auth", fake_gather)
    monkeypatch.setattr(
        workflow,
        "gather_config_models",
        lambda *args, **kwargs: SimpleNamespace(
            model=cfg.model,
            opus=cfg.opus,
            sonnet=cfg.sonnet,
            haiku=cfg.haiku,
        ),
    )

    monkeypatch.setattr(workflow, "install_dependencies", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow, "authenticate", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow, "cleanup_legacy_cache", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow, "write_settings", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow, "write_helper", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow, "cleanup_legacy_hooks", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow, "run_smoke_test", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow, "_print_summary", lambda *args, **kwargs: None)

    adapter = ClaudeCodeAdapter()
    monkeypatch.setattr(adapter, "ensure_onboarding", lambda: None)

    workflow.do_setup(
        adapter,
        PlatformInfo(os_type="Linux", is_wsl=False, wsl_version="", wsl_distro=""),
        cli_host="",
        cli_profile="",
        cli_model="",
        cli_opus="",
        cli_sonnet="",
        cli_haiku="",
        cli_ttl="",
        cli_settings_location="",
        cli_ai_gateway="",
        cli_workspace_id="",
        file_cfg=FileConfig(),
        non_interactive=False,
        dry_run=False,
        script_dir=tmp_path,
    )

    assert calls["migrate_reason"] == "setup (existing installation)"
    assert calls["gather_non_interactive"] is True
