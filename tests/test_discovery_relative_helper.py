from fmapi_opskit.agents.claudecode import ClaudeCodeAdapter
from fmapi_opskit.config.discovery import discover_config


def test_discovery_resolves_relative_json_helper_path(tmp_path):
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()

    helper_path = settings_dir / "fmapi-key-helper.sh"
    helper_path.write_text(
        'FMAPI_PROFILE="fmapi-claudecode-profile"\n'
        'FMAPI_HOST="https://workspace.cloud.databricks.com"\n'
        'echo "token"\n'
    )
    helper_path.chmod(0o700)

    settings_file = settings_dir / "settings.json"
    settings_file.write_text(
        '{"apiKeyHelper":"./fmapi-key-helper.sh","env":{"ANTHROPIC_BASE_URL":"https://workspace.cloud.databricks.com/serving-endpoints/anthropic","ANTHROPIC_MODEL":"databricks-claude-opus-4-6"}}'
    )

    adapter = ClaudeCodeAdapter()
    adapter.settings_candidates = lambda: [settings_file]  # type: ignore[assignment]

    cfg = discover_config(adapter)

    assert cfg.found is True
    assert cfg.host == "https://workspace.cloud.databricks.com"
    assert cfg.profile == "fmapi-claudecode-profile"
    assert cfg.helper_file == str(helper_path.resolve())
