"""Write settings, helper script, and hook scripts."""

from __future__ import annotations

from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.network.gateway import build_base_url
from fmapi_opskit.settings.hooks import merge_fmapi_hooks
from fmapi_opskit.settings.manager import SettingsManager
from fmapi_opskit.templates.renderer import render_template
from fmapi_opskit.ui import logging as log

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def write_settings(
    adapter: AgentAdapter,
    *,
    settings_file: str,
    helper_file: str,
    host: str,
    model: str,
    opus: str,
    sonnet: str,
    haiku: str,
    ttl_ms: str,
    ai_gateway_enabled: bool,
    workspace_id: str,
) -> None:
    """Write/merge the settings.json file."""
    log.heading("Writing settings")

    base_url = build_base_url(host, ai_gateway_enabled, workspace_id)
    env_json = adapter.write_env_json(model, base_url, opus, sonnet, haiku, ttl_ms)

    mgr = SettingsManager(Path(settings_file))
    mgr.merge_env(
        env_json,
        api_key_helper=helper_file,
        legacy_cleanup_keys=adapter.config.legacy_cleanup_keys,
    )

    log.debug(f"write_settings: wrote {settings_file} (TTL={ttl_ms}ms)")
    log.success(f"Settings written to {settings_file}.")


def write_helper(
    adapter: AgentAdapter,
    *,
    script_dir: Path,
    helper_file: str,
    host: str,
    profile: str,
) -> None:
    """Write the API key helper script from template."""
    log.heading("API key helper")

    template = _TEMPLATES_DIR / "fmapi-key-helper.sh.template"
    setup_script = f"setup-fmapi-{adapter.config.id}"

    render_template(
        template,
        Path(helper_file),
        {
            "PROFILE": profile,
            "HOST": host,
            "SETUP_SCRIPT": setup_script,
        },
        mode=0o700,
    )

    log.debug(f"write_helper: wrote {helper_file} (profile={profile}, host={host})")
    log.success(f"Helper script written to {helper_file}.")


def write_hooks(
    adapter: AgentAdapter,
    *,
    script_dir: Path,
    settings_file: str,
    hook_file: str,
    host: str,
    profile: str,
) -> None:
    """Write the auth pre-check hook script and merge into settings."""
    log.heading("Auth pre-check hooks")

    template = _TEMPLATES_DIR / "fmapi-auth-precheck.sh.template"

    # Clean up legacy hook script
    legacy_hook = Path(hook_file).parent / "fmapi-subagent-precheck.sh"
    if legacy_hook.is_file() and str(legacy_hook) != hook_file:
        legacy_hook.unlink()
        log.debug(f"write_hooks: removed legacy hook script {legacy_hook}")

    # Render hook script
    render_template(
        template,
        Path(hook_file),
        {
            "PROFILE": profile,
            "HOST": host,
        },
        mode=0o700,
    )

    log.debug(f"write_hooks: wrote {hook_file} (profile={profile}, host={host})")
    log.success(f"Hook script written to {hook_file}.")

    # Merge hooks into settings.json
    mgr = SettingsManager(Path(settings_file))
    settings = mgr.read()
    merge_fmapi_hooks(settings, hook_file)
    mgr.write(settings)

    log.debug(f"write_hooks: merged hooks section into {settings_file}")
