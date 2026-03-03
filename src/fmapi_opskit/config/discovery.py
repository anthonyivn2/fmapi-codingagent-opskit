"""Discover existing FMAPI configuration from settings and helper files."""

from __future__ import annotations

import re
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.config.models import FmapiConfig


def discover_config(adapter: AgentAdapter) -> FmapiConfig:
    """Discover existing FMAPI configuration from settings and helper files.

    Searches settings candidates for a file with apiKeyHelper set,
    then parses the helper script for profile/host and the settings
    env block for model names and TTL.
    """
    cfg = FmapiConfig()

    for candidate in adapter.settings_candidates():
        if not candidate.is_file():
            continue

        abs_path = candidate.resolve()

        try:
            import json

            settings = json.loads(abs_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        helper = settings.get("apiKeyHelper", "")
        if not helper:
            continue

        cfg.found = True
        cfg.settings_file = str(abs_path)
        cfg.helper_file = helper

        # Parse helper script for FMAPI_* variables
        helper_path = Path(helper)
        if helper_path.is_file():
            try:
                helper_text = helper_path.read_text()
            except OSError:
                helper_text = ""

            # Profile: try FMAPI_PROFILE first, then legacy PROFILE
            m = re.search(r'^FMAPI_PROFILE="(.*?)"', helper_text, re.MULTILINE)
            if not m:
                m = re.search(r'^PROFILE="(.*?)"', helper_text, re.MULTILINE)
            if m:
                cfg.profile = m.group(1)

            # Host: try FMAPI_HOST first, then legacy HOST
            m = re.search(r'^FMAPI_HOST="(.*?)"', helper_text, re.MULTILINE)
            if not m:
                m = re.search(r'^HOST="(.*?)"', helper_text, re.MULTILINE)
            if m:
                cfg.host = m.group(1).rstrip("/")

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

        break  # Use first match

    return cfg
