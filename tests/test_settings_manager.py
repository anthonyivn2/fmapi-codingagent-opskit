"""Tests for SettingsManager."""

from __future__ import annotations

import json
import os

from fmapi_opskit.settings.manager import SettingsManager


def test_read_missing_returns_empty(tmp_path):
    mgr = SettingsManager(tmp_path / "nope" / "settings.json")
    result = mgr.read()
    assert result == {}, f"Missing file should return empty dict, got {result}"


def test_read_corrupt_json_returns_empty(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("{corrupt")
    result = SettingsManager(p).read()
    assert result == {}, f"Corrupt JSON should return empty dict, got {result}"


def test_write_read_roundtrip(tmp_path):
    p = tmp_path / "settings.json"
    mgr = SettingsManager(p)
    data = {"env": {"A": "1"}}
    mgr.write(data)
    result = mgr.read()
    assert result == data, f"Roundtrip mismatch: wrote {data}, read {result}"


def test_write_creates_parent_dirs(tmp_path):
    p = tmp_path / "deep" / "nested" / "settings.json"
    SettingsManager(p).write({"key": "val"})
    assert p.is_file(), f"Expected file at {p} to be created with parent dirs"


def test_write_sets_600_permissions(tmp_path):
    p = tmp_path / "settings.json"
    SettingsManager(p).write({"key": "val"})
    actual_mode = os.stat(p).st_mode & 0o777
    assert actual_mode == 0o600, f"Expected permissions 0o600, got {oct(actual_mode)}"


def test_merge_env_adds_keys(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {"KEEP": "v"}}))
    mgr = SettingsManager(p)
    mgr.merge_env({"NEW": "n"}, api_key_helper="/h.sh")
    env = mgr.read()["env"]
    assert env["NEW"] == "n", f"New key should be added, got env={env}"
    assert env["KEEP"] == "v", f"Existing key should be preserved, got env={env}"


def test_merge_env_removes_legacy_keys(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {"KEEP": "v", "OLD": "x"}}))
    mgr = SettingsManager(p)
    mgr.merge_env({"NEW": "n"}, api_key_helper="/h.sh", legacy_cleanup_keys=("OLD",))
    env = mgr.read()["env"]
    assert "OLD" not in env, f"Legacy key 'OLD' should be removed, got env={env}"


def test_merge_env_sets_api_key_helper(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {}}))
    mgr = SettingsManager(p)
    mgr.merge_env({}, api_key_helper="/path/to/helper.sh")
    helper = mgr.read().get("apiKeyHelper")
    assert helper == "/path/to/helper.sh", (
        f"Expected apiKeyHelper='/path/to/helper.sh', got '{helper}'"
    )


def test_merge_env_removes_fmapi_meta(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {}, "_fmapi_meta": {"old": "data"}}))
    mgr = SettingsManager(p)
    mgr.merge_env({}, api_key_helper="/h.sh")
    settings = mgr.read()
    assert "_fmapi_meta" not in settings, (
        f"_fmapi_meta should be removed after merge, got keys: {list(settings.keys())}"
    )


def test_remove_deletes_file_when_empty(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {"ONLY": "m"}, "apiKeyHelper": "/h"}))
    result = SettingsManager(p).remove_fmapi_keys(("ONLY",))
    assert result is True, "Should return True when file is deleted"
    assert not p.is_file(), f"File {p} should be deleted when no keys remain"


def test_remove_keeps_file_when_others_remain(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {"ONLY": "m", "USER_KEY": "keep"}, "apiKeyHelper": "/h"}))
    result = SettingsManager(p).remove_fmapi_keys(("ONLY",))
    assert result is False, "Should return False when file still has content"
    assert p.is_file(), f"File {p} should still exist with remaining keys"
    settings = json.loads(p.read_text())
    assert "USER_KEY" in settings["env"], (
        f"Non-FMAPI key 'USER_KEY' should be preserved, got env={settings.get('env')}"
    )


def test_get_env_value_present(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {"KEY": "val"}}))
    result = SettingsManager(p).get_env_value("KEY")
    assert result == "val", f"Expected 'val' for present key, got '{result}'"


def test_get_env_value_missing(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"env": {}}))
    result = SettingsManager(p).get_env_value("NOPE")
    assert result == "", f"Expected empty string for missing key, got '{result}'"
