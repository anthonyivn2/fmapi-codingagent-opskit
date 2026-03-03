"""Tests for AgentConfig dataclass and ClaudeCodeAdapter methods."""

from __future__ import annotations


def test_config_name(adapter):
    assert adapter.config.name == "Claude Code", (
        f"Expected name='Claude Code', got '{adapter.config.name}'"
    )


def test_config_default_model(adapter):
    expected = "databricks-claude-opus-4-6"
    assert adapter.config.default_model == expected, (
        f"Expected default_model='{expected}', got '{adapter.config.default_model}'"
    )


def test_config_cli_cmd(adapter):
    assert adapter.config.cli_cmd == "claude", (
        f"Expected cli_cmd='claude', got '{adapter.config.cli_cmd}'"
    )


def test_config_env_variable_names(adapter):
    c = adapter.config
    assert c.env_model == "ANTHROPIC_MODEL", f"env_model mismatch: {c.env_model}"
    assert c.env_base_url == "ANTHROPIC_BASE_URL", f"env_base_url mismatch: {c.env_base_url}"
    assert c.env_opus == "ANTHROPIC_DEFAULT_OPUS_MODEL", f"env_opus mismatch: {c.env_opus}"
    assert c.env_sonnet == "ANTHROPIC_DEFAULT_SONNET_MODEL", f"env_sonnet mismatch: {c.env_sonnet}"
    assert c.env_haiku == "ANTHROPIC_DEFAULT_HAIKU_MODEL", f"env_haiku mismatch: {c.env_haiku}"
    assert c.env_ttl == "CLAUDE_CODE_API_KEY_HELPER_TTL_MS", f"env_ttl mismatch: {c.env_ttl}"


def test_adapter_satisfies_protocol(adapter):
    required_attrs = [
        "config",
        "settings_candidates",
        "read_env",
        "write_env_json",
        "ensure_onboarding",
        "register_plugin",
        "deregister_plugin",
        "install_cli",
        "doctor_extra",
        "dry_run_env_display",
        "dry_run_extra",
    ]
    for attr in required_attrs:
        assert hasattr(adapter, attr), f"AgentAdapter protocol requires '{attr}' but it is missing"


def test_read_env_extracts_models(adapter, sample_settings):
    result = adapter.read_env(sample_settings)
    assert result["model"] == "databricks-claude-opus-4-6", f"model mismatch: {result.get('model')}"
    assert result["opus"] == "databricks-claude-opus-4-6", f"opus mismatch: {result.get('opus')}"
    assert result["sonnet"] == "databricks-claude-sonnet-4-6", (
        f"sonnet mismatch: {result.get('sonnet')}"
    )
    assert result["haiku"] == "databricks-claude-haiku-4-5", (
        f"haiku mismatch: {result.get('haiku')}"
    )


def test_read_env_converts_ttl(adapter, sample_settings):
    result = adapter.read_env(sample_settings)
    assert result["ttl"] == "60", (
        f"Expected ttl='60' (3600000ms / 60000), got '{result.get('ttl')}'"
    )


def test_read_env_empty_settings(adapter):
    result = adapter.read_env({})
    assert result == {}, f"Empty settings should produce empty result, got {result}"


def test_read_env_skips_non_numeric_ttl(adapter):
    settings = {"env": {"CLAUDE_CODE_API_KEY_HELPER_TTL_MS": "not-a-number"}}
    result = adapter.read_env(settings)
    assert "ttl" not in result, f"Non-numeric TTL should be skipped, got result={result}"


def test_write_env_json_all_keys(adapter):
    env = adapter.write_env_json(
        model="m1",
        base_url="https://example.com",
        opus="o1",
        sonnet="s1",
        haiku="h1",
        ttl_ms="3600000",
    )
    assert len(env) == 8, f"Expected 8 env keys, got {len(env)}: {list(env.keys())}"
    assert env["ANTHROPIC_MODEL"] == "m1", f"ANTHROPIC_MODEL mismatch: {env['ANTHROPIC_MODEL']}"
    assert env["ANTHROPIC_BASE_URL"] == "https://example.com", (
        f"ANTHROPIC_BASE_URL mismatch: {env['ANTHROPIC_BASE_URL']}"
    )
    assert env["ANTHROPIC_DEFAULT_OPUS_MODEL"] == "o1", (
        f"ANTHROPIC_DEFAULT_OPUS_MODEL mismatch: {env['ANTHROPIC_DEFAULT_OPUS_MODEL']}"
    )
    assert env["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "s1", (
        f"ANTHROPIC_DEFAULT_SONNET_MODEL mismatch: {env['ANTHROPIC_DEFAULT_SONNET_MODEL']}"
    )
    assert env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] == "h1", (
        f"ANTHROPIC_DEFAULT_HAIKU_MODEL mismatch: {env['ANTHROPIC_DEFAULT_HAIKU_MODEL']}"
    )
    assert env["CLAUDE_CODE_API_KEY_HELPER_TTL_MS"] == "3600000", (
        f"TTL mismatch: {env['CLAUDE_CODE_API_KEY_HELPER_TTL_MS']}"
    )
    assert env["ANTHROPIC_CUSTOM_HEADERS"] == "x-databricks-use-coding-agent-mode: true", (
        f"Custom headers mismatch: {env['ANTHROPIC_CUSTOM_HEADERS']}"
    )
    assert env["CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS"] == "1", (
        f"Experimental betas flag mismatch: {env['CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS']}"
    )
