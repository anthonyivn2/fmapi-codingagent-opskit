"""HTTP reachability, serving endpoint queries, and gateway URL utilities."""

from __future__ import annotations

import re
import urllib.request

from fmapi_opskit.auth import get_oauth_token, run_databricks_json

# ---------------------------------------------------------------------------
# HTTP reachability checks
# ---------------------------------------------------------------------------


def check_http_reachable(url: str, token: str, timeout: int = 10) -> int:
    """Check if a URL is reachable with bearer auth.

    Returns the HTTP status code, or 0 on connection failure.
    """
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Serving endpoint fetch / filter / validate
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Gateway URL building and workspace ID detection
# ---------------------------------------------------------------------------


def build_base_url(host: str, gateway_enabled: bool, workspace_id: str) -> str:
    """Build the Anthropic base URL.

    Returns the gateway URL when enabled, otherwise the serving-endpoints URL.
    """
    if gateway_enabled and workspace_id:
        return f"https://{workspace_id}.ai-gateway.cloud.databricks.com/anthropic"
    return f"{host}/serving-endpoints/anthropic"


def detect_workspace_id(profile: str, host: str) -> str:
    """Detect the workspace ID from the x-databricks-org-id response header.

    Returns the numeric workspace ID string, or empty string on failure.
    """
    if not profile or not host:
        return ""

    token = get_oauth_token(profile)
    if not token:
        return ""

    url = f"{host}/api/2.0/clusters/spark-versions"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            # Check response headers for org ID
            org_id = response.headers.get("x-databricks-org-id", "")
            if org_id and org_id.strip().isdigit():
                return org_id.strip()
    except Exception:
        pass

    return ""


def detect_gateway_from_url(base_url: str) -> tuple[bool, str]:
    """Detect if a base URL is an AI Gateway URL and extract workspace ID.

    Returns (is_gateway, workspace_id).
    """
    m = re.match(r"^https://(\d+)\.ai-gateway\.cloud\.databricks\.com", base_url)
    if m:
        return True, m.group(1)
    return False, ""
