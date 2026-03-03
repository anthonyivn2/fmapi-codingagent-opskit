"""Shared pytest fixtures for the fmapi-opskit test suite."""

from __future__ import annotations

import json

import pytest

from fmapi_opskit.agents.claudecode import CLAUDE_CODE_CONFIG, ClaudeCodeAdapter


@pytest.fixture
def adapter() -> ClaudeCodeAdapter:
    """Return a fresh ClaudeCodeAdapter instance."""
    return ClaudeCodeAdapter()


@pytest.fixture
def agent_config():
    """Return the CLAUDE_CODE_CONFIG constant."""
    return CLAUDE_CODE_CONFIG


@pytest.fixture
def sample_config_data() -> dict:
    """Return a valid config dict suitable for load_config_file."""
    return {
        "version": 1,
        "host": "https://example.cloud.databricks.com",
        "profile": "test-profile",
        "model": "databricks-claude-opus-4-6",
        "ttl": "30",
    }


@pytest.fixture
def config_file(tmp_path, sample_config_data):
    """Write a sample config JSON file and return its path."""
    p = tmp_path / "config.json"
    p.write_text(json.dumps(sample_config_data))
    return p


@pytest.fixture
def sample_settings() -> dict:
    """Return a realistic settings.json dict with full env block."""
    return {
        "env": {
            "ANTHROPIC_MODEL": "databricks-claude-opus-4-6",
            "ANTHROPIC_BASE_URL": "https://example.com/serving-endpoints/anthropic",
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "databricks-claude-opus-4-6",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "databricks-claude-sonnet-4-6",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "databricks-claude-haiku-4-5",
            "ANTHROPIC_CUSTOM_HEADERS": "x-databricks-use-coding-agent-mode: true",
            "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
            "CLAUDE_CODE_API_KEY_HELPER_TTL_MS": "3600000",
        },
        "apiKeyHelper": "/home/user/.claude/fmapi-key-helper.sh",
    }


@pytest.fixture
def sample_endpoints() -> list[dict]:
    """Return a list of 4 mock endpoint dicts for network tests."""
    return [
        {"name": "databricks-claude-opus-4-6", "state": {"ready": "READY"}},
        {"name": "databricks-claude-sonnet-4-6", "state": {"ready": "READY"}},
        {"name": "databricks-llama-3-70b", "state": {"ready": "READY"}},
        {"name": "databricks-claude-haiku-4-5", "state": {"config_update": "IN_PROGRESS"}},
    ]
