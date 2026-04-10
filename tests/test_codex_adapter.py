"""Tests for CodexAdapter — TOML-based configuration."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import tomli_w

from fmapi_opskit.agents.codex import CODEX_CONFIG, SKILL_NAMES, CodexAdapter
from fmapi_opskit.config.discovery import discover_config


@pytest.fixture
def codex_adapter() -> CodexAdapter:
    return CodexAdapter()


@pytest.fixture
def codex_config():
    return CODEX_CONFIG


@pytest.fixture
def sample_codex_toml_data() -> dict:
    """Return a parsed TOML config dict matching the Codex schema."""
    return {
        "profile": "codinggateway-codex-profile",
        "profiles": {
            "codinggateway-codex-profile": {
                "model_provider": "Databricks",
                "model": "databricks-gpt-5-2",
                "model_reasoning_effort": "high",
            }
        },
        "model_providers": {
            "Databricks": {
                "name": "Databricks FMAPI",
                "base_url": "https://example.com/serving-endpoints/openai/v1",
                "wire_api": "responses",
                "auth": {
                    "command": "/home/user/.codex/fmapi-key-helper.sh",
                    "refresh_interval_ms": 3300000,
                    "timeout_ms": 10000,
                },
            }
        },
    }


# --- AgentConfig identity tests ---


def test_codex_config_identity(codex_config):
    assert codex_config.id == "codex"
    assert codex_config.name == "Codex"
    assert codex_config.cli_cmd == "codex"
    assert codex_config.setup_cmd == "setup-fmapi-codex"


def test_codex_config_settings_paths(codex_config):
    assert codex_config.settings_dir == ".codex"
    assert codex_config.settings_filename == "config.toml"
    assert codex_config.helper_filename == "fmapi-key-helper.sh"


def test_codex_config_endpoint_filter(codex_config):
    assert codex_config.endpoint_filter == r"gpt|openai"
    assert codex_config.base_url_suffix == "/serving-endpoints/openai/v1"


def test_codex_config_no_model_tiers(codex_config):
    """Codex has no opus/sonnet/haiku model tiers."""
    assert codex_config.default_opus == ""
    assert codex_config.default_sonnet == ""
    assert codex_config.default_haiku == ""


def test_codex_config_no_env_keys(codex_config):
    """Codex uses TOML config, not env vars."""
    assert codex_config.env_model == ""
    assert codex_config.env_base_url == ""
    assert codex_config.required_env_keys == ()
    assert codex_config.uninstall_env_keys == ()


def test_codex_skill_names_has_six_entries():
    assert len(SKILL_NAMES) == 6
    assert all(name.startswith("fmapi-codingagent-") for name in SKILL_NAMES)


# --- read_env tests ---


def test_read_env_extracts_model(codex_adapter, sample_codex_toml_data):
    result = codex_adapter.read_env(sample_codex_toml_data)
    assert result["model"] == "databricks-gpt-5-2"


def test_read_env_extracts_ttl(codex_adapter, sample_codex_toml_data):
    result = codex_adapter.read_env(sample_codex_toml_data)
    assert result["ttl"] == "55", f"Expected '55' (3300000ms / 60000), got '{result.get('ttl')}'"


def test_read_env_extracts_reasoning_effort(codex_adapter, sample_codex_toml_data):
    result = codex_adapter.read_env(sample_codex_toml_data)
    assert result["model_reasoning_effort"] == "high"


def test_read_env_empty_settings(codex_adapter):
    result = codex_adapter.read_env({})
    assert result == {}


def test_read_env_no_profiles(codex_adapter):
    result = codex_adapter.read_env({"model_providers": {"databricks_fmapi": {}}})
    assert result == {}


def test_read_env_no_auth_block(codex_adapter):
    data = {
        "profile": "databricks_fmapi",
        "profiles": {
            "databricks_fmapi": {"model": "my-model", "model_provider": "databricks_fmapi"}
        },
    }
    result = codex_adapter.read_env(data)
    assert result["model"] == "my-model"
    assert "ttl" not in result


def test_read_env_no_model_tiers(codex_adapter, sample_codex_toml_data):
    """Codex read_env never returns opus/sonnet/haiku."""
    result = codex_adapter.read_env(sample_codex_toml_data)
    assert "opus" not in result
    assert "sonnet" not in result
    assert "haiku" not in result


def test_read_env_legacy_default_profile(codex_adapter):
    """read_env should fall back to legacy 'default' profile."""
    data = {
        "profiles": {"default": {"model": "legacy-model", "model_provider": "databricks"}},
        "model_providers": {
                "databricks": {
                "auth": {"command": "/path/helper.sh", "refresh_interval_ms": 1800000}
            }
        },
    }
    result = codex_adapter.read_env(data)
    assert result["model"] == "legacy-model"
    assert result["ttl"] == "30"


# --- write_env_json tests ---


def test_write_env_json_flat_dict(codex_adapter):
    env = codex_adapter.write_env_json(
        model="my-model",
        base_url="https://example.com/serving-endpoints/openai/v1",
        opus="",
        sonnet="",
        haiku="",
        ttl_ms="3300000",
    )
    assert env["model"] == "my-model"
    assert env["base_url"] == "https://example.com/serving-endpoints/openai/v1"
    assert env["refresh_interval_ms"] == "3300000"
    assert len(env) == 3


# --- settings_candidates tests ---


def test_settings_candidates_returns_paths(codex_adapter):
    candidates = codex_adapter.settings_candidates()
    assert len(candidates) == 2
    assert all(str(c).endswith("config.toml") for c in candidates)
    assert ".codex" in str(candidates[0])


# --- TOML config discovery tests ---


def test_discover_config_finds_toml(tmp_path):
    """discover_config should find FMAPI config via auth.command."""
    adapter = CodexAdapter()

    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"

    toml_data = {
        "profile": "codinggateway-codex-profile",
        "profiles": {
            "codinggateway-codex-profile": {
                "model_provider": "Databricks",
                "model": "databricks-gpt-5-2",
            }
        },
        "model_providers": {
            "Databricks": {
                "name": "Databricks AI Gateway",
                "base_url": "https://example.com/serving-endpoints/openai/v1",
                "wire_api": "responses",
                "auth": {
                    "command": str(tmp_path / ".codex" / "fmapi-key-helper.sh"),
                    "refresh_interval_ms": 3300000,
                    "timeout_ms": 10000,
                },
            }
        },
    }
    config_file.write_bytes(tomli_w.dumps(toml_data).encode())

    helper_path = tmp_path / ".codex" / "fmapi-key-helper.sh"
    helper_path.write_text(
        '#!/bin/sh\nFMAPI_HOST="https://example.com"\nFMAPI_PROFILE="test-profile"\n'
    )

    with patch.object(adapter, "settings_candidates", return_value=[config_file]):
        cfg = discover_config(adapter)

    assert cfg.found is True
    assert cfg.model == "databricks-gpt-5-2"
    assert cfg.ttl == "55"
    assert cfg.host == "https://example.com"
    assert cfg.profile == "test-profile"
    assert cfg.settings_file == str(config_file)
    assert cfg.provider_id == "Databricks"
    assert cfg.provider_name == "Databricks AI Gateway"


def test_discover_config_custom_provider_id(tmp_path):
    """discover_config should populate provider_id from the matched TOML key."""
    adapter = CodexAdapter()

    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"

    toml_data = {
        "profile": "my_custom_provider",
        "profiles": {
            "my_custom_provider": {
                "model_provider": "my_custom_provider",
                "model": "test-model",
            }
        },
        "model_providers": {
            "my_custom_provider": {
                "name": "Databricks FMAPI",
                "base_url": "https://example.com/serving-endpoints/openai/v1",
                "wire_api": "responses",
                "auth": {
                    "command": str(tmp_path / ".codex" / "fmapi-key-helper.sh"),
                    "refresh_interval_ms": 3300000,
                    "timeout_ms": 10000,
                },
            }
        },
    }
    config_file.write_bytes(tomli_w.dumps(toml_data).encode())

    helper_path = tmp_path / ".codex" / "fmapi-key-helper.sh"
    helper_path.write_text(
        '#!/bin/sh\nFMAPI_HOST="https://example.com"\nFMAPI_PROFILE="test-profile"\n'
    )

    with patch.object(adapter, "settings_candidates", return_value=[config_file]):
        cfg = discover_config(adapter)

    assert cfg.found is True
    assert cfg.provider_id == "my_custom_provider"
    assert cfg.model == "test-model"


def test_discover_config_toml_no_fmapi(tmp_path):
    """discover_config should not find FMAPI in a TOML without fmapi-key-helper."""
    adapter = CodexAdapter()

    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"

    toml_data = {
        "profiles": {"codinggateway-codex-profile": {"model_provider": "openai", "model": "gpt-4"}},
        "model_providers": {"openai": {"name": "OpenAI", "base_url": "https://api.openai.com"}},
    }
    config_file.write_bytes(tomli_w.dumps(toml_data).encode())

    with patch.object(adapter, "settings_candidates", return_value=[config_file]):
        cfg = discover_config(adapter)

    assert cfg.found is False


def test_discover_config_toml_gateway(tmp_path):
    """discover_config should detect AI Gateway from TOML base_url."""
    adapter = CodexAdapter()

    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"

    toml_data = {
        "profile": "databricks_fmapi",
        "profiles": {
            "databricks_fmapi": {
                "model_provider": "databricks_fmapi",
                "model": "test-model",
            }
        },
        "model_providers": {
            "databricks_fmapi": {
                "base_url": "https://99999.ai-gateway.cloud.databricks.com/openai/v1",
                "wire_api": "responses",
                "auth": {
                    "command": str(tmp_path / ".codex" / "fmapi-key-helper.sh"),
                    "refresh_interval_ms": 3300000,
                },
            }
        },
    }
    config_file.write_bytes(tomli_w.dumps(toml_data).encode())

    helper_path = tmp_path / ".codex" / "fmapi-key-helper.sh"
    helper_path.write_text('#!/bin/sh\nFMAPI_HOST="https://example.com"\n')

    with patch.object(adapter, "settings_candidates", return_value=[config_file]):
        cfg = discover_config(adapter)

    assert cfg.found is True
    assert cfg.ai_gateway == "true"
    assert cfg.workspace_id == "99999"
