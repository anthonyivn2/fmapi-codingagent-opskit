"""Tests for AgentAdapter protocol compliance and ClaudeCodeAdapter."""

from __future__ import annotations

from fmapi_opskit.agents.base import AgentConfig
from fmapi_opskit.agents.claudecode import CLAUDE_CODE_CONFIG


class TestAgentConfig:
    def test_config_is_frozen(self):
        """AgentConfig should be immutable."""
        import pytest

        config = CLAUDE_CODE_CONFIG
        with pytest.raises(AttributeError):
            config.name = "modified"  # type: ignore[misc]

    def test_default_model_values(self):
        c = CLAUDE_CODE_CONFIG
        assert c.default_model == "databricks-claude-opus-4-6"
        assert c.default_opus == "databricks-claude-opus-4-6"
        assert c.default_sonnet == "databricks-claude-sonnet-4-6"
        assert c.default_haiku == "databricks-claude-haiku-4-5"

    def test_env_var_names(self):
        c = CLAUDE_CODE_CONFIG
        assert c.env_model == "ANTHROPIC_MODEL"
        assert c.env_base_url == "ANTHROPIC_BASE_URL"
        assert c.env_opus == "ANTHROPIC_DEFAULT_OPUS_MODEL"
        assert c.env_sonnet == "ANTHROPIC_DEFAULT_SONNET_MODEL"
        assert c.env_haiku == "ANTHROPIC_DEFAULT_HAIKU_MODEL"
        assert c.env_ttl == "CLAUDE_CODE_API_KEY_HELPER_TTL_MS"

    def test_required_env_keys(self):
        c = CLAUDE_CODE_CONFIG
        assert len(c.required_env_keys) >= 5
        assert "ANTHROPIC_MODEL" in c.required_env_keys
        assert "ANTHROPIC_BASE_URL" in c.required_env_keys

    def test_settings_dir_and_filename(self):
        c = CLAUDE_CODE_CONFIG
        assert c.settings_dir == ".claude"
        assert c.settings_filename == "settings.json"
        assert c.helper_filename == "fmapi-key-helper.sh"
        assert c.hook_precheck_filename == "fmapi-auth-precheck.sh"

    def test_agent_id_and_name(self):
        c = CLAUDE_CODE_CONFIG
        assert c.id == "claudecode"
        assert c.name == "Claude Code"

    def test_uninstall_env_keys(self):
        c = CLAUDE_CODE_CONFIG
        keys = c.uninstall_env_keys
        assert "ANTHROPIC_MODEL" in keys
        assert "ANTHROPIC_AUTH_TOKEN" in keys  # legacy cleanup
        assert "ANTHROPIC_BASE_URL" in keys
        assert "CLAUDE_CODE_API_KEY_HELPER_TTL_MS" in keys


class TestClaudeCodeAdapter:
    def test_has_config(self, adapter):
        assert isinstance(adapter.config, AgentConfig)

    def test_write_env_json(self, adapter):
        env = adapter.write_env_json(
            model="m",
            base_url="https://x.com/serving-endpoints/anthropic",
            opus="o",
            sonnet="s",
            haiku="h",
            ttl_ms="3600000",
        )
        assert env["ANTHROPIC_MODEL"] == "m"
        assert env["ANTHROPIC_BASE_URL"] == "https://x.com/serving-endpoints/anthropic"
        assert env["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "o"
        assert env["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "s"
        assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "h"
        assert env["CLAUDE_CODE_API_KEY_HELPER_TTL_MS"] == "3600000"

    def test_read_env_from_settings(self, adapter, sample_settings):
        result = adapter.read_env(sample_settings)
        assert result["model"] == "databricks-claude-opus-4-6"
        assert result["opus"] == "databricks-claude-opus-4-6"
        assert result["sonnet"] == "databricks-claude-sonnet-4-6"
        assert result["haiku"] == "databricks-claude-haiku-4-5"
        assert result["ttl"] == "60"

    def test_read_env_empty_settings(self, adapter):
        result = adapter.read_env({})
        assert result == {}

    def test_settings_candidates(self, adapter):
        candidates = adapter.settings_candidates()
        assert len(candidates) > 0
        for c in candidates:
            assert str(c).endswith("settings.json")
