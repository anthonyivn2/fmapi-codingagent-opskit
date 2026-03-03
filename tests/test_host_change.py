"""Tests for workspace_id and host normalization during reinstallation.

Covers the bug where switching workspace URLs would carry over a stale
workspace_id from the previous configuration instead of forcing re-detection.
"""

from __future__ import annotations

import json

from fmapi_opskit.agents.claudecode import ClaudeCodeAdapter
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.config.loader import load_config_file
from fmapi_opskit.config.models import FileConfig, FmapiConfig
from fmapi_opskit.setup.gather import gather_config_pre_auth


# ---------------------------------------------------------------------------
# Helper to run gather_config_pre_auth in non-interactive mode
# ---------------------------------------------------------------------------


def _run_gather(
    adapter: ClaudeCodeAdapter,
    cfg: FmapiConfig,
    file_cfg: FileConfig | None = None,
    *,
    cli_host: str = "",
    cli_workspace_id: str = "",
    cli_ai_gateway: str = "true",
) -> object:
    """Run gather_config_pre_auth in non-interactive mode and return the result."""
    return gather_config_pre_auth(
        adapter,
        cfg,
        file_cfg or FileConfig(),
        cli_host=cli_host,
        cli_profile="test-profile",
        cli_ttl="60",
        cli_ai_gateway=cli_ai_gateway,
        cli_workspace_id=cli_workspace_id,
        cli_settings_location="home",
        cli_model="m",
        cli_opus="o",
        cli_sonnet="s",
        cli_haiku="h",
        non_interactive=True,
    )


# ---------------------------------------------------------------------------
# gather_config_pre_auth: workspace_id cleared on host change
# ---------------------------------------------------------------------------


def test_workspace_id_cleared_when_host_changes(adapter):
    """Switching to a new workspace URL must drop the old workspace_id."""
    old_cfg = FmapiConfig(
        host="https://old-workspace.cloud.databricks.com",
        workspace_id="1111111111111111",
        ai_gateway="true",
    )
    result = _run_gather(
        adapter, old_cfg, cli_host="https://new-workspace.cloud.databricks.com"
    )
    assert result.pending_workspace_id == "", (
        f"Expected empty workspace_id after host change, got '{result.pending_workspace_id}'"
    )


def test_workspace_id_kept_when_host_same(adapter):
    """Re-running setup with the same host should keep the existing workspace_id."""
    host = "https://same-workspace.cloud.databricks.com"
    old_cfg = FmapiConfig(
        host=host,
        workspace_id="2222222222222222",
        ai_gateway="true",
    )
    result = _run_gather(adapter, old_cfg, cli_host=host)
    assert result.pending_workspace_id == "2222222222222222", (
        f"Expected preserved workspace_id '2222222222222222', "
        f"got '{result.pending_workspace_id}'"
    )


def test_workspace_id_cleared_with_trailing_slash_mismatch(adapter):
    """Host with trailing slash in old config should still match after normalization."""
    old_cfg = FmapiConfig(
        host="https://workspace.cloud.databricks.com/",
        workspace_id="3333333333333333",
        ai_gateway="true",
    )
    # Same host without trailing slash — should be treated as same workspace
    result = _run_gather(
        adapter, old_cfg, cli_host="https://workspace.cloud.databricks.com"
    )
    assert result.pending_workspace_id == "3333333333333333", (
        f"Trailing slash should not cause host mismatch, "
        f"got '{result.pending_workspace_id}'"
    )


def test_cli_workspace_id_overrides_stale_config(adapter):
    """Explicit --workspace-id should always win, even when host changes."""
    old_cfg = FmapiConfig(
        host="https://old.cloud.databricks.com",
        workspace_id="1111111111111111",
        ai_gateway="true",
    )
    result = _run_gather(
        adapter,
        old_cfg,
        cli_host="https://new.cloud.databricks.com",
        cli_workspace_id="9999999999999999",
    )
    assert result.pending_workspace_id == "9999999999999999", (
        f"--workspace-id should override stale config, "
        f"got '{result.pending_workspace_id}'"
    )


