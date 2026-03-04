"""Template and rendered helper-script validity/behavior tests."""

from __future__ import annotations

import json
import os
import subprocess
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
  exit 0
fi

echo "unexpected databricks args: $*" >&2
exit 1
"""

    jq_script = """#!/usr/bin/env python3
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

if "access_token" in query:
    print_raw(payload.get("access_token", ""))
    raise SystemExit(0)

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
        normalized = expiry_value.replace("Z", "+00:00") if expiry_value.endswith("Z") else expiry_value
        try:
            expiry_dt = datetime.datetime.fromisoformat(normalized)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=datetime.timezone.utc)
            seconds = int((expiry_dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds())
            print_raw(seconds)
            raise SystemExit(0)
        except Exception:
            pass

print_raw("")
"""

    databricks_path = bin_dir / "databricks"
    jq_path = bin_dir / "jq"
    databricks_path.write_text(databricks_script)
    jq_path.write_text(jq_script)
    databricks_path.chmod(0o700)
    jq_path.chmod(0o700)


def _run_helper(helper_file: Path, *, home: Path, state_dir: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{state_dir.parent / 'bin'}:{env.get('PATH', '')}"
    env["HOME"] = str(home)
    env["FMAPI_TEST_STATE_DIR"] = str(state_dir)
    env.pop("SSH_CONNECTION", None)
    env.pop("SSH_TTY", None)

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

