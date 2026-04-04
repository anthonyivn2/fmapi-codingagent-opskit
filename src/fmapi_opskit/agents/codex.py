"""Codex agent adapter — implements AgentAdapter Protocol for OpenAI Codex CLI."""

from __future__ import annotations

import contextlib
import shutil
import subprocess
from pathlib import Path

from fmapi_opskit.agents.base import AgentConfig
from fmapi_opskit.ui import logging as log

# Codex-specific TOML configuration constants
PROVIDER_ID = "databricks_fmapi"
PROVIDER_NAME = "Databricks FMAPI"
WIRE_API = "responses"
AUTH_TIMEOUT_MS = 10000

SKILL_NAMES = (
    "fmapi-codingagent-status",
    "fmapi-codingagent-reauth",
    "fmapi-codingagent-setup",
    "fmapi-codingagent-doctor",
    "fmapi-codingagent-list-models",
    "fmapi-codingagent-validate-models",
)

MIN_CODEX_VERSION = "0.118.0"

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
    # Version requirement
    min_cli_version=MIN_CODEX_VERSION,
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

        # Get model from active profile, with fallback to legacy "default"
        profiles = settings.get("profiles", {})
        active = settings.get("profile", "databricks_fmapi")
        default_prof = (
            profiles.get(active, {})
            or profiles.get("databricks_fmapi", {})
            or profiles.get("default", {})
        )
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
        """Copy skill files to ~/.agents/skills/ for Codex auto-discovery."""
        source_skills = script_dir / "skills-codex"
        if not source_skills.is_dir():
            log.debug(f"No skills-codex directory found at {source_skills}")
            return

        target_dir = Path.home() / ".agents" / "skills"
        target_dir.mkdir(parents=True, exist_ok=True)

        log.subheading("Skills")
        copied = 0
        for skill_dir in sorted(source_skills.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            dest = target_dir / skill_dir.name
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_md, dest / "SKILL.md")
            copied += 1

        if copied:
            log.success(f"Installed {copied} skill(s) to {target_dir}.")
        else:
            log.debug("No SKILL.md files found to install.")

    def deregister_plugin(self) -> None:
        """Remove FMAPI skill files from ~/.agents/skills/."""
        skills_dir = Path.home() / ".agents" / "skills"
        removed = 0
        for name in SKILL_NAMES:
            skill_dir = skills_dir / name
            if skill_dir.is_dir():
                shutil.rmtree(skill_dir)
                removed += 1
        if removed:
            log.success(f"Removed {removed} skill(s) from {skills_dir}.")

    def install_cli(self) -> None:
        """Install or upgrade the Codex CLI, ensuring minimum version requirement."""
        c = self._config
        installed_version = _get_codex_version()

        if installed_version:
            if _version_satisfies(installed_version, c.min_cli_version):
                log.success(f"{c.name} {installed_version} already installed.")
                return
            log.warn(
                f"{c.name} {installed_version} is below minimum required "
                f"version {c.min_cli_version}. Upgrading ..."
            )
            _upgrade_codex()
        else:
            log.info(f"Installing {c.name} ...")
            _install_codex()

        # Verify installation succeeded
        new_version = _get_codex_version()
        if new_version and _version_satisfies(new_version, c.min_cli_version):
            log.success(f"{c.name} {new_version} installed.")
        elif new_version:
            log.warn(
                f"{c.name} {new_version} installed but still below "
                f"minimum {c.min_cli_version}."
            )
        else:
            log.error(f"Failed to install {c.name}. Install manually and re-run setup.")

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

        # Check for FMAPI provider by scanning auth.command for fmapi-key-helper
        providers = data.get("model_providers", {})
        fmapi_provider = None
        for prov in providers.values():
            cmd = prov.get("auth", {}).get("command", "")
            if cmd and "fmapi-key-helper" in cmd:
                fmapi_provider = prov
                break

        if not fmapi_provider:
            console.print(
                "  [error]FAIL[/error]  No FMAPI provider in config  "
                "[dim]Fix: re-run setup[/dim]"
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
        provider_id: str = "",
    ) -> None:
        """Print TOML config for dry-run display."""
        console = _get_console()
        pid = provider_id or PROVIDER_ID
        console.print(f"       [dim][profiles.{pid}][/dim]")
        console.print(f"       model_provider = [bold]{pid}[/bold]")
        console.print(f"       model = [bold]{model}[/bold]")
        console.print()
        console.print(f"       [dim][model_providers.{pid}][/dim]")
        console.print(f"       name = [bold]{PROVIDER_NAME}[/bold]")
        console.print(f"       base_url = [bold]{base_url}[/bold]")
        console.print(f"       wire_api = [bold]{WIRE_API}[/bold]")
        console.print()
        console.print(f"       [dim][model_providers.{pid}.auth][/dim]")
        console.print(f"       refresh_interval_ms = [bold]{ttl_ms}[/bold]")
        console.print(f"       timeout_ms = [bold]{AUTH_TIMEOUT_MS}[/bold]")

    def dry_run_extra(self, script_dir: Path) -> None:
        """Print Codex-specific dry-run sections."""
        console = _get_console()
        c = self._config
        console.print("  [bold]Onboarding[/bold]")
        console.print("  [dim]No onboarding flag needed for Codex[/dim]")
        console.print()
        console.print("  [bold]Skills[/bold]")
        console.print(
            f"  [dim]Use '{c.setup_cmd} install-skills' after setup to install skills[/dim]"
        )


