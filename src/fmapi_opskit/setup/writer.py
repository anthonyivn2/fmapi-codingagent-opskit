"""Write settings, helper script, and clean up legacy hooks."""

from __future__ import annotations

from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth import clear_helper_token_cache
from fmapi_opskit.network import build_base_url
from fmapi_opskit.settings.hooks import remove_fmapi_hooks
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

    if clear_helper_token_cache(helper_file):
        log.debug("write_helper: cleared stale helper token cache")

    log.debug(f"write_helper: wrote {helper_file} (profile={profile}, host={host})")
    log.success(f"Helper script written to {helper_file}.")


def helper_needs_migration(helper_file: str) -> bool:
    """Return True when helper script matches known legacy patterns."""
    if not helper_file:
        return False

    helper_path = Path(helper_file)
    if not helper_path.is_file():
        return False

    try:
        helper_text = helper_path.read_text()
    except OSError:
        return False

    if "token=$(_fetch_token)" in helper_text:
        return True

    return "_fmapi_last_expires_in" in helper_text and "_fmapi_last_token" not in helper_text


def migrate_helper_if_needed(
    adapter: AgentAdapter,
    *,
    helper_file: str,
    host: str,
    profile: str,
    reason: str,
) -> bool:
    """Rewrite helper script when legacy patterns are detected.

    Returns True if migration was performed.
    """
    if not helper_needs_migration(helper_file):
        return False

    if not host or not profile:
        log.warn(
            "Detected legacy helper script but missing host/profile; "
            f"skipping migration during {reason}."
        )
        return False

    log.info(f"Legacy helper script detected during {reason}; refreshing it now.")
    write_helper(adapter, helper_file=helper_file, host=host, profile=profile)
    return True


def cleanup_legacy_hooks(
    *,
    settings_file: str,
) -> None:
    """Remove FMAPI hook entries from settings.json and delete hook script files.

    Called during setup to clean up hooks from prior installations.
    Hooks are no longer deployed — the apiKeyHelper handles all token management.
    """
    mgr = SettingsManager(Path(settings_file))
    settings = mgr.read()

    # Remove FMAPI hook entries from settings.json
    remove_fmapi_hooks(settings)
    mgr.write(settings)

    # Delete hook script files if they exist
    settings_dir = Path(settings_file).parent
    for hook_name in ("fmapi-auth-precheck.sh", "fmapi-subagent-precheck.sh"):
        hook_path = settings_dir / hook_name
        if hook_path.is_file():
            hook_path.unlink()
            log.debug(f"cleanup_legacy_hooks: removed {hook_path}")

    log.debug(f"cleanup_legacy_hooks: cleaned hooks from {settings_file}")
