"""Tests for config file loading and validation."""

from __future__ import annotations

import json

import pytest

from fmapi_opskit.config.loader import ConfigError, load_config_file


def test_load_valid_returns_correct_fields(config_file):
    cfg = load_config_file(str(config_file))
    assert cfg.host == "https://example.cloud.databricks.com", f"Unexpected host: {cfg.host}"
    assert cfg.profile == "test-profile", f"Unexpected profile: {cfg.profile}"
    assert cfg.model == "databricks-claude-opus-4-6", f"Unexpected model: {cfg.model}"
    assert cfg.ttl == "30", f"Unexpected ttl: {cfg.ttl}"


def test_load_missing_path_raises(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(ConfigError, match="not found"):
        load_config_file(str(missing))


def test_load_bad_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config_file(str(bad))


def test_load_unknown_keys_raises(tmp_path):
    p = tmp_path / "unk.json"
    p.write_text(json.dumps({"host": "https://x.com", "bad_key": "v"}))
    with pytest.raises(ConfigError, match=r"Unknown keys.*bad_key"):
        load_config_file(str(p))


def test_load_http_host_raises(tmp_path):
    p = tmp_path / "http.json"
    p.write_text(json.dumps({"host": "http://x.com"}))
    with pytest.raises(ConfigError, match="https://"):
        load_config_file(str(p))


def test_load_invalid_profile_raises(tmp_path):
    p = tmp_path / "profile.json"
    p.write_text(json.dumps({"profile": "has spaces!"}))
    with pytest.raises(ConfigError, match="invalid profile"):
        load_config_file(str(p))


def test_load_ttl_zero_raises(tmp_path):
    p = tmp_path / "ttl0.json"
    p.write_text(json.dumps({"ttl": 0}))
    with pytest.raises(ConfigError, match="positive integer"):
        load_config_file(str(p))


def test_load_ttl_exceeds_max_raises(tmp_path):
    p = tmp_path / "ttl99.json"
    p.write_text(json.dumps({"ttl": 99}))
    with pytest.raises(ConfigError, match="cannot exceed 60"):
        load_config_file(str(p))


def test_load_ttl_valid_accepted(tmp_path):
    p = tmp_path / "ttl30.json"
    p.write_text(json.dumps({"ttl": 30}))
    cfg = load_config_file(str(p))
    assert cfg.ttl == "30", f"Expected ttl='30', got '{cfg.ttl}'"


def test_load_ai_gateway_bool_coerced(tmp_path):
    p = tmp_path / "gw.json"
    p.write_text(json.dumps({"ai_gateway": True}))
    cfg = load_config_file(str(p))
    assert cfg.ai_gateway == "true", f"Expected ai_gateway='true', got '{cfg.ai_gateway}'"


def test_load_ai_gateway_invalid_raises(tmp_path):
    p = tmp_path / "gw_bad.json"
    p.write_text(json.dumps({"ai_gateway": "maybe"}))
    with pytest.raises(ConfigError, match="true or false"):
        load_config_file(str(p))


def test_load_workspace_id_non_numeric_raises(tmp_path):
    p = tmp_path / "ws.json"
    p.write_text(json.dumps({"workspace_id": "abc"}))
    with pytest.raises(ConfigError, match="numeric"):
        load_config_file(str(p))


def test_load_unsupported_version_raises(tmp_path):
    p = tmp_path / "ver.json"
    p.write_text(json.dumps({"version": 99}))
    with pytest.raises(ConfigError, match="Unsupported"):
        load_config_file(str(p))


def test_load_version_omitted_accepted(tmp_path):
    p = tmp_path / "nover.json"
    p.write_text(json.dumps({"host": "https://example.com"}))
    cfg = load_config_file(str(p))
    assert cfg.host == "https://example.com", (
        f"Expected host parsed without version, got '{cfg.host}'"
    )
