"""URL building, workspace ID detection, and gateway utilities."""

from __future__ import annotations

import re
import urllib.request

from fmapi_opskit.auth.oauth import get_oauth_token


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
