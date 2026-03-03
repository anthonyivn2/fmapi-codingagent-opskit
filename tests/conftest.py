"""Shared pytest fixtures."""

from __future__ import annotations

import json

import pytest

from fmapi_opskit.agents.claudecode import ClaudeCodeAdapter


@pytest.fixture
def adapter():
    """Return a ClaudeCodeAdapter for testing."""
    return ClaudeCodeAdapter()


@pytest.fixture
def tmp_settings(tmp_path):
    """Create a temp directory with an empty settings file."""
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    settings_file = settings_dir / "settings.json"
    settings_file.write_text("{}")
    return settings_file


@pytest.fixture
def sample_settings():
    """Return a sample settings dict with FMAPI config."""
    return {
        "env": {
            "ANTHROPIC_MODEL": "databricks-claude-opus-4-6",
            "ANTHROPIC_BASE_URL": "https://example.com/serving-endpoints/anthropic",
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "databricks-claude-opus-4-6",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "databricks-claude-sonnet-4-6",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "databricks-claude-haiku-4-5",
            "CLAUDE_CODE_API_KEY_HELPER_TTL_MS": "3600000",
        },
        "apiKeyHelper": "/home/user/.claude/fmapi-key-helper.sh",
    }


@pytest.fixture
def sample_config():
    """Return a sample config JSON dict."""
    return {
        "version": 1,
        "host": "https://example.cloud.databricks.com",
        "profile": "test-profile",
        "model": "databricks-claude-opus-4-6",
        "opus": "databricks-claude-opus-4-6",
        "sonnet": "databricks-claude-sonnet-4-6",
        "haiku": "databricks-claude-haiku-4-5",
        "ttl": "60",
    }


@pytest.fixture
def config_file(tmp_path, sample_config):
    """Write a sample config JSON file and return its path."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps(sample_config))
    return p
