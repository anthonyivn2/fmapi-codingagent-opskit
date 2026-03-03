"""HTTP reachability checks (urllib, replaces curl)."""

from __future__ import annotations

import urllib.request


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
