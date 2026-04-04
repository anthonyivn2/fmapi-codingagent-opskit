"""Discover existing FMAPI configuration from settings and helper files."""

from __future__ import annotations

import re
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.config.models import FmapiConfig


def discover_config(adapter: AgentAdapter) -> FmapiConfig:
    """Discover existing FMAPI configuration from settings and helper files.

    Searches settings candidates for a file containing FMAPI configuration.
    Dispatches to JSON or TOML parsing based on file extension.
    """
    cfg = FmapiConfig()

    for candidate in adapter.settings_candidates():
        if not candidate.is_file():
            continue

        abs_path = candidate.resolve()

        if abs_path.suffix == ".toml":
            cfg = _discover_from_toml(adapter, abs_path)
        else:
            cfg = _discover_from_json(adapter, abs_path)

        if cfg.found:
            break

    return cfg


def _parse_helper_script(helper_path: Path, cfg: FmapiConfig) -> None:
    """Parse the helper script for FMAPI_PROFILE and FMAPI_HOST."""
    if not helper_path.is_file():
        return

    try:
        helper_text = helper_path.read_text()
    except OSError:
        return

    # Profile: try FMAPI_PROFILE first, then legacy PROFILE
    m = re.search(r'''^FMAPI_PROFILE=['"](.*?)['"]''', helper_text, re.MULTILINE)
    if not m:
        m = re.search(r'''^PROFILE=['"](.*?)['"]''', helper_text, re.MULTILINE)
    if m:
        cfg.profile = m.group(1)

    # Host: try FMAPI_HOST first, then legacy HOST
    m = re.search(r'''^FMAPI_HOST=['"](.*?)['"]''', helper_text, re.MULTILINE)
    if not m:
        m = re.search(r'''^HOST=['"](.*?)['"]''', helper_text, re.MULTILINE)
    if m:
        cfg.host = m.group(1).rstrip("/")


def _discover_from_json(adapter: AgentAdapter, abs_path: Path) -> FmapiConfig:
    """Discover FMAPI configuration from a JSON settings file."""
    cfg = FmapiConfig()

    try:
        import json

        settings = json.loads(abs_path.read_text())
    except (json.JSONDecodeError, OSError):
        return cfg

    helper = settings.get("apiKeyHelper", "")
    if not helper:
        return cfg

    cfg.found = True
    cfg.settings_file = str(abs_path)
    cfg.helper_file = helper

    _parse_helper_script(Path(helper), cfg)

    # Parse model names and TTL from settings.json env block
    env_vals = adapter.read_env(settings)
    cfg.model = env_vals.get("model", "")
    cfg.opus = env_vals.get("opus", "")
    cfg.sonnet = env_vals.get("sonnet", "")
    cfg.haiku = env_vals.get("haiku", "")
    cfg.ttl = env_vals.get("ttl", "")

    # Detect AI Gateway v2 from base URL
    base_url = settings.get("env", {}).get(adapter.config.env_base_url, "")
    gw_match = re.match(r"^https://(\d+)\.ai-gateway\.cloud\.databricks\.com", base_url)
    if gw_match:
        cfg.ai_gateway = "true"
        cfg.workspace_id = gw_match.group(1)
    else:
        cfg.ai_gateway = "false"

    return cfg


def _discover_from_toml(adapter: AgentAdapter, abs_path: Path) -> FmapiConfig:
    """Discover FMAPI configuration from a TOML config file."""
    cfg = FmapiConfig()

    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib  # type: ignore[no-redef]

        data = tomllib.loads(abs_path.read_text())
    except Exception:
        return cfg

    # Find FMAPI provider by checking auth.command for fmapi-key-helper
    providers = data.get("model_providers", {})
    for provider_key, provider in providers.items():
        auth = provider.get("auth", {})
        command = auth.get("command", "")
        if not (command and "fmapi-key-helper" in command):
            continue

        cfg.found = True
        cfg.settings_file = str(abs_path)
        cfg.helper_file = command
        cfg.provider_id = provider_key

        _parse_helper_script(Path(command), cfg)

        # Read model and TTL from TOML structure
        env_vals = adapter.read_env(data)
        cfg.model = env_vals.get("model", "")
        cfg.ttl = env_vals.get("ttl", "")

        # Detect AI Gateway v2 from base_url
        base_url = provider.get("base_url", "")
        gw_match = re.match(r"^https://(\d+)\.ai-gateway\.cloud\.databricks\.com", base_url)
        if gw_match:
            cfg.ai_gateway = "true"
            cfg.workspace_id = gw_match.group(1)
        else:
            cfg.ai_gateway = "false"

        break

    return cfg
