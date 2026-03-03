"""Validate configured models command."""

from __future__ import annotations

import sys

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.auth import check_oauth_status
from fmapi_opskit.commands._common import require_fmapi_config
from fmapi_opskit.config.discovery import discover_config
from fmapi_opskit.network import fetch_endpoints, validate_model
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console
from fmapi_opskit.ui.tables import display_model_validation


def do_validate_models(adapter: AgentAdapter) -> None:
    """Validate that configured models exist and are ready."""
    require_fmapi_config(adapter, "validate-models")
    cfg = discover_config(adapter)

    if not check_oauth_status(cfg.profile):
        log.error(f"OAuth session expired or invalid. Run: setup-fmapi-{adapter.config.id} reauth")
        sys.exit(1)

    console = get_console()
    console.print("\n[bold]  FMAPI Model Validation[/bold]\n")

    endpoints = fetch_endpoints(cfg.profile)
    if endpoints is None:
        log.error("Failed to fetch serving endpoints. Check your network and profile.")
        sys.exit(1)

    models_to_check: list[tuple[str, str]] = []
    if cfg.model:
        models_to_check.append(("Model", cfg.model))
    if cfg.opus:
        models_to_check.append(("Opus", cfg.opus))
    if cfg.sonnet:
        models_to_check.append(("Sonnet", cfg.sonnet))
    if cfg.haiku:
        models_to_check.append(("Haiku", cfg.haiku))

    results: list[tuple[str, str, str, str]] = []
    for label, model_name in models_to_check:
        status, detail = validate_model(endpoints, model_name)
        results.append((label, model_name, status, detail))

    all_pass = display_model_validation(results)
    console.print()

    if not all_pass:
        log.info(
            "Some models failed validation. "
            "Run [info]list-models[/info] to see available endpoints."
        )
        console.print()
        sys.exit(1)

    log.success("All configured models are available and ready.")
    console.print()
