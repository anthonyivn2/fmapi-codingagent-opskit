"""OAuth re-authentication command."""

from __future__ import annotations

import sys

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth import auth_login, check_oauth_status, clear_helper_token_cache
from fmapi_opskit.commands._common import require_fmapi_config
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.setup.writer import migrate_helper_if_needed
from fmapi_opskit.ui import logging as log


def do_reauth(adapter: AgentAdapter) -> None:
    """Re-authenticate Databricks OAuth session."""
    require_fmapi_config(adapter, "reauth")
    cfg = discover_config(adapter)

    migrate_helper_if_needed(
        adapter,
        helper_file=cfg.helper_file,
        host=cfg.host,
        profile=cfg.profile,
        reason="reauth",
    )

    log.info(f"Re-authenticating with Databricks (profile: {cfg.profile}) ...")

    if not auth_login(cfg.host, cfg.profile):
        log.error(
            f"Re-authentication failed. Try manually: "
            f"databricks auth login --host {cfg.host} --profile {cfg.profile}"
        )
        sys.exit(1)

    if clear_helper_token_cache(cfg.helper_file):
        log.debug("reauth: cleared helper token cache after successful login")

    if check_oauth_status(cfg.profile):
        log.success(f"OAuth session re-established for profile '{cfg.profile}'.")
    else:
        log.error(
            f"Re-authentication failed. Try manually: "
            f"databricks auth login --host {cfg.host} --profile {cfg.profile}"
        )
        sys.exit(1)
