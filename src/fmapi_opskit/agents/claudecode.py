"""Claude Code agent adapter — implements AgentAdapter Protocol."""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
from pathlib import Path

from fmapi_opskit.agents.base import AgentConfig
from fmapi_opskit.ui import logging as log

CLAUDE_CODE_CONFIG = AgentConfig(
    # Identity
    name="Claude Code",
    id="claudecode",
    cli_cmd="claude",
    setup_cmd="setup-fmapi-claudecode",
    cli_install_cmd="curl -fsSL https://claude.ai/install.sh | bash",
    # Settings paths
    settings_dir=".claude",
    settings_filename="settings.json",
    helper_filename="fmapi-key-helper.sh",
    hook_precheck_filename="fmapi-auth-precheck.sh",
    # Defaults
    default_profile="fmapi-claudecode-profile",
    default_model="databricks-claude-opus-4-6",
    default_opus="databricks-claude-opus-4-6",
    default_sonnet="databricks-claude-sonnet-4-6",
    default_haiku="databricks-claude-haiku-4-5",
    # Endpoint filtering
    endpoint_filter=r"claude|anthropic",
    endpoint_title="Anthropic Claude",
    base_url_suffix="/serving-endpoints/anthropic",
    # Environment variable names
    env_model="ANTHROPIC_MODEL",
    env_base_url="ANTHROPIC_BASE_URL",
    env_opus="ANTHROPIC_DEFAULT_OPUS_MODEL",
    env_sonnet="ANTHROPIC_DEFAULT_SONNET_MODEL",
    env_haiku="ANTHROPIC_DEFAULT_HAIKU_MODEL",
    env_ttl="CLAUDE_CODE_API_KEY_HELPER_TTL_MS",
    # Required env keys for doctor checks
    required_env_keys=(
        "ANTHROPIC_MODEL",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    ),
    # Legacy keys to remove from .env on write
    legacy_cleanup_keys=("ANTHROPIC_AUTH_TOKEN",),
    # All env keys to remove on uninstall
    uninstall_env_keys=(
        "ANTHROPIC_MODEL",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        "ANTHROPIC_CUSTOM_HEADERS",
        "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS",
        "CLAUDE_CODE_API_KEY_HELPER_TTL_MS",
    ),
)


