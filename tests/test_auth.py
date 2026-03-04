"""Tests for auth helpers and Databricks token cache recovery."""

from __future__ import annotations

from pathlib import Path

import fmapi_opskit.auth as auth


def _patch_home(monkeypatch, tmp_path: Path) -> Path:
    """Point Path.home() to tmp_path and return cache file path."""
    cache_file = tmp_path / ".databricks" / "token-cache.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(auth.Path, "home", classmethod(lambda cls: tmp_path))
    return cache_file


def test_repair_malformed_token_cache_removes_invalid_json(tmp_path, monkeypatch):
    """Malformed token cache should be deleted and reported as repaired."""
    cache_file = _patch_home(monkeypatch, tmp_path)
    cache_file.write_text('{"broken": true}}')

    repaired = auth.repair_malformed_token_cache()

    assert repaired is True, "Expected malformed cache to be repaired"
    assert not cache_file.exists(), "Malformed cache file should be removed"


def test_repair_malformed_token_cache_keeps_valid_json(tmp_path, monkeypatch):
    """Valid token cache should not be modified."""
    cache_file = _patch_home(monkeypatch, tmp_path)
    cache_file.write_text('{"ok": true}')

    repaired = auth.repair_malformed_token_cache()

    assert repaired is False, "Valid cache should not be reported as repaired"
    assert cache_file.exists(), "Valid cache file should remain"


def test_auth_login_repairs_cache_before_login(tmp_path, monkeypatch):
    """auth_login should remove malformed cache before invoking login command."""
    cache_file = _patch_home(monkeypatch, tmp_path)
    cache_file.write_text('{"broken": true}}')

    def fake_run_databricks(*args, **kwargs):
        assert not cache_file.exists(), "Cache should be repaired before login command"
        assert args == ("auth", "login", "--host", "https://example.cloud.databricks.com")
        assert kwargs["profile"] == "test-profile"
        assert kwargs["capture_output"] is False
        assert kwargs["timeout"] == 120
        return auth.DatabricksResult(success=True)

    monkeypatch.setattr(auth, "run_databricks", fake_run_databricks)

    ok = auth.auth_login("https://example.cloud.databricks.com", "test-profile")

    assert ok is True, "Expected auth_login success from mocked CLI result"


def test_get_oauth_token_repairs_cache_before_fetch(tmp_path, monkeypatch):
    """get_oauth_token should repair malformed cache before auth token fetch."""
    cache_file = _patch_home(monkeypatch, tmp_path)
    cache_file.write_text('{"broken": true}}')

    def fake_run_databricks_json(*args, **kwargs):
        assert not cache_file.exists(), "Cache should be repaired before token fetch"
        assert args == ("auth", "token")
        assert kwargs["profile"] == "test-profile"
        return {"access_token": "abc"}

    monkeypatch.setattr(auth, "run_databricks_json", fake_run_databricks_json)

    token = auth.get_oauth_token("test-profile")

    assert token == "abc", f"Expected access token from mocked JSON response, got '{token}'"
