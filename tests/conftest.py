"""Shared pytest fixtures."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def config_file(tmp_path):
    """Write a sample config JSON file and return its path."""
    data = {
        "version": 1,
        "host": "https://example.cloud.databricks.com",
        "profile": "test-profile",
        "model": "databricks-claude-opus-4-6",
        "ttl": "60",
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data))
    return p