def _get_codex_version() -> str:
    """Return the installed Codex CLI version string, or empty if not found."""
    if not shutil.which("codex"):
        return ""
    try:
        result = subprocess.run(
            ["codex", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Output is typically "codex-cli 0.118.0" or "codex/0.118.0"
        version_text = result.stdout.strip()
        # Strip any prefix like "codex-cli " or "codex/"
        for sep in (" ", "/"):
            if sep in version_text:
                version_text = version_text.rsplit(sep, 1)[1]
        return version_text
    except (subprocess.SubprocessError, OSError):
        return ""


def _version_satisfies(installed: str, minimum: str) -> bool:
    """Check if installed version meets the minimum requirement.

    Compares version segments numerically (e.g. "0.1.2025011800" >= "0.1.2025011800").
    """
    if not minimum:
        return True
    try:
        installed_parts = [int(p) for p in installed.split(".")]
        minimum_parts = [int(p) for p in minimum.split(".")]
        # Pad shorter list with zeros for comparison
        max_len = max(len(installed_parts), len(minimum_parts))
        installed_parts.extend([0] * (max_len - len(installed_parts)))
        minimum_parts.extend([0] * (max_len - len(minimum_parts)))
        return installed_parts >= minimum_parts
    except (ValueError, AttributeError):
        # Non-numeric version — fall back to string comparison
        return installed >= minimum


def _install_codex() -> None:
    """Install Codex CLI via npm, falling back to brew if npm fails or is unavailable."""
    if shutil.which("npm"):
        try:
            subprocess.run(
                ["npm", "install", "-g", "@openai/codex"],
                check=True,
            )
            return
        except subprocess.CalledProcessError:
            log.warn("npm install failed, trying brew ...")

    # Fallback: brew
    if shutil.which("brew"):
        subprocess.run(["brew", "install", "codex"], check=True)
        return

    log.error(
        "Cannot install Codex: neither npm nor brew is available. "
        "Install Codex manually: npm install -g @openai/codex"
    )


def _upgrade_codex() -> None:
    """Upgrade Codex CLI via npm, falling back to brew if npm fails or is unavailable."""
    if shutil.which("npm"):
        try:
            subprocess.run(
                ["npm", "update", "-g", "@openai/codex"],
                check=True,
            )
            return
        except subprocess.CalledProcessError:
            log.warn("npm update failed, trying brew ...")

    # Fallback: brew
    if shutil.which("brew"):
        try:
            subprocess.run(["brew", "upgrade", "codex"], check=True)
            return
        except subprocess.CalledProcessError:
            log.warn("brew upgrade failed (Codex may not be brew-managed).")

    log.error(
        "Cannot upgrade Codex: neither npm nor brew succeeded. "
        "Upgrade manually: npm install -g @openai/codex"
    )


def _get_console():
    """Helper to get the console (avoid circular imports)."""
    from fmapi_opskit.ui.console import get_console

    return get_console()
