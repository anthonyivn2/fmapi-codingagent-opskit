"""Tests for config file loading and validation."""

from __future__ import annotations

import json

import pytest

from fmapi_opskit.config.loader import ConfigError, load_config_file


def test_config_loading(config_file, tmp_path):
    # valid config
    cfg = load_config_file(str(config_file))
    assert cfg.host == "https://example.cloud.databricks.com"

    # rejects: not found, bad JSON, unknown key, http host
    with pytest.raises(ConfigError):
        load_config_file(str(tmp_path / "nope.json"))

    bad = tmp_path / "bad.json"
    bad.write_text("{nope")
    with pytest.raises(ConfigError):
        load_config_file(str(bad))

    unk = tmp_path / "unk.json"
    unk.write_text(json.dumps({"host": "https://x.com", "bad_key": "v"}))
    with pytest.raises(ConfigError):
        load_config_file(str(unk))

    http = tmp_path / "http.json"
    http.write_text(json.dumps({"host": "http://x.com"}))
    with pytest.raises(ConfigError):
        load_config_file(str(http))
