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
        'profile = "databricks_fmapi"\n\n'
        "[profiles.databricks_fmapi]\n"
        'model_provider = "databricks_fmapi"\n'
        'model = "databricks-gpt-5-2"\n\n'
        "[model_providers.databricks_fmapi]\n"
        'name = "Databricks FMAPI"\n'
        'base_url = "https://example.com/serving-endpoints/openai/v1"\n'
        'wire_api = "responses"\n\n'
        "[model_providers.databricks_fmapi.auth]\n"
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
        provider_id="databricks_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://example.com/serving-endpoints/openai/v1",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="databricks_fmapi",
        model="databricks-gpt-5-2",
    )

    data = mgr.read()
    assert data["profile"] == "databricks_fmapi"
    assert data["profiles"]["databricks_fmapi"]["model_provider"] == "databricks_fmapi"
    assert data["profiles"]["databricks_fmapi"]["model"] == "databricks-gpt-5-2"
    assert data["model_providers"]["databricks_fmapi"]["name"] == "Databricks FMAPI"
    assert data["model_providers"]["databricks_fmapi"]["wire_api"] == "responses"
    assert data["model_providers"]["databricks_fmapi"]["auth"]["command"] == (
        "/path/to/fmapi-key-helper.sh"
    )
    assert data["model_providers"]["databricks_fmapi"]["auth"]["refresh_interval_ms"] == 3300000
    assert data["model_providers"]["databricks_fmapi"]["auth"]["timeout_ms"] == 10000


def test_merge_provider_preserves_existing_sections(mgr):
    """Merging a provider should not destroy other sections."""
    mgr.write({"some_other_section": {"key": "value"}})
    mgr.merge_provider(
        provider_id="databricks_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://example.com/serving-endpoints/openai/v1",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="databricks_fmapi",
        model="test-model",
    )

    data = mgr.read()
    assert data["some_other_section"]["key"] == "value"
    assert data["model_providers"]["databricks_fmapi"]["name"] == "Databricks FMAPI"


def test_merge_provider_updates_existing(mgr):
    """Re-merging should update existing provider settings."""
    mgr.merge_provider(
        provider_id="databricks_fmapi",
        provider_name="Old Name",
        base_url="https://old.com",
        wire_api="chat",
        auth_command="/old/fmapi-key-helper.sh",
        refresh_interval_ms=100,
        timeout_ms=5000,
        profile="databricks_fmapi",
        model="old-model",
    )
    mgr.merge_provider(
        provider_id="databricks_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://new.com",
        wire_api="responses",
        auth_command="/new/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="databricks_fmapi",
        model="new-model",
    )

    data = mgr.read()
    assert data["model_providers"]["databricks_fmapi"]["base_url"] == "https://new.com"
    assert data["model_providers"]["databricks_fmapi"]["auth"]["command"] == (
        "/new/fmapi-key-helper.sh"
    )
    assert data["profiles"]["databricks_fmapi"]["model"] == "new-model"


def test_merge_provider_cleans_up_old_fmapi_name(mgr):
    """Changing provider name should remove old FMAPI provider and profile."""
    # First install with name "old_fmapi"
    mgr.merge_provider(
        provider_id="old_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="old_fmapi",
        model="old-model",
    )
    data = mgr.read()
    assert "old_fmapi" in data["profiles"]
    assert "old_fmapi" in data["model_providers"]

    # Reinstall with new name "new_fmapi"
    mgr.merge_provider(
        provider_id="new_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="new_fmapi",
        model="new-model",
    )
    data = mgr.read()
    # Old name should be gone
    assert "old_fmapi" not in data.get("profiles", {})
    assert "old_fmapi" not in data.get("model_providers", {})
    # New name should be present
    assert data["profile"] == "new_fmapi"
    assert data["profiles"]["new_fmapi"]["model"] == "new-model"
    assert "new_fmapi" in data["model_providers"]


def test_merge_provider_removes_legacy_env_key(mgr):
    """Merging should remove any legacy env_key from the provider."""
    mgr.write({
        "model_providers": {
            "databricks_fmapi": {
                "name": "Old",
                "base_url": "https://old.com",
                "wire_api": "responses",
                "env_key": "DATABRICKS_TOKEN",
            }
        }
    })

    mgr.merge_provider(
        provider_id="databricks_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://new.com",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="databricks_fmapi",
        model="test-model",
    )

    data = mgr.read()
    assert "env_key" not in data["model_providers"]["databricks_fmapi"]
    assert data["model_providers"]["databricks_fmapi"]["auth"]["command"] == (
        "/path/to/fmapi-key-helper.sh"
    )


