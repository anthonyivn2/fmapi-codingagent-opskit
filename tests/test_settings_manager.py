"""Tests for SettingsManager: read, write, merge, cleanup."""

from __future__ import annotations

import json
import stat

from fmapi_opskit.settings.manager import SettingsManager


def test_read_empty_settings(tmp_settings):
    mgr = SettingsManager(tmp_settings)
    assert mgr.read() == {}


def test_write_creates_file(tmp_path):
    p = tmp_path / ".claude" / "settings.json"
    mgr = SettingsManager(p)
    mgr.write({"key": "value"})
    assert p.is_file()
    assert json.loads(p.read_text()) == {"key": "value"}


def test_write_creates_parent_dirs(tmp_path):
    p = tmp_path / "deep" / "nested" / "settings.json"
    mgr = SettingsManager(p)
    mgr.write({"a": 1})
    assert p.is_file()


def test_write_sets_owner_permissions(tmp_path):
    p = tmp_path / "settings.json"
    mgr = SettingsManager(p)
    mgr.write({"x": 1})
    mode = p.stat().st_mode
    assert mode & stat.S_IRWXO == 0  # no other permissions
    assert mode & stat.S_IRWXG == 0  # no group permissions


def test_merge_env_adds_keys_and_helper(tmp_settings):
    mgr = SettingsManager(tmp_settings)
    mgr.merge_env(
        {"ANTHROPIC_MODEL": "test-model"},
        api_key_helper="/path/to/helper.sh",
    )
    settings = mgr.read()
    assert settings["env"]["ANTHROPIC_MODEL"] == "test-model"
    assert settings["apiKeyHelper"] == "/path/to/helper.sh"


def test_merge_env_preserves_existing(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {"OTHER_KEY": "other_value"}}))
    mgr = SettingsManager(p)
    mgr.merge_env(
        {"ANTHROPIC_MODEL": "m"},
        api_key_helper="/helper.sh",
    )
    settings = mgr.read()
    assert settings["env"]["OTHER_KEY"] == "other_value"
    assert settings["env"]["ANTHROPIC_MODEL"] == "m"


def test_merge_env_removes_legacy_keys(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {"ANTHROPIC_AUTH_TOKEN": "old", "KEEP": "v"}}))
    mgr = SettingsManager(p)
    mgr.merge_env(
        {"NEW_KEY": "val"},
        api_key_helper="/helper.sh",
        legacy_cleanup_keys=("ANTHROPIC_AUTH_TOKEN",),
    )
    settings = mgr.read()
    assert "ANTHROPIC_AUTH_TOKEN" not in settings["env"]
    assert settings["env"]["KEEP"] == "v"


def test_set_api_key_helper(tmp_settings):
    mgr = SettingsManager(tmp_settings)
    mgr.set_api_key_helper("/path/to/helper.sh")
    settings = mgr.read()
    assert settings["apiKeyHelper"] == "/path/to/helper.sh"


def test_remove_fmapi_keys(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_MODEL": "m",
                    "ANTHROPIC_BASE_URL": "u",
                    "OTHER_KEY": "v",
                },
                "apiKeyHelper": "/path/to/helper.sh",
                "_fmapi_meta": {"version": "1"},
            }
        )
    )
    mgr = SettingsManager(p)
    uninstall_keys = (
        "ANTHROPIC_MODEL",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
    )
    mgr.remove_fmapi_keys(uninstall_keys)
    settings = mgr.read()
    assert "apiKeyHelper" not in settings
    assert "_fmapi_meta" not in settings
    assert settings["env"]["OTHER_KEY"] == "v"
    assert "ANTHROPIC_MODEL" not in settings["env"]


def test_remove_fmapi_keys_removes_empty_env(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(
        json.dumps(
            {
                "env": {"ANTHROPIC_MODEL": "m"},
                "apiKeyHelper": "/path",
            }
        )
    )
    mgr = SettingsManager(p)
    deleted = mgr.remove_fmapi_keys(("ANTHROPIC_MODEL",))
    # File should be deleted since nothing remains
    assert deleted is True
    assert not p.is_file()


def test_get_env_value(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {"KEY": "val"}}))
    mgr = SettingsManager(p)
    assert mgr.get_env_value("KEY") == "val"
    assert mgr.get_env_value("MISSING") == ""


def test_get_api_key_helper(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"apiKeyHelper": "/path/helper.sh"}))
    mgr = SettingsManager(p)
    assert mgr.get_api_key_helper() == "/path/helper.sh"


def test_get_api_key_helper_empty(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("{}")
    mgr = SettingsManager(p)
    assert mgr.get_api_key_helper() == ""


def test_roundtrip_read_write(tmp_settings):
    mgr = SettingsManager(tmp_settings)
    data = {"env": {"A": "1"}, "apiKeyHelper": "/x"}
    mgr.write(data)
    assert mgr.read() == data
