"""Template and rendered helper-script validity/behavior tests."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import time
from pathlib import Path

from fmapi_opskit.agents.claudecode import ClaudeCodeAdapter
from fmapi_opskit.setup.writer import write_helper, write_settings
from fmapi_opskit.templates.renderer import render_template


def _helper_template_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "src"
        / "fmapi_opskit"
        / "templates"
        / "fmapi-key-helper.sh.template"
    )


def _render_helper_for_test(tmp_path: Path, host: str, profile: str) -> Path:
    helper_file = tmp_path / ".claude" / "fmapi-key-helper.sh"
    render_template(
        _helper_template_path(),
        helper_file,
        {
            "PROFILE": profile,
            "HOST": host,
            "SETUP_SCRIPT": "setup-fmapi-claudecode",
        },
        mode=0o700,
    )
    return helper_file


def _make_jwt_with_exp(exp_epoch: int) -> str:
    """Build an unsigned JWT token containing an exp claim."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode()
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp_epoch}).encode()).decode()
    return f"{header.rstrip('=')}.{payload.rstrip('=')}.sig"


def _write_stub_binaries(bin_dir: Path) -> None:
    databricks_script = """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "token" ]; then
  _count_file="${FMAPI_TEST_STATE_DIR}/token-count"
  _count=0
  if [ -f "$_count_file" ]; then
    _count=$(cat "$_count_file")
  fi
  _count=$(( _count + 1 ))
  printf '%s' "$_count" > "$_count_file"

  _resp="${FMAPI_TEST_STATE_DIR}/token-${_count}.json"
  if [ ! -f "$_resp" ]; then
    _resp="${FMAPI_TEST_STATE_DIR}/token-default.json"
  fi
  cat "$_resp"
  exit 0
fi

if [ "$1" = "auth" ] && [ "$2" = "login" ]; then
  _browser_file="${FMAPI_TEST_STATE_DIR}/login-browser.txt"
  printf '%s' "${BROWSER:-}" > "$_browser_file"

  _stdout_file="${FMAPI_TEST_STATE_DIR}/login-stdout.txt"
  if [ -f "$_stdout_file" ]; then
    cat "$_stdout_file"
  fi

  _stderr_file="${FMAPI_TEST_STATE_DIR}/login-stderr.txt"
  if [ -f "$_stderr_file" ]; then
    cat "$_stderr_file" >&2
  fi

  _sleep_file="${FMAPI_TEST_STATE_DIR}/login-sleep-seconds"
  if [ -f "$_sleep_file" ]; then
    _sleep_seconds=$(cat "$_sleep_file")
    case "$_sleep_seconds" in
      ''|*[!0-9]*) _sleep_seconds=0 ;;
    esac
    if [ "$_sleep_seconds" -gt 0 ]; then
      sleep "$_sleep_seconds"
    fi
  fi

  _exit_file="${FMAPI_TEST_STATE_DIR}/login-exit-code"
  if [ -f "$_exit_file" ]; then
    _code=$(cat "$_exit_file")
    case "$_code" in
      ''|*[!0-9]*) _code=1 ;;
    esac
    exit "$_code"
  fi

  exit 0
fi

echo "unexpected databricks args: $*" >&2
exit 1
"""

    jq_script = """#!/usr/bin/env python3
import base64
import datetime
import json
import sys

query = ""
for arg in sys.argv[1:]:
    if not arg.startswith("-"):
        query = arg
        break

try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}

def print_raw(value):
    if value is None:
        sys.stdout.write("")
        return
    sys.stdout.write(str(value))

if "expires_in" in query or "expiresIn" in query or "fromdateiso8601" in query:
    expires_in = payload.get("expires_in", payload.get("expiresIn"))
    if expires_in is not None:
        try:
            print_raw(int(float(expires_in)))
        except Exception:
            print_raw("")
        raise SystemExit(0)

    expiry_value = payload.get("expiry") or payload.get("expires_at") or payload.get("expiresAt")
    if isinstance(expiry_value, str) and expiry_value:
        normalized = (
            expiry_value.replace("Z", "+00:00") if expiry_value.endswith("Z") else expiry_value
        )
        try:
            expiry_dt = datetime.datetime.fromisoformat(normalized)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=datetime.timezone.utc)
            seconds = int(
                (expiry_dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
            )
            print_raw(seconds)
            raise SystemExit(0)
        except Exception:
            pass

    token = payload.get("access_token")
    if 'split(".")' in query and isinstance(token, str) and token:
        parts = token.split(".")
        if len(parts) >= 2 and parts[1]:
            padded = parts[1] + ("=" * (-len(parts[1]) % 4))
            try:
                decoded = base64.urlsafe_b64decode(padded.encode()).decode()
                token_payload = json.loads(decoded)
                exp_epoch = token_payload.get("exp")
                if exp_epoch is not None:
                    print_raw(int(float(exp_epoch) - datetime.datetime.now(datetime.timezone.utc).timestamp()))
                    raise SystemExit(0)
            except Exception:
                pass

    print_raw("")
    raise SystemExit(0)

if "access_token" in query:
    print_raw(payload.get("access_token", ""))
    raise SystemExit(0)

print_raw("")
"""

    databricks_path = bin_dir / "databricks"
    jq_path = bin_dir / "jq"
    databricks_path.write_text(databricks_script)
    jq_path.write_text(jq_script)
    databricks_path.chmod(0o700)
    jq_path.chmod(0o700)