# --- remove_fmapi_provider tests ---


def test_remove_provider_deletes_file_when_only_fmapi(mgr):
    """If FMAPI is the only config, the file should be deleted."""
    mgr.merge_provider(
        provider_id="databricks_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="databricks_fmapi",
        model="test-model",
    )
    assert mgr.exists()

    deleted = mgr.remove_fmapi_provider()
    assert deleted is True
    assert not mgr.exists()


def test_remove_provider_keeps_file_when_others_remain(mgr):
    """If other config sections exist, file should be preserved."""
    mgr.merge_provider(
        provider_id="databricks_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="databricks_fmapi",
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
    assert "databricks_fmapi" not in data.get("model_providers", {})
    assert "databricks_fmapi" not in data.get("profiles", {})
    assert data["model_providers"]["openai"]["name"] == "OpenAI"
    assert data["profiles"]["other"]["model"] == "gpt-4"


def test_remove_provider_missing_returns_false(mgr):
    """Removing from empty config should return False."""
    deleted = mgr.remove_fmapi_provider()
    assert deleted is False


# --- get_provider_auth_command tests ---


def test_get_provider_auth_command(mgr):
    mgr.merge_provider(
        provider_id="databricks_fmapi",
        provider_name="Test",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="databricks_fmapi",
        model="test-model",
    )
    assert mgr.get_provider_auth_command() == "/path/to/fmapi-key-helper.sh"


def test_get_provider_auth_command_missing(mgr):
    assert mgr.get_provider_auth_command() == ""


# --- custom provider_id tests ---


def test_merge_provider_custom_id(mgr):
    """Custom provider_id should work for both profile and provider sections."""
    mgr.merge_provider(
        provider_id="my_custom_provider",
        provider_name="Databricks FMAPI",
        base_url="https://example.com/serving-endpoints/openai/v1",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="my_custom_provider",
        model="test-model",
    )

    data = mgr.read()
    assert data["profile"] == "my_custom_provider"
    assert "my_custom_provider" in data["profiles"]
    assert data["profiles"]["my_custom_provider"]["model_provider"] == "my_custom_provider"
    assert "my_custom_provider" in data["model_providers"]
    assert data["model_providers"]["my_custom_provider"]["auth"]["command"] == (
        "/path/to/fmapi-key-helper.sh"
    )


def test_remove_provider_name_agnostic(mgr):
    """remove_fmapi_provider should find and remove providers by auth.command content."""
    mgr.merge_provider(
        provider_id="custom_name",
        provider_name="Databricks FMAPI",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/home/user/.codex/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="custom_name",
        model="test-model",
    )
    assert mgr.exists()

    deleted = mgr.remove_fmapi_provider()
    assert deleted is True
    assert not mgr.exists()


def test_remove_provider_preserves_non_fmapi_with_custom_id(mgr):
    """Removing custom-named FMAPI provider preserves other providers."""
    mgr.merge_provider(
        provider_id="my_fmapi",
        provider_name="Databricks FMAPI",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/path/to/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="my_fmapi",
        model="test-model",
    )
    data = mgr.read()
    data["model_providers"]["openai"] = {"name": "OpenAI", "base_url": "https://api.openai.com"}
    data["profiles"]["other"] = {"model_provider": "openai", "model": "gpt-4"}
    mgr.write(data)

    deleted = mgr.remove_fmapi_provider()
    assert deleted is False

    data = mgr.read()
    assert "my_fmapi" not in data.get("model_providers", {})
    assert "my_fmapi" not in data.get("profiles", {})
    assert "profile" not in data  # top-level profile pointed to removed profile
    assert data["model_providers"]["openai"]["name"] == "OpenAI"


def test_remove_provider_no_fmapi_returns_false(mgr):
    """remove_fmapi_provider returns False when no FMAPI providers exist."""
    mgr.write({
        "model_providers": {
            "openai": {"name": "OpenAI", "auth": {"command": "some-other-helper.sh"}}
        }
    })
    assert mgr.remove_fmapi_provider() is False


def test_get_auth_command_custom_provider_id(mgr):
    """get_provider_auth_command finds command regardless of provider name."""
    mgr.merge_provider(
        provider_id="custom_name",
        provider_name="Test",
        base_url="https://example.com",
        wire_api="responses",
        auth_command="/custom/path/fmapi-key-helper.sh",
        refresh_interval_ms=3300000,
        timeout_ms=10000,
        profile="custom_name",
        model="test-model",
    )
    assert mgr.get_provider_auth_command() == "/custom/path/fmapi-key-helper.sh"
