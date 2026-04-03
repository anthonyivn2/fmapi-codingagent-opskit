"""Tests for TomlSettingsManager — TOML read/write/merge for Codex."""

from __future__ import annotations

import pytest

from fmapi_opskit.settings.toml_manager import TomlSettingsManager


@pytest.fixture
def toml_path(tmp_path):
    """Return a config.toml path inside a temp directory."""
    return tmp_path / ".codex" / "config.toml"


@pytest.fixture
def mgr(toml_path):
    """Return a fresh TomlSettingsManager."""
    return TomlSettingsManager(toml_path)


@pytest.fixture
def sample_toml_content() -> str:
    """Valid TOML content matching the Codex FMAPI schema."""
    return (
        "[profiles.default]\n"
        'model_provider = "databricks"\n'
        'model = "databricks-gpt-5-2"\n\n'
        "[model_providers.databricks]\n"
        'name = "Databricks FMAPI"\n'
        'base_url = "https://example.com/serving-endpoints/openai/v1"\n'
        'wire_api = "responses"\n\n'
        "[model_providers.databricks.auth]\n"
        'command = "/home/user/.codex/fmapi-key-helper.sh"\n'
        "refresh_interval_ms = 3300000\n"
        "timeout_ms = 10000\n"
    )


# --- read/write tests ---


def test_read_missing_returns_empty(mgr):
    assert mgr.read() == {}


def test_read_corrupt_toml_returns_empty(toml_path, mgr):
    toml_path.parent.mkdir(parents=True, exist_ok=True)
    toml_path.write_text("[[invalid toml ===")
    assert mgr.read() == {}


def test_write_read_roundtrip(mgr):
    data = {"profiles": {"default": {"model": "test-model"}}}
    mgr.write(data)
    result = mgr.read()
    assert result["profiles"]["default"]["model"] == "test-model"


def test_write_creates_parent_dirs(toml_path, mgr):
    assert not toml_path.parent.exists()
    mgr.write({"key": "value"})
    assert toml_path.is_file()


def test_write_sets_600_permissions(mgr):
    mgr.write({"key": "value"})
    mode = mgr.path.stat().st_mode & 0o777
    assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"


def test_exists(mgr):
    assert not mgr.exists()
    mgr.write({"key": "value"})
    assert mgr.exists()


# --- merge_provider tests ---


def test_merge_provider_creates_config(mgr):
    mgr.merge_provider(
        provider_id="databricks",
        provider_name="Databricks FMAPI",
        base_url="https://example.com/serving-endpoints/openai/v1",
        wire_api="responses",
        auth_command="/path/to/helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="default",
        model="databricks-gpt-5-2",
    )

    data = mgr.read()
    assert data["profiles"]["default"]["model_provider"] == "databricks"
    assert data["profiles"]["default"]["model"] == "databricks-gpt-5-2"
    assert data["model_providers"]["databricks"]["name"] == "Databricks FMAPI"
    assert data["model_providers"]["databricks"]["wire_api"] == "responses"
    assert data["model_providers"]["databricks"]["auth"]["command"] == "/path/to/helper.sh"
    assert data["model_providers"]["databricks"]["auth"]["refresh_interval_ms"] == 3300000
    assert data["model_providers"]["databricks"]["auth"]["timeout_ms"] == 10000


def test_merge_provider_preserves_existing_sections(mgr):
    """Merging a provider should not destroy other sections."""
    mgr.write({"some_other_section": {"key": "value"}})
    mgr.merge_provider(
        provider_id="databricks",
        provider_name="Databricks FMAPI",
        base_url="https://example.com/serving-endpoints/openai/v1",
        wire_api="responses",
        auth_command="/path/to/helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="default",
        model="test-model",
    )

    data = mgr.read()
    assert data["some_other_section"]["key"] == "value"
    assert data["model_providers"]["databricks"]["name"] == "Databricks FMAPI"


def test_merge_provider_updates_existing(mgr):
    """Re-merging should update existing provider settings."""
    mgr.merge_provider(
        provider_id="databricks",
        provider_name="Old Name",
        base_url="https://old.com",
        wire_api="chat",
        auth_command="/old/path",
        refresh_interval_ms=100,
        timeout_ms=5000,
        profile="default",
        model="old-model",
    )
    mgr.merge_provider(
        provider_id="databricks",
        provider_name="Databricks FMAPI",
        base_url="https://new.com",
        wire_api="responses",
        auth_command="/new/path",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="default",
        model="new-model",
    )

    data = mgr.read()
    assert data["model_providers"]["databricks"]["base_url"] == "https://new.com"
    assert data["model_providers"]["databricks"]["auth"]["command"] == "/new/path"
    assert data["profiles"]["default"]["model"] == "new-model"


# --- remove_fmapi_provider tests ---


def test_remove_provider_deletes_file_when_only_fmapi(mgr):
    """If FMAPI is the only config, the file should be deleted."""
    mgr.merge_provider(
        provider_id="databricks",
        provider_name="Databricks FMAPI",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="default",
        model="test-model",
    )
    assert mgr.exists()

    deleted = mgr.remove_fmapi_provider()
    assert deleted is True
    assert not mgr.exists()


def test_remove_provider_keeps_file_when_others_remain(mgr):
    """If other config sections exist, file should be preserved."""
    mgr.merge_provider(
        provider_id="databricks",
        provider_name="Databricks FMAPI",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="default",
        model="test-model",
    )
    # Add another provider
    data = mgr.read()
    data["model_providers"]["openai"] = {"name": "OpenAI", "base_url": "https://api.openai.com"}
    data["profiles"]["other"] = {"model_provider": "openai", "model": "gpt-4"}
    mgr.write(data)

    deleted = mgr.remove_fmapi_provider()
    assert deleted is False
    assert mgr.exists()

    data = mgr.read()
    assert "databricks" not in data.get("model_providers", {})
    assert "default" not in data.get("profiles", {})
    assert data["model_providers"]["openai"]["name"] == "OpenAI"
    assert data["profiles"]["other"]["model"] == "gpt-4"


def test_remove_provider_missing_returns_false(mgr):
    """Removing from empty config should return False."""
    deleted = mgr.remove_fmapi_provider()
    assert deleted is False


# --- get_provider_auth_command tests ---


def test_get_provider_auth_command(mgr):
    mgr.merge_provider(
        provider_id="databricks",
        provider_name="Test",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="default",
        model="test-model",
    )
    assert mgr.get_provider_auth_command() == "/path/to/fmapi-key-helper.sh"


def test_get_provider_auth_command_missing(mgr):
    assert mgr.get_provider_auth_command() == ""