def _run_helper(
    helper_file: Path,
    *,
    home: Path,
    state_dir: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{state_dir.parent / 'bin'}:{env.get('PATH', '')}"
    env["HOME"] = str(home)
    env["FMAPI_TEST_STATE_DIR"] = str(state_dir)
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        [str(helper_file)],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


def test_helper_template_is_shell_valid(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    check = subprocess.run(["sh", "-n", str(helper_file)], capture_output=True, text=True)

    assert check.returncode == 0, f"Expected shell-valid helper template, got: {check.stderr}"


def test_api_key_helper_written_to_settings_is_shell_valid(tmp_path):
    adapter = ClaudeCodeAdapter()
    settings_file = tmp_path / ".claude" / "settings.json"
    helper_file = tmp_path / ".claude" / "fmapi-key-helper.sh"

    write_settings(
        adapter,
        settings_file=str(settings_file),
        helper_file=str(helper_file),
        host="https://example.cloud.databricks.com",
        model="databricks-claude-opus-4-6",
        opus="databricks-claude-opus-4-6",
        sonnet="databricks-claude-sonnet-4-6",
        haiku="databricks-claude-haiku-4-5",
        ttl_ms="3600000",
        ai_gateway_enabled=False,
        workspace_id="",
    )
    write_helper(
        adapter,
        helper_file=str(helper_file),
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    settings = json.loads(settings_file.read_text())
    api_key_helper = Path(settings["apiKeyHelper"])
    check = subprocess.run(["sh", "-n", str(api_key_helper)], capture_output=True, text=True)

    assert api_key_helper == helper_file
    assert check.returncode == 0, f"Expected shell-valid apiKeyHelper script, got: {check.stderr}"


def test_helper_returns_token_with_stubbed_databricks(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    state_dir.mkdir()
    home_dir.mkdir()
    (home_dir / ".claude").mkdir(parents=True, exist_ok=True)

    _write_stub_binaries(bin_dir)
    (state_dir / "token-default.json").write_text(
        '{"access_token": "fresh-token", "expires_in": 3600}'
    )

    result = _run_helper(helper_file, home=home_dir, state_dir=state_dir)
    cache_file = home_dir / ".claude" / ".fmapi-token-cache"

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fresh-token"
    assert cache_file.is_file(), "Expected helper token cache to be written"


def test_helper_retries_near_expiry_and_returns_refreshed_token(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    state_dir.mkdir()
    home_dir.mkdir()
    (home_dir / ".claude").mkdir(parents=True, exist_ok=True)

    _write_stub_binaries(bin_dir)
    (state_dir / "token-1.json").write_text('{"access_token": "stale-token", "expires_in": 30}')
    (state_dir / "token-2.json").write_text(
        '{"access_token": "refreshed-token", "expires_in": 3600}'
    )

    result = _run_helper(helper_file, home=home_dir, state_dir=state_dir)
    calls = (state_dir / "token-count").read_text().strip()

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "refreshed-token"
    assert calls == "2", f"Expected 2 token calls (retry path), got {calls}"


def test_helper_retries_when_expiry_only_in_jwt_claim(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    state_dir.mkdir()
    home_dir.mkdir()
    (home_dir / ".claude").mkdir(parents=True, exist_ok=True)

    _write_stub_binaries(bin_dir)
    now = int(time.time())
    stale_jwt = _make_jwt_with_exp(now + 30)
    fresh_jwt = _make_jwt_with_exp(now + 3600)
    (state_dir / "token-1.json").write_text(json.dumps({"access_token": stale_jwt}))
    (state_dir / "token-2.json").write_text(json.dumps({"access_token": fresh_jwt}))

    result = _run_helper(helper_file, home=home_dir, state_dir=state_dir)
    calls = (state_dir / "token-count").read_text().strip()

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == fresh_jwt
    assert calls == "2", f"Expected 2 token calls (retry path), got {calls}"


def test_helper_reauth_routes_login_output_to_stderr(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    state_dir.mkdir()
    home_dir.mkdir()
    (home_dir / ".claude").mkdir(parents=True, exist_ok=True)

    _write_stub_binaries(bin_dir)
    (state_dir / "token-1.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-2.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-default.json").write_text(
        '{"access_token": "fresh-after-reauth", "expires_in": 3600}'
    )
    (state_dir / "login-stdout.txt").write_text("Opening https://example/login\n")

    result = _run_helper(helper_file, home=home_dir, state_dir=state_dir)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fresh-after-reauth"
    assert "Opening https://example/login" in result.stderr


def test_helper_reauth_returns_before_long_login_process_exits(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    state_dir.mkdir()
    home_dir.mkdir()
    (home_dir / ".claude").mkdir(parents=True, exist_ok=True)

    _write_stub_binaries(bin_dir)
    (state_dir / "token-1.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-2.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-default.json").write_text(
        '{"access_token": "fresh-after-reauth", "expires_in": 3600}'
    )
    (state_dir / "login-sleep-seconds").write_text("5")
    (state_dir / "login-stdout.txt").write_text("Opening https://example/login\n")

    start = time.monotonic()
    result = _run_helper(helper_file, home=home_dir, state_dir=state_dir)
    elapsed = time.monotonic() - start

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fresh-after-reauth"
    assert (state_dir / "login-browser.txt").exists(), "Expected login flow to be triggered"
    assert elapsed < 4, f"Expected helper to continue before login exit, took {elapsed:.2f}s"


def test_helper_treats_wayland_as_display_for_ssh_reauth(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    state_dir.mkdir()
    home_dir.mkdir()
    (home_dir / ".claude").mkdir(parents=True, exist_ok=True)

    _write_stub_binaries(bin_dir)
    (state_dir / "token-1.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-2.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-default.json").write_text(
        '{"access_token": "fresh-wayland", "expires_in": 3600}'
    )

    result = _run_helper(
        helper_file,
        home=home_dir,
        state_dir=state_dir,
        extra_env={
            "SSH_CONNECTION": "10.0.0.1 50000 10.0.0.2 22",
            "WAYLAND_DISPLAY": "wayland-0",
        },
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fresh-wayland"


def test_helper_headless_ssh_reauth_uses_browser_none(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    state_dir.mkdir()
    home_dir.mkdir()
    (home_dir / ".claude").mkdir(parents=True, exist_ok=True)

    _write_stub_binaries(bin_dir)
    (state_dir / "token-1.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-2.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-default.json").write_text(
        '{"access_token": "fresh-headless", "expires_in": 3600}'
    )
    (state_dir / "login-stdout.txt").write_text(
        "Opening https://example.cloud.databricks.com/oidc/v1/authorize\n"
    )

    result = _run_helper(
        helper_file,
        home=home_dir,
        state_dir=state_dir,
        extra_env={
            "SSH_CONNECTION": "10.0.0.1 50000 10.0.0.2 22",
            "DISPLAY": "",
            "WAYLAND_DISPLAY": "",
        },
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "fresh-headless"
    assert "Open the Databricks login URL" in result.stderr
    assert (state_dir / "login-browser.txt").read_text() == "none"


def test_helper_reauth_failure_mentions_claude_slash_command(tmp_path):
    helper_file = _render_helper_for_test(
        tmp_path,
        host="https://example.cloud.databricks.com",
        profile="test-profile",
    )

    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    home_dir = tmp_path / "home"
    bin_dir.mkdir()
    state_dir.mkdir()
    home_dir.mkdir()
    (home_dir / ".claude").mkdir(parents=True, exist_ok=True)

    _write_stub_binaries(bin_dir)
    (state_dir / "token-1.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-2.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "token-default.json").write_text('{"access_token": "", "expires_in": 0}')
    (state_dir / "login-exit-code").write_text("1")

    result = _run_helper(helper_file, home=home_dir, state_dir=state_dir)

    assert result.returncode == 1
    assert "/fmapi-codingagent-reauth" in result.stderr
