"""Config file and URL loading with validation."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from fmapi_opskit.config.models import VALID_CONFIG_KEYS, FileConfig


class ConfigError(Exception):
    """Raised when config file validation fails."""


def load_config_file(path: str | Path) -> FileConfig:
    """Load and validate a local JSON config file."""
    p = Path(path)

    if not p.is_file():
        raise ConfigError(f"Config file not found: {p}")
    if not p.stat().st_mode & 0o444:
        raise ConfigError(f"Config file is not readable: {p}")

    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON: {p}") from exc

    return _validate_and_parse(data)


def load_config_url(url: str) -> FileConfig:
    """Fetch a remote JSON config and validate it."""
    if not url.startswith("https://"):
        raise ConfigError("Config URL must use HTTPS.")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fmapi-opskit"})
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except Exception as e:
        raise ConfigError(f"Failed to fetch config from URL: {url} ({e})") from e

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config URL did not return valid JSON: {url}") from exc

    return _validate_and_parse(data)


def _validate_and_parse(data: dict) -> FileConfig:
    """Validate config data and return a FileConfig."""
    # Validate version
    version = data.get("version")
    if version is not None and version != 1:
        raise ConfigError(f"Unsupported config file version: {version} (expected: 1).")

    # Reject unknown keys
    all_valid = VALID_CONFIG_KEYS | {"version"}
    unknown = set(data.keys()) - all_valid
    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        valid_list = "version, " + ", ".join(sorted(VALID_CONFIG_KEYS))
        raise ConfigError(f"Unknown keys in config file: {unknown_list}. Valid keys: {valid_list}")

    cfg = FileConfig()

    # host
    host = data.get("host", "")
    if host:
        if not host.startswith("https://"):
            raise ConfigError(f"Config file: host must start with https://. Got: {host}")
        cfg.host = host

    # profile
    profile = data.get("profile", "")
    if profile:
        if not re.match(r"^[a-zA-Z0-9_-]+$", profile):
            raise ConfigError(
                f"Config file: invalid profile name '{profile}'. "
                "Use letters, numbers, hyphens, and underscores."
            )
        cfg.profile = profile

    # model names (no validation needed, just strings)
    for field_name in ("model", "opus", "sonnet", "haiku"):
        val = data.get(field_name, "")
        if val:
            setattr(cfg, field_name, str(val))

    # settings_location
    cfg.settings_location = str(data.get("settings_location", ""))

    # ttl
    raw_ttl = data.get("ttl")
    if raw_ttl is not None:
        ttl_str = str(raw_ttl)
        if not ttl_str.isdigit() or int(ttl_str) <= 0:
            raise ConfigError(
                f"Config file: ttl must be a positive integer (minutes). Got: {raw_ttl}"
            )
        if int(ttl_str) > 60:
            raise ConfigError(f"Config file: ttl cannot exceed 60 minutes. Got: {raw_ttl}")
        cfg.ttl = ttl_str

    # ai_gateway
    raw_gw = data.get("ai_gateway")
    if raw_gw is not None:
        if raw_gw is True:
            cfg.ai_gateway = "true"
        elif raw_gw is False:
            cfg.ai_gateway = "false"
        elif str(raw_gw) in ("true", "false"):
            cfg.ai_gateway = str(raw_gw)
        else:
            raise ConfigError(f"Config file: ai_gateway must be true or false. Got: {raw_gw}")

    # workspace_id
    raw_ws = data.get("workspace_id")
    if raw_ws is not None and str(raw_ws):
        ws_str = str(raw_ws)
        if ws_str and not ws_str.isdigit():
            raise ConfigError(f"Config file: workspace_id must be numeric. Got: {raw_ws}")
        cfg.workspace_id = ws_str

    return cfg