def test_file_cfg_workspace_id_used_when_cfg_stale(adapter):
    """Config file workspace_id should be used even when discovered config is stale."""
    old_cfg = FmapiConfig(
        host="https://old.cloud.databricks.com",
        workspace_id="1111111111111111",
        ai_gateway="true",
    )
    file_cfg = FileConfig(workspace_id="5555555555555555")
    result = _run_gather(
        adapter,
        old_cfg,
        file_cfg,
        cli_host="https://new.cloud.databricks.com",
    )
    assert result.pending_workspace_id == "5555555555555555", (
        f"Config file workspace_id should be used, got '{result.pending_workspace_id}'"
    )


# ---------------------------------------------------------------------------
# loader: host trailing slash normalization
# ---------------------------------------------------------------------------


def test_loader_strips_trailing_slash(tmp_path):
    """Config file host with trailing slash should be normalized."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"host": "https://example.cloud.databricks.com/"}))
    cfg = load_config_file(str(p))
    assert cfg.host == "https://example.cloud.databricks.com", (
        f"Loader should strip trailing slash, got '{cfg.host}'"
    )


# ---------------------------------------------------------------------------
# discovery: host trailing slash normalization from helper script
# ---------------------------------------------------------------------------


def _write_settings_and_helper(
    tmp_path, host: str, workspace_id: str = "", profile: str = "test"
) -> ClaudeCodeAdapter:
    """Write a settings.json + helper script and return an adapter pointing at them."""
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()

    helper_path = settings_dir / "fmapi-key-helper.sh"
    helper_path.write_text(
        f'FMAPI_PROFILE="{profile}"\nFMAPI_HOST="{host}"\necho "token"\n'
    )
    helper_path.chmod(0o700)

    if workspace_id:
        base_url = f"https://{workspace_id}.ai-gateway.cloud.databricks.com/anthropic"
    else:
        base_url = f"{host}/serving-endpoints/anthropic"

    settings = {
        "env": {
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_MODEL": "databricks-claude-opus-4-6",
        },
        "apiKeyHelper": str(helper_path),
    }
    settings_file = settings_dir / "settings.json"
    settings_file.write_text(json.dumps(settings))

    adapter = ClaudeCodeAdapter()
    # Override settings_candidates to point at our tmp file
    adapter.settings_candidates = lambda: [settings_file]  # type: ignore[assignment]
    return adapter


def test_discovery_strips_trailing_slash_from_host(tmp_path):
    """Discovered host from helper script should have trailing slash removed."""
    adapter = _write_settings_and_helper(
        tmp_path, host="https://workspace.cloud.databricks.com/"
    )
    cfg = discover_config(adapter)
    assert cfg.host == "https://workspace.cloud.databricks.com", (
        f"Discovery should strip trailing slash from host, got '{cfg.host}'"
    )


def test_discovery_host_without_slash_unchanged(tmp_path):
    """Discovered host without trailing slash should be unchanged."""
    adapter = _write_settings_and_helper(
        tmp_path, host="https://workspace.cloud.databricks.com"
    )
    cfg = discover_config(adapter)
    assert cfg.host == "https://workspace.cloud.databricks.com", (
        f"Host without slash should be unchanged, got '{cfg.host}'"
    )


def test_discovery_extracts_workspace_id_from_gateway_url(tmp_path):
    """Discovery should extract workspace_id from AI Gateway base URL."""
    adapter = _write_settings_and_helper(
        tmp_path,
        host="https://workspace.cloud.databricks.com",
        workspace_id="4444444444444444",
    )
    cfg = discover_config(adapter)
    assert cfg.workspace_id == "4444444444444444", (
        f"Expected workspace_id '4444444444444444', got '{cfg.workspace_id}'"
    )
    assert cfg.ai_gateway == "true", (
        f"Expected ai_gateway='true', got '{cfg.ai_gateway}'"
    )
