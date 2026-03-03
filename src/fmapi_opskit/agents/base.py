"""Agent adapter base — AgentConfig dataclass and AgentAdapter Protocol."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class AgentConfig:
    """All agent-specific configuration values (replaces AGENT_* bash variables)."""

    # Identity
    name: str
    id: str
    cli_cmd: str
    cli_install_cmd: str

    # Settings paths
    settings_dir: str
    settings_filename: str
    helper_filename: str
    hook_precheck_filename: str

    # Defaults
    default_profile: str
    default_model: str
    default_opus: str
    default_sonnet: str
    default_haiku: str

    # Endpoint filtering
    endpoint_filter: str
    endpoint_title: str
    base_url_suffix: str

    # Environment variable names
    env_model: str
    env_base_url: str
    env_opus: str
    env_sonnet: str
    env_haiku: str
    env_ttl: str

    # Required env keys for doctor checks
    required_env_keys: tuple[str, ...] = ()

    # Legacy keys to remove from .env on write
    legacy_cleanup_keys: tuple[str, ...] = ()

    # All env keys to remove on uninstall
    uninstall_env_keys: tuple[str, ...] = ()


class AgentAdapter(Protocol):
    """Protocol defining the agent adapter contract (replaces agent_* bash functions)."""

    @property
    def config(self) -> AgentConfig: ...

    def settings_candidates(self) -> list[Path]:
        """Return settings file search paths (ordered by priority)."""
        ...

    def read_env(self, settings: dict) -> dict[str, str]:
        """Read model/TTL values from settings dict, return as {key: value}."""
        ...

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
        ...

    def ensure_onboarding(self) -> None:
        """Set agent-specific onboarding flags (e.g., hasCompletedOnboarding)."""
        ...

    def register_plugin(self, script_dir: Path) -> None:
        """Register the agent plugin."""
        ...

    def deregister_plugin(self) -> None:
        """Remove the agent plugin registration."""
        ...

    def install_cli(self) -> None:
        """Install the agent CLI if missing."""
        ...

    def doctor_extra(self) -> bool:
        """Run agent-specific doctor checks. Return True if all pass."""
        ...

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
        ...

    def dry_run_extra(self, script_dir: Path) -> None:
        """Print agent-specific dry-run sections."""
        ...
