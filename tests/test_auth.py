"""Tests for auth helpers and Databricks token cache recovery."""

from __future__ import annotations

from pathlib import Path

import fmapi_opskit.auth as auth
from fmapi_opskit.core import PlatformInfo


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


def test_clear_helper_token_cache_removes_cache_and_lock(tmp_path):
    """clear_helper_token_cache should remove cache and lock artifacts."""
    helper = tmp_path / ".claude" / "fmapi-key-helper.sh"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("#!/bin/sh\n")

    cache_file = helper.parent / ".fmapi-token-cache"
    lock_dir = helper.parent / ".fmapi-token-lock"
    cache_file.write_text("stale")
    lock_dir.mkdir()
    (lock_dir / "pid").write_text("123")

    removed = auth.clear_helper_token_cache(str(helper))

    assert removed is True, "Expected cache cleanup to report removals"
    assert not cache_file.exists(), "Token cache file should be removed"
    assert not lock_dir.exists(), "Token lock directory should be removed"


def test_clear_helper_token_cache_noop_when_missing(tmp_path):
    """clear_helper_token_cache should be a no-op when artifacts do not exist."""
    helper = tmp_path / ".claude" / "fmapi-key-helper.sh"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text("#!/bin/sh\n")

    removed = auth.clear_helper_token_cache(str(helper))

    assert removed is False, "Expected no removals when cache artifacts are absent"



def test_get_oauth_token_retries_when_first_token_near_expiry(monkeypatch):
    """Near-expiry token should trigger a retry and return a refreshed token."""
    calls = iter(
        [
            {"access_token": "soon-expiring", "expires_in": 30},
            {"access_token": "fresh-token", "expires_in": 3600},
        ]
    )

    monkeypatch.setattr(auth, "repair_malformed_token_cache", lambda: False)
    monkeypatch.setattr(auth, "run_databricks_json", lambda *args, **kwargs: next(calls))

    token = auth.get_oauth_token("test-profile")

    assert token == "fresh-token", "Expected retry to return a refreshed token"


def test_get_oauth_token_rejects_token_that_stays_near_expiry(monkeypatch):
    """If token never refreshes beyond buffer, helper should treat it as invalid."""
    calls = iter(
        [
            {"access_token": "still-stale", "expires_in": 60},
            {"access_token": "still-stale", "expires_in": 45},
        ]
    )

    monkeypatch.setattr(auth, "repair_malformed_token_cache", lambda: False)
    monkeypatch.setattr(auth, "run_databricks_json", lambda *args, **kwargs: next(calls))

    token = auth.get_oauth_token("test-profile")

    assert token == "", "Expected near-expiry token to be rejected"


def test_authenticate_clears_cache_and_retries_when_token_missing(monkeypatch):
    """authenticate should clear cache and retry login once when token remains missing."""
    token_values = iter(["", "", "fresh-token"])
    login_calls: list[tuple[str, str]] = []
    clear_calls = {"count": 0}

    monkeypatch.setattr(auth, "repair_malformed_token_cache", lambda: False)
    monkeypatch.setattr(auth, "get_oauth_token", lambda profile: next(token_values))
    monkeypatch.setattr(auth, "_cleanup_legacy_pats", lambda profile: None)

    def fake_auth_login(host: str, profile: str) -> bool:
        login_calls.append((host, profile))
        return True

    def fake_clear_token_cache() -> bool:
        clear_calls["count"] += 1
        return True

    monkeypatch.setattr(auth, "auth_login", fake_auth_login)
    monkeypatch.setattr(auth, "clear_token_cache", fake_clear_token_cache)

    pi = PlatformInfo(os_type="Darwin", is_wsl=False, wsl_version="", wsl_distro="")
    auth.authenticate("https://example.cloud.databricks.com", "test-profile", pi)

    assert login_calls == [
        ("https://example.cloud.databricks.com", "test-profile"),
        ("https://example.cloud.databricks.com", "test-profile"),
    ]
    assert clear_calls["count"] == 1, "Expected a single token-cache clear before retry"


def test_clear_token_cache_deletes_cache_file(tmp_path, monkeypatch):
    """clear_token_cache should remove token-cache.json when present."""
    cache_file = _patch_home(monkeypatch, tmp_path)
    cache_file.write_text('{"ok": true}')

    cleared = auth.clear_token_cache()

    assert cleared is True
    assert not cache_file.exists()
