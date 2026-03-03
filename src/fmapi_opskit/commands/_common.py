"""Common helpers shared across command modules."""

from __future__ import annotations

import sys

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth import has_databricks_cli
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.ui import logging as log


def require_fmapi_config(adapter: AgentAdapter, caller: str) -> None:
    """Common preamble: require databricks CLI, discover config, validate profile.

    Exits with error if any prerequisite is missing.
    """
    if not has_databricks_cli():
        log.error(f"Databricks CLI is required for {caller}.")
        sys.exit(1)

    cfg = discover_config(adapter)
    if not cfg.found:
        log.error("No FMAPI configuration found. Run setup first.")
        sys.exit(1)
    if not cfg.profile:
        log.error("Could not determine profile from helper script.")
        sys.exit(1)
