"""Regression tests for API key helper token refresh behavior."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

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
  exit 1
fi

echo "unexpected databricks args: $*" >&2
exit 1
"""

    jq_script = """#!/usr/bin/env python3
import base64
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

def emit(value):
    if value is None:
        value = ""
    sys.stdout.write(str(value))

if 'split(".")[1]' in query:
    token = payload.get("access_token")
    if isinstance(token, str) and token:
        parts = token.split(".")
        if len(parts) >= 2 and parts[1]:
            padded = parts[1] + ("=" * (-len(parts[1]) % 4))
            try:
                decoded = base64.urlsafe_b64decode(padded.encode()).decode()
                claims = json.loads(decoded)
                emit(claims.get("exp", ""))
                raise SystemExit(0)
            except Exception:
                pass
    emit("")
    raise SystemExit(0)

if "access_token" in query:
    emit(payload.get("access_token", ""))
    raise SystemExit(0)

if "expires_in" in query or "expiresIn" in query:
    value = payload.get("expires_in", payload.get("expiresIn", ""))
    if value in (None, ""):
        emit("")
        raise SystemExit(0)

    try:
        emit(int(float(value)))
    except Exception:
        emit("")
    raise SystemExit(0)

emit("")
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
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{state_dir.parent / 'bin'}:{env.get('PATH', '')}"
    env["HOME"] = str(home)
    env["FMAPI_TEST_STATE_DIR"] = str(state_dir)

    return subprocess.run(
        [str(helper_file)],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


def test_helper_refreshes_when_expires_in_is_float_string(tmp_path):
    """Near-expiry tokens with float expires_in should still trigger refresh."""
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

    _write_stub_binaries(bin_dir)
    (state_dir / "token-1.json").write_text('{"access_token": "stale-token", "expires_in": "30.5"}')
    (state_dir / "token-2.json").write_text(
        '{"access_token": "refreshed-token", "expires_in": 3600}'
    )

    result = _run_helper(helper_file, home=home_dir, state_dir=state_dir)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "refreshed-token"
    assert (state_dir / "token-count").read_text().strip() == "2"
