"""Stress test for concurrent token locking.

Run with: uv run pytest tests/test_stress_token_locking.py -v

Requires a working FMAPI setup (helper script + valid OAuth session).
Skipped automatically if no configuration is found.
"""

from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest


def _find_helper() -> str | None:
    """Find the rendered key-helper script from an existing installation."""
    candidates = [
        Path.home() / ".claude" / "fmapi-key-helper.sh",
        Path.cwd() / ".claude" / "fmapi-key-helper.sh",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def _invoke_helper(helper_file: str, index: int) -> tuple[int, bool, float, str]:
    """Invoke the key-helper once. Returns (index, success, duration_s, error)."""
    start = time.monotonic()
    try:
        result = subprocess.run(
            [helper_file],
            capture_output=True,
            text=True,
            timeout=60,
        )
        elapsed = time.monotonic() - start
        if result.returncode == 0 and result.stdout.strip():
            return (index, True, elapsed, "")
        return (index, False, elapsed, result.stderr.strip() or "empty token")
    except subprocess.TimeoutExpired:
        return (index, False, time.monotonic() - start, "timeout")
    except Exception as e:
        return (index, False, time.monotonic() - start, str(e))


@pytest.fixture()
def helper_file():
    """Locate the key-helper script or skip the test."""
    path = _find_helper()
    if path is None:
        pytest.skip("No FMAPI key-helper found — run setup first")
    return path


@pytest.mark.slow
def test_concurrent_token_fetch(helper_file, concurrency=10):
    """Launch N parallel key-helper invocations and verify all succeed."""
    results: list[tuple[int, bool, float, str]] = []

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(_invoke_helper, helper_file, i): i for i in range(concurrency)}
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda r: r[0])

    failures = [(idx, err) for idx, ok, _, err in results if not ok]
    if failures:
        detail = "; ".join(f"worker {idx}: {err}" for idx, err in failures)
        pytest.fail(f"{len(failures)}/{concurrency} workers failed: {detail}")

    # All workers succeeded without timing out or returning empty tokens.
