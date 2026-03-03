"""Tests for config file loading and validation."""

from __future__ import annotations

import json

import pytest

from fmapi_opskit.config.loader import ConfigError, load_config_file


def test_load_valid_config(config_file):
    cfg = load_config_file(str(config_file))
    assert cfg.host == "https://example.cloud.databricks.com"
    assert cfg.profile == "test-profile"
    assert cfg.model == "databricks-claude-opus-4-6"
    assert cfg.ttl == "60"


def test_load_config_file_not_found(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config_file(str(tmp_path / "nonexistent.json"))


def test_load_config_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config_file(str(p))


def test_load_config_unknown_key(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"host": "https://example.com", "unknown_key": "val"}))
    with pytest.raises(ConfigError, match="unknown_key"):
        load_config_file(str(p))


def test_load_config_ai_gateway_true(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"host": "https://x.com", "ai_gateway": True}))
    cfg = load_config_file(str(p))
    assert cfg.ai_gateway == "true"


def test_load_config_ai_gateway_false(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"host": "https://x.com", "ai_gateway": False}))
    cfg = load_config_file(str(p))
    assert cfg.ai_gateway == "false"


def test_load_config_workspace_id_numeric(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"host": "https://x.com", "workspace_id": "12345"}))
    cfg = load_config_file(str(p))
    assert cfg.workspace_id == "12345"


def test_load_config_workspace_id_non_numeric(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"host": "https://x.com", "workspace_id": "abc"}))
    with pytest.raises(ConfigError, match="numeric"):
        load_config_file(str(p))


def test_load_config_version_field_accepted(tmp_path):
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps({"version": 1, "host": "https://x.com"}))
    cfg = load_config_file(str(p))
    assert cfg.host == "https://x.com"


def test_load_config_all_valid_keys(tmp_path):
    """All recognized config keys are accepted without error."""
    data = {
        "version": 1,
        "host": "https://x.com",
        "profile": "p",
        "model": "m",
        "opus": "o",
        "sonnet": "s",
        "haiku": "h",
        "ttl": "30",
        "settings_location": "home",
        "ai_gateway": False,
        "workspace_id": "123",
    }
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(data))
    cfg = load_config_file(str(p))
    assert cfg.host == "https://x.com"
    assert cfg.profile == "p"


def test_load_config_empty_object(tmp_path):
    """An empty JSON object is valid (all fields optional)."""
    p = tmp_path / "cfg.json"
    p.write_text("{}")
    cfg = load_config_file(str(p))
    assert cfg.host == ""
    assert cfg.model == ""