class ClaudeCodeAdapter:
    """Claude Code agent adapter — all 25 variables + 11 methods."""

    def __init__(self) -> None:
        self._config = CLAUDE_CODE_CONFIG

    @property
    def config(self) -> AgentConfig:
        return self._config

    def settings_candidates(self) -> list[Path]:
        """Return settings file search paths."""
        c = self._config
        return [
            Path.home() / c.settings_dir / c.settings_filename,
            Path.cwd() / c.settings_dir / c.settings_filename,
        ]

    def read_env(self, settings: dict) -> dict[str, str]:
        """Read model/TTL from settings dict into a flat dict."""
        c = self._config
        env = settings.get("env", {})
        result: dict[str, str] = {}
        for attr, key in [
            ("model", c.env_model),
            ("opus", c.env_opus),
            ("sonnet", c.env_sonnet),
            ("haiku", c.env_haiku),
        ]:
            val = env.get(key, "")
            if val:
                result[attr] = val

        ttl_ms = env.get(c.env_ttl, "")
        if ttl_ms:
            with contextlib.suppress(ValueError, TypeError):
                result["ttl"] = str(int(ttl_ms) // 60000)

        return result

    def write_env_json(
        self,
        model: str,
        base_url: str,
        opus: str,
        sonnet: str,
        haiku: str,
        ttl_ms: str,
    ) -> dict[str, str]:
        """Build the env block dict for settings.json."""
        return {
            "ANTHROPIC_MODEL": model,
            "ANTHROPIC_BASE_URL": base_url,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": opus,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": sonnet,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": haiku,
            "ANTHROPIC_CUSTOM_HEADERS": "x-databricks-use-coding-agent-mode: true",
            "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
            "CLAUDE_CODE_API_KEY_HELPER_TTL_MS": ttl_ms,
        }

    def ensure_onboarding(self) -> None:
        """Set hasCompletedOnboarding in ~/.claude.json."""
        claude_json = Path.home() / ".claude.json"

        if claude_json.is_file():
            try:
                data = json.loads(claude_json.read_text())
            except (json.JSONDecodeError, OSError):
                data = {}
            if data.get("hasCompletedOnboarding") is True:
                log.debug(f"agent_ensure_onboarding: already set in {claude_json}")
                return
        else:
            data = {}

        log.subheading("Onboarding flag")
        data["hasCompletedOnboarding"] = True

        tmp_path = claude_json.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2) + "\n")
        tmp_path.chmod(0o600)
        tmp_path.rename(claude_json)

        log.debug(f"agent_ensure_onboarding: set hasCompletedOnboarding=true in {claude_json}")
        log.success(f"Onboarding flag set in {claude_json}.")

    def register_plugin(self, script_dir: Path) -> None:
        """Register plugin in ~/.claude/plugins/installed_plugins.json."""
        plugin_manifest = script_dir / ".claude-plugin" / "plugin.json"
        if not plugin_manifest.is_file():
            return

        plugins_file = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        plugins_file.parent.mkdir(parents=True, exist_ok=True)

        plugins: dict = {}
        if plugins_file.is_file():
            try:
                plugins = json.loads(plugins_file.read_text())
            except (json.JSONDecodeError, OSError):
                plugins = {}

        existing_path = (plugins.get("fmapi-codingagent") or {}).get("installPath", "")
        if existing_path == str(script_dir):
            return  # Already registered with correct path

        plugins["fmapi-codingagent"] = {
            "scope": "user",
            "installPath": str(script_dir),
        }

        tmp_path = plugins_file.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(plugins, indent=2) + "\n")
        tmp_path.rename(plugins_file)

        log.success(
            "Plugin registered (skills: /fmapi-codingagent-status, "
            "/fmapi-codingagent-reauth, /fmapi-codingagent-setup, "
            "/fmapi-codingagent-doctor, /fmapi-codingagent-list-models, "
            "/fmapi-codingagent-validate-models)."
        )

    def deregister_plugin(self) -> None:
        """Remove plugin from ~/.claude/plugins/installed_plugins.json."""
        plugins_file = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        if not plugins_file.is_file():
            return

        try:
            plugins = json.loads(plugins_file.read_text())
        except (json.JSONDecodeError, OSError):
            return

        if "fmapi-codingagent" not in plugins:
            return

        del plugins["fmapi-codingagent"]

        if not plugins:
            plugins_file.unlink(missing_ok=True)
            log.success("Removed plugin registration (file deleted -- no other plugins).")
        else:
            tmp_path = plugins_file.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(plugins, indent=2) + "\n")
            tmp_path.rename(plugins_file)
            log.success(f"Removed plugin registration from {plugins_file}.")

    def install_cli(self) -> None:
        """Install the agent CLI if missing."""
        c = self._config
        if shutil.which(c.cli_cmd):
            log.success(f"{c.name} already installed.")
        else:
            log.info(f"Installing {c.name} ...")
            subprocess.run(c.cli_install_cmd, shell=True, check=True)
            log.success(f"{c.name} installed.")

    def doctor_extra(self) -> bool:
        """Check hasCompletedOnboarding. Return True if pass."""
        console = _get_console()
        claude_json = Path.home() / ".claude.json"

        if claude_json.is_file():
            try:
                data = json.loads(claude_json.read_text())
            except (json.JSONDecodeError, OSError):
                data = {}
            if data.get("hasCompletedOnboarding") is True:
                console.print(
                    f"  [success]PASS[/success]  hasCompletedOnboarding is set  "
                    f"[dim]{claude_json}[/dim]"
                )
                return True
            else:
                console.print(
                    f"  [error]FAIL[/error]  hasCompletedOnboarding not set  "
                    f"[dim]Fix: re-run setup or add to {claude_json}[/dim]"
                )
                return False
        else:
            console.print(
                f"  [error]FAIL[/error]  {claude_json} not found  [dim]Fix: re-run setup[/dim]"
            )
            return False

    def dry_run_env_display(
        self,
        model: str,
        base_url: str,
        opus: str,
        sonnet: str,
        haiku: str,
        ttl_ms: str,
    ) -> None:
        """Print env vars for dry-run display."""
        console = _get_console()
        c = self._config
        for key, val in [
            (c.env_model, model),
            (c.env_base_url, base_url),
            (c.env_opus, opus),
            (c.env_sonnet, sonnet),
            (c.env_haiku, haiku),
            (c.env_ttl, ttl_ms),
        ]:
            console.print(f"       {key}=[bold]{val}[/bold]")

    def dry_run_extra(self, script_dir: Path) -> None:
        """Print onboarding and plugin registration dry-run sections."""
        console = _get_console()
        claude_json = Path.home() / ".claude.json"

        # Onboarding
        console.print("  [bold]Onboarding[/bold]")
        onboarding_done = False
        if claude_json.is_file():
            try:
                data = json.loads(claude_json.read_text())
                onboarding_done = data.get("hasCompletedOnboarding") is True
            except (json.JSONDecodeError, OSError):
                pass

        if onboarding_done:
            console.print(
                f"  [success]ok[/success]  hasCompletedOnboarding already set in "
                f"[dim]{claude_json}[/dim]"
            )
        else:
            console.print(
                f"  [info]::[/info]  Would set hasCompletedOnboarding=true in "
                f"[dim]{claude_json}[/dim]"
            )
        console.print()

        # Plugin registration
        console.print("  [bold]Plugin registration[/bold]")
        plugins_file = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
        already_registered = False
        if plugins_file.is_file():
            try:
                plugins = json.loads(plugins_file.read_text())
                existing_path = (plugins.get("fmapi-codingagent") or {}).get("installPath", "")
                already_registered = existing_path == str(script_dir)
            except (json.JSONDecodeError, OSError):
                pass

        if already_registered:
            console.print("  [success]ok[/success]  Already registered")
        else:
            console.print(f"  [info]::[/info]  Would register plugin at [bold]{script_dir}[/bold]")


def _get_console():
    """Helper to get the console (avoid circular imports)."""
    from fmapi_opskit.ui.console import get_console

    return get_console()
