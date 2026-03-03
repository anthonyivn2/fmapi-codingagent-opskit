"""OAuth token management — get, validate, refresh."""

from __future__ import annotations

from fmapi_opskit.auth.databricks import run_databricks_json


def get_oauth_token(profile: str) -> str:
    """Get an OAuth access token for the given profile.

    Returns the token string, or empty string on failure.
    """
    if not profile:
        return ""
    data = run_databricks_json("auth", "token", profile=profile)
    if isinstance(data, dict):
        return data.get("access_token", "")
    return ""


def check_oauth_status(profile: str) -> bool:
    """Check if the OAuth token is currently valid."""
    return bool(get_oauth_token(profile))
