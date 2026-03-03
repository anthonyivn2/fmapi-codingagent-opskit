"""Post-setup verification (smoke test)."""

from __future__ import annotations

import subprocess

from fmapi_opskit.auth.oauth import get_oauth_token
from fmapi_opskit.network.connectivity import check_http_reachable
from fmapi_opskit.network.endpoints import fetch_endpoints, validate_model
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console
from fmapi_opskit.ui.tables import display_model_validation


def run_smoke_test(
    *,
    helper_file: str,
    host: str,
    profile: str,
    model: str,
    opus: str,
    sonnet: str,
    haiku: str,
    ai_gateway_enabled: bool,
    workspace_id: str,
) -> None:
    """Run post-setup verification checks."""
    log.heading("Verifying setup")
    console = get_console()
    warnings = 0

    # 1. Helper script returns a token
    try:
        result = subprocess.run(
            [helper_file],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            log.success("Helper script returns a valid token.")
        else:
            console.print("  [warning]WARN[/warning]  Helper script did not return a token.")
            warnings += 1
    except Exception:
        console.print(f"  [warning]WARN[/warning]  Helper script is not executable: {helper_file}")
        warnings += 1

    # 2. Workspace reachable
    token = get_oauth_token(profile)
    if token:
        code = check_http_reachable(f"{host}/api/2.0/serving-endpoints", token)
        if code == 200:
            log.success(f"Workspace reachable ({host}).")
        elif code > 0:
            console.print(f"  [warning]WARN[/warning]  Workspace returned HTTP {code}.")
            warnings += 1
        else:
            console.print(f"  [warning]WARN[/warning]  Cannot reach workspace at {host}.")
            warnings += 1

        # 3. Gateway connectivity
        if ai_gateway_enabled and workspace_id:
            gw_url = f"https://{workspace_id}.ai-gateway.cloud.databricks.com/anthropic/v1/messages"
            gw_code = check_http_reachable(gw_url, token)
            if gw_code > 0:
                log.success(f"AI Gateway v2 reachable (HTTP {gw_code}).")
            else:
                console.print(f"  [warning]WARN[/warning]  Cannot reach AI Gateway v2 at {gw_url}.")
                warnings += 1

        # 4. Validate configured models
        endpoints = fetch_endpoints(profile)
        if endpoints is not None:
            models_to_check: list[tuple[str, str]] = []
            if model:
                models_to_check.append(("Model", model))
            if opus:
                models_to_check.append(("Opus", opus))
            if sonnet:
                models_to_check.append(("Sonnet", sonnet))
            if haiku:
                models_to_check.append(("Haiku", haiku))

            results: list[tuple[str, str, str, str]] = []
            for label, name in models_to_check:
                status, detail = validate_model(endpoints, name)
                results.append((label, name, status, detail))

            if not display_model_validation(results):
                warnings += 1
        else:
            console.print(
                "  [warning]WARN[/warning]  Could not fetch serving endpoints for model validation."
            )
            warnings += 1
    else:
        console.print(
            "  [warning]WARN[/warning]  No OAuth token available -- "
            "skipping connectivity and model checks."
        )
        warnings += 1

    if warnings > 0:
        console.print(
            "\n  [yellow]Setup succeeded with warnings[/yellow] -- "
            "run [info]doctor[/info] for details."
        )
