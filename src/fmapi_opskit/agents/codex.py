"""Codex agent adapter — implements AgentAdapter Protocol for OpenAI Codex CLI."""

from __future__ import annotations

import contextlib
import shutil
import subprocess
from pathlib import Path

from fmapi_opskit.agents.base import AgentConfig
from fmapi_opskit.ui import logging as log

# Codex-specific TOML configuration constants
PROVIDER_ID = "databricks"
PROVIDER_NAME = "Databricks FMAPI"
WIRE_API = "responses"
AUTH_TIMEOUT_MS = 10000

CODEX_CONFIG = AgentConfig(
    # Identity
    name="Codex",
    id="codex",
    cli_cmd="codex",
    setup_cmd="setup-fmapi-codex",
    cli_install_cmd="npm install -g @openai/codex",
    # Settings paths
    settings_dir=".codex",
    settings_filename="config.toml",
    helper_filename="fmapi-key-helper.sh",
    hook_precheck_filename="",
    # Defaults
    default_profile="fmapi-codex-profile",
    default_model="databricks-gpt-5-2",
    default_opus="",
    default_sonnet="",
    default_haiku="",
    # Endpoint filtering
    endpoint_filter=r"gpt|openai",
    endpoint_title="OpenAI",
    base_url_suffix="/serving-endpoints/openai/v1",
    # Environment variable names (not used — Codex uses TOML config)
    env_model="",
    env_base_url="",
    env_opus="",
    env_sonnet="",
    env_haiku="",
    env_ttl="",
    # No env keys (TOML-based config)
    required_env_keys=(),
    legacy_cleanup_keys=(),
    uninstall_env_keys=(),
)


class CodexAdapter:
    """Codex agent adapter — TOML-based configuration."""

    def __init__(self) -> None:
        self._config = CODEX_CONFIG

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
        """Read model/TTL from parsed TOML settings dict."""
        result: dict[str, str] = {}

        # Get model from default profile
        profiles = settings.get("profiles", {})
        default_prof = profiles.get("default", {})
        model = default_prof.get("model", "")
        if model:
            result["model"] = model

        # Get TTL from provider auth refresh_interval_ms
        provider_id = default_prof.get("model_provider", PROVIDER_ID)
        providers = settings.get("model_providers", {})
        provider = providers.get(provider_id, {})
        auth = provider.get("auth", {})

        refresh_ms = auth.get("refresh_interval_ms")
        if refresh_ms is not None:
            with contextlib.suppress(ValueError, TypeError):
                result["ttl"] = str(int(refresh_ms) // 60000)

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
        """Build a flat dict representation for display/compatibility purposes."""
        return {
            "model": model,
            "base_url": base_url,
            "refresh_interval_ms": ttl_ms,
        }

    def ensure_onboarding(self) -> None:
        """No onboarding flag needed for Codex."""
        log.debug("ensure_onboarding: no onboarding flag for Codex")

    def register_plugin(self, script_dir: Path) -> None:
        """No plugin registration for Codex."""
        log.debug("register_plugin: no plugin registration for Codex")

    def deregister_plugin(self) -> None:
        """No plugin deregistration for Codex."""
        log.debug("deregister_plugin: no plugin to deregister for Codex")

    def install_cli(self) -> None:
        """Install the Codex CLI if missing."""
        c = self._config
        if shutil.which(c.cli_cmd):
            log.success(f"{c.name} already installed.")
        else:
            log.info(f"Installing {c.name} ...")
            subprocess.run(c.cli_install_cmd, shell=True, check=True)
            log.success(f"{c.name} installed.")

    def doctor_extra(self) -> bool:
        """Check Codex TOML config is valid. Return True if pass."""
        console = _get_console()
        c = self._config

        config_path = Path.home() / c.settings_dir / c.settings_filename
        if not config_path.is_file():
            console.print(
                f"  [error]FAIL[/error]  {config_path} not found  [dim]Fix: re-run setup[/dim]"
            )
            return False

        try:
            try:
                import tomllib
            except ModuleNotFoundError:
                import tomli as tomllib  # type: ignore[no-redef]

            data = tomllib.loads(config_path.read_text())
        except Exception:
            console.print(
                f"  [error]FAIL[/error]  {config_path} is not valid TOML  "
                f"[dim]Fix: re-run setup[/dim]"
            )
            return False

        # Check for databricks provider
        providers = data.get("model_providers", {})
        if PROVIDER_ID not in providers:
            console.print(
                f"  [error]FAIL[/error]  No '{PROVIDER_ID}' provider in config  "
                f"[dim]Fix: re-run setup[/dim]"
            )
            return False

        provider = providers[PROVIDER_ID]
        auth = provider.get("auth", {})
        if not auth.get("command"):
            console.print(
                "  [error]FAIL[/error]  No auth command configured  [dim]Fix: re-run setup[/dim]"
            )
            return False

        console.print(
            f"  [success]PASS[/success]  Codex TOML config is valid  [dim]{config_path}[/dim]"
        )
        return True

    def dry_run_env_display(
        self,
        model: str,
        base_url: str,
        opus: str,
        sonnet: str,
        haiku: str,
        ttl_ms: str,
    ) -> None:
        """Print TOML config for dry-run display."""
        console = _get_console()
        console.print("       [dim][profiles.default][/dim]")
        console.print(f"       model_provider = [bold]{PROVIDER_ID}[/bold]")
        console.print(f"       model = [bold]{model}[/bold]")
        console.print()
        console.print(f"       [dim][model_providers.{PROVIDER_ID}][/dim]")
        console.print(f"       name = [bold]{PROVIDER_NAME}[/bold]")
        console.print(f"       base_url = [bold]{base_url}[/bold]")
        console.print(f"       wire_api = [bold]{WIRE_API}[/bold]")
        console.print()
        console.print(f"       [dim][model_providers.{PROVIDER_ID}.auth][/dim]")
        console.print(f"       refresh_interval_ms = [bold]{ttl_ms}[/bold]")
        console.print(f"       timeout_ms = [bold]{AUTH_TIMEOUT_MS}[/bold]")

    def dry_run_extra(self, script_dir: Path) -> None:
        """Print Codex-specific dry-run sections."""
        console = _get_console()
        console.print("  [bold]Onboarding[/bold]")
        console.print("  [dim]No onboarding flag needed for Codex[/dim]")
        console.print()
        console.print("  [bold]Plugins[/bold]")
        console.print("  [dim]No plugin registration for Codex[/dim]")


def _get_console():
    """Helper to get the console (avoid circular imports)."""
    from fmapi_opskit.ui.console import get_console

    return get_console()
