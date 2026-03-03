"""Fetch and filter serving endpoints via databricks CLI."""

from __future__ import annotations

import re

from fmapi_opskit.auth.databricks import run_databricks_json


def fetch_endpoints(profile: str) -> list[dict] | None:
    """Fetch all serving endpoints from the workspace.

    Returns a list of endpoint dicts, or None on failure.
    """
    data = run_databricks_json("serving-endpoints", "list", profile=profile)
    if isinstance(data, list):
        return data
    return None


def filter_agent_endpoints(endpoints: list[dict], filter_pattern: str) -> list[dict]:
    """Filter endpoints to those matching the agent's filter pattern."""
    try:
        pattern = re.compile(filter_pattern, re.IGNORECASE)
    except re.error:
        return []
    return [ep for ep in endpoints if pattern.search(ep.get("name", ""))]


def get_endpoint_state(endpoint: dict) -> str:
    """Extract the ready state from an endpoint dict."""
    state = endpoint.get("state", {})
    if isinstance(state, dict):
        return state.get("ready", state.get("config_update", "UNKNOWN"))
    return str(state) if state else "UNKNOWN"


def validate_model(endpoints: list[dict], model_name: str) -> tuple[str, str]:
    """Validate a model name against available endpoints.

    Returns (status, detail) where status is "PASS", "WARN", "FAIL".
    """
    for ep in endpoints:
        if ep.get("name") == model_name:
            state = get_endpoint_state(ep)
            if state == "READY":
                return "PASS", ""
            return "WARN", f"state: {state}"
    return "FAIL", "not found"
