"""FmapiConfig dataclass and config validation constants."""

from __future__ import annotations

from dataclasses import dataclass

VALID_CONFIG_KEYS = frozenset(
    {
        "host",
        "profile",
        "provider_name",
        "model",
        "model_reasoning_effort",
        "opus",
        "sonnet",
        "haiku",
        "ttl",
        "settings_location",
        "ai_gateway",
        "workspace_id",
        "provider_id",
    }
)


@dataclass
class FmapiConfig:
    """Discovered or loaded FMAPI configuration."""

    found: bool = False

    # From helper script parsing
    host: str = ""
    profile: str = ""

    # From settings.json env block
    model: str = ""
    model_reasoning_effort: str = ""
    opus: str = ""
    sonnet: str = ""
    haiku: str = ""
    ttl: str = ""  # minutes as string

    # Gateway settings
    ai_gateway: str = ""  # "true" or "false"
    workspace_id: str = ""

    # TOML provider/profile name (Codex only)
    provider_id: str = ""
    provider_name: str = ""

    # File paths
    settings_file: str = ""
    helper_file: str = ""


@dataclass
class FileConfig:
    """Values loaded from a config file (--config / --config-url)."""

    host: str = ""
    profile: str = ""
    model: str = ""
    model_reasoning_effort: str = ""
    opus: str = ""
    sonnet: str = ""
    haiku: str = ""
    ttl: str = ""
    settings_location: str = ""
    ai_gateway: str = ""
    workspace_id: str = ""
    provider_id: str = ""
    provider_name: str = ""
