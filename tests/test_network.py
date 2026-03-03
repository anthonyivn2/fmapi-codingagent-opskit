"""Tests for network module — pure logic only, no HTTP mocking."""

from __future__ import annotations

from fmapi_opskit.network import (
    build_base_url,
    detect_gateway_from_url,
    filter_agent_endpoints,
    get_endpoint_state,
    validate_model,
)


def test_filter_matches_by_pattern(sample_endpoints):
    result = filter_agent_endpoints(sample_endpoints, r"claude")
    names = [ep["name"] for ep in result]
    assert "databricks-claude-opus-4-6" in names, f"Opus should match 'claude', got {names}"
    assert "databricks-claude-sonnet-4-6" in names, f"Sonnet should match 'claude', got {names}"
    assert "databricks-llama-3-70b" not in names, f"Llama should not match 'claude', got {names}"


def test_filter_case_insensitive(sample_endpoints):
    result = filter_agent_endpoints(sample_endpoints, r"CLAUDE")
    assert len(result) == 3, (
        f"Case-insensitive 'CLAUDE' should match 3 endpoints, got {len(result)}: "
        f"{[ep['name'] for ep in result]}"
    )


def test_filter_no_match_returns_empty(sample_endpoints):
    result = filter_agent_endpoints(sample_endpoints, r"gemini")
    assert result == [], f"'gemini' should match nothing, got {[ep['name'] for ep in result]}"


def test_filter_invalid_regex_returns_empty(sample_endpoints):
    result = filter_agent_endpoints(sample_endpoints, r"[invalid")
    assert result == [], f"Invalid regex should return empty list, got {len(result)} results"


def test_state_extracts_ready():
    ep = {"name": "model", "state": {"ready": "READY"}}
    state = get_endpoint_state(ep)
    assert state == "READY", f"Expected 'READY' from state.ready, got '{state}'"


def test_state_falls_back_to_config_update():
    ep = {"name": "model", "state": {"config_update": "IN_PROGRESS"}}
    state = get_endpoint_state(ep)
    assert state == "IN_PROGRESS", (
        f"Expected 'IN_PROGRESS' from state.config_update fallback, got '{state}'"
    )


def test_state_missing_returns_unknown():
    ep = {"name": "model"}
    state = get_endpoint_state(ep)
    assert state == "UNKNOWN", f"Missing state key should return 'UNKNOWN', got '{state}'"


def test_state_non_dict_returns_string():
    ep = {"name": "model", "state": "some_string"}
    state = get_endpoint_state(ep)
    assert state == "some_string", f"Non-dict state should be stringified, got '{state}'"


def test_validate_pass_when_ready(sample_endpoints):
    status, detail = validate_model(sample_endpoints, "databricks-claude-opus-4-6")
    assert status == "PASS", f"Ready endpoint should PASS, got '{status}'"
    assert detail == "", f"PASS should have empty detail, got '{detail}'"


def test_validate_warn_when_not_ready(sample_endpoints):
    status, detail = validate_model(sample_endpoints, "databricks-claude-haiku-4-5")
    assert status == "WARN", f"Non-ready endpoint should WARN, got '{status}'"
    assert "IN_PROGRESS" in detail, f"WARN detail should mention state, got '{detail}'"


def test_validate_fail_when_not_found(sample_endpoints):
    status, detail = validate_model(sample_endpoints, "nonexistent-model")
    assert status == "FAIL", f"Missing endpoint should FAIL, got '{status}'"
    assert "not found" in detail, f"FAIL detail should say 'not found', got '{detail}'"


def test_build_url_with_gateway():
    url = build_base_url("https://example.com", gateway_enabled=True, workspace_id="12345")
    expected = "https://12345.ai-gateway.cloud.databricks.com/anthropic"
    assert url == expected, f"Gateway URL mismatch: expected '{expected}', got '{url}'"


def test_build_url_without_gateway():
    url = build_base_url("https://example.com", gateway_enabled=False, workspace_id="")
    expected = "https://example.com/serving-endpoints/anthropic"
    assert url == expected, f"Non-gateway URL mismatch: expected '{expected}', got '{url}'"


def test_detect_gateway_url():
    is_gw, ws_id = detect_gateway_from_url(
        "https://12345.ai-gateway.cloud.databricks.com/anthropic"
    )
    assert is_gw is True, "AI Gateway URL should be detected as gateway"
    assert ws_id == "12345", f"Workspace ID should be '12345', got '{ws_id}'"


def test_detect_non_gateway_url():
    is_gw, ws_id = detect_gateway_from_url("https://example.com/serving-endpoints/anthropic")
    assert is_gw is False, "Non-gateway URL should not be detected as gateway"
    assert ws_id == "", f"Non-gateway URL should have empty workspace ID, got '{ws_id}'"
