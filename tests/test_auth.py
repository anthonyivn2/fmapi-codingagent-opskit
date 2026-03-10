"""Tests for auth helpers and Databricks token cache recovery."""

from __future__ import annotations

import base64
import json
import subprocess
import time
from pathlib import Path

import fmapi_opskit.auth as auth


def _make_jwt_with_exp(exp_epoch: int) -> str:
    """Build an unsigned JWT token containing an exp claim."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode()
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp_epoch}).encode()).decode()
    return f"{header.rstrip('=')}.{payload.rstrip('=')}.sig"


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


def test_get_oauth_token_forces_cache_refresh_when_first_token_near_expiry(monkeypatch):
    """Near-expiry first token should force Databricks cache refresh before retry."""
    calls = iter(
        [
            {"access_token": "soon-expiring", "expires_in": 30},
            {"access_token": "fresh-token", "expires_in": 3600},
        ]
    )
    refresh_calls = {"count": 0}

    monkeypatch.setattr(auth, "repair_malformed_token_cache", lambda: False)
    monkeypatch.setattr(auth, "run_databricks_json", lambda *args, **kwargs: next(calls))

    def fake_force_refresh_databricks_token_cache() -> bool:
        refresh_calls["count"] += 1
        return True

    monkeypatch.setattr(
        auth,
        "_force_refresh_databricks_token_cache",
        fake_force_refresh_databricks_token_cache,
    )

    token = auth.get_oauth_token("test-profile")

    assert token == "fresh-token"
    assert refresh_calls["count"] == 1, "Expected one forced cache refresh before retry"


def test_get_oauth_token_does_not_force_refresh_when_token_missing(monkeypatch):
    """Missing first token should not force-refresh cache before retry."""
    calls = iter(
        [
            None,
            {"access_token": "fresh-token", "expires_in": 3600},
        ]
    )
    refresh_calls = {"count": 0}

    monkeypatch.setattr(auth, "repair_malformed_token_cache", lambda: False)
    monkeypatch.setattr(auth, "run_databricks_json", lambda *args, **kwargs: next(calls))

    def fake_force_refresh_databricks_token_cache() -> bool:
        refresh_calls["count"] += 1
        return True

    monkeypatch.setattr(
        auth,
        "_force_refresh_databricks_token_cache",
        fake_force_refresh_databricks_token_cache,
    )

    token = auth.get_oauth_token("test-profile")

    assert token == "fresh-token"
    assert refresh_calls["count"] == 0, "Cache refresh should not run when token is missing"


def test_get_oauth_token_retries_when_expiry_only_in_jwt_claim(monkeypatch):
    """Near-expiry JWT should trigger retry even without expires_in metadata."""
    now = int(time.time())
    stale_jwt = _make_jwt_with_exp(now + 30)
    fresh_jwt = _make_jwt_with_exp(now + 3600)

    calls = iter(
        [
            {"access_token": stale_jwt},
            {"access_token": fresh_jwt},
        ]
    )

    monkeypatch.setattr(auth, "repair_malformed_token_cache", lambda: False)
    monkeypatch.setattr(auth, "run_databricks_json", lambda *args, **kwargs: next(calls))

    token = auth.get_oauth_token("test-profile")

    assert token == fresh_jwt, "Expected JWT exp claim fallback to trigger retry"


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

    auth.authenticate("https://example.cloud.databricks.com", "test-profile")

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


# ---------------------------------------------------------------------------
# Polling tests
# ---------------------------------------------------------------------------


def test_poll_for_token_returns_true_when_token_appears(monkeypatch):
    """Polling should return True once a valid token is found."""
    call_count = {"n": 0}

    def fake_get_oauth_token(profile: str) -> str:
        call_count["n"] += 1
        return "fresh-token" if call_count["n"] >= 3 else ""

    monkeypatch.setattr(auth, "get_oauth_token", fake_get_oauth_token)
    monkeypatch.setattr(auth, "_POLL_INTERVAL", 0.01)

    result = auth._poll_for_token("test-profile", timeout=10)
    assert result is True
    assert call_count["n"] >= 3


def test_poll_for_token_returns_false_on_timeout(monkeypatch):
    """Polling should return False when timeout is reached without a token."""
    monkeypatch.setattr(auth, "get_oauth_token", lambda profile: "")
    monkeypatch.setattr(auth, "_POLL_INTERVAL", 0.01)

    result = auth._poll_for_token("test-profile", timeout=0.05)
    assert result is False


# ---------------------------------------------------------------------------
# auth_login integration test
# ---------------------------------------------------------------------------


def test_auth_login_polls_for_token_without_oauth_url_display(tmp_path, monkeypatch):
    """auth_login should poll token availability without URL extraction/display."""
    _patch_home(monkeypatch, tmp_path)

    poll_called = {"called": False}

    class FakePopen:
        def __init__(self, *args, **kwargs):
            self.stdout = iter([])
            self.stderr = iter([])
            self.returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return 0

        def terminate(self):
            self.returncode = -15

        def kill(self):
            pass

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    def fake_poll_for_token(profile: str, timeout: int = 300, *, stop_when=None) -> bool:
        poll_called["called"] = True
        assert callable(stop_when)
        return True

    monkeypatch.setattr(auth, "_poll_for_token", fake_poll_for_token)

    ok = auth.auth_login("https://dbc-test.cloud.databricks.com", "test-profile")

    assert ok is True
    assert poll_called["called"] is True
