"""Tests for hook merge/uninstall logic."""

from __future__ import annotations

from fmapi_opskit.settings.hooks import (
    get_fmapi_hook_command,
    is_fmapi_hook_entry,
    remove_fmapi_hooks,
)

NEW_CMD = "/new/path/fmapi-auth-precheck.sh"
USER_CMD = "/user/custom-hook.sh"


def _entry(cmd: str) -> dict:
    return {"hooks": [{"type": "command", "command": cmd}]}


def _cmds(settings: dict, hook_type: str) -> list[str]:
    return [
        h["command"]
        for e in settings.get("hooks", {}).get(hook_type, [])
        for h in e.get("hooks", [])
    ]


def test_is_fmapi_detects_auth_precheck():
    entry = _entry("/path/to/fmapi-auth-precheck.sh")
    assert is_fmapi_hook_entry(entry) is True, "Should detect fmapi-auth-precheck.sh as FMAPI hook"


def test_is_fmapi_detects_legacy_subagent_precheck():
    entry = _entry("/old/fmapi-subagent-precheck.sh")
    assert is_fmapi_hook_entry(entry) is True, (
        "Should detect legacy fmapi-subagent-precheck.sh as FMAPI hook"
    )


def test_is_fmapi_rejects_unrelated_hook():
    entry = _entry(USER_CMD)
    assert is_fmapi_hook_entry(entry) is False, (
        f"Should reject unrelated hook '{USER_CMD}' as non-FMAPI"
    )


def test_is_fmapi_handles_missing_hooks_key():
    assert is_fmapi_hook_entry({}) is False, "Empty dict should not crash and should return False"


def test_remove_strips_fmapi_keeps_user():
    settings = {"hooks": {"SubagentStart": [_entry(NEW_CMD), _entry(USER_CMD)]}}
    remove_fmapi_hooks(settings)
    remaining = _cmds(settings, "SubagentStart")
    assert remaining == [USER_CMD], f"Only user hook should remain, got {remaining}"


def test_remove_cleans_empty_hooks_section():
    settings = {
        "hooks": {"SubagentStart": [_entry(NEW_CMD)], "UserPromptSubmit": [_entry(NEW_CMD)]}
    }
    remove_fmapi_hooks(settings)
    assert "hooks" not in settings, (
        f"Empty hooks section should be removed, got keys: {list(settings.keys())}"
    )


def test_remove_no_hooks_is_noop():
    settings = {"env": {"KEY": "val"}}
    remove_fmapi_hooks(settings)
    assert "hooks" not in settings, "Should not create a hooks key when none existed"
    assert settings["env"]["KEY"] == "val", "Existing keys should be untouched"


def test_get_command_returns_when_present():
    settings = {"hooks": {"SubagentStart": [_entry(NEW_CMD)]}}
    result = get_fmapi_hook_command(settings, "SubagentStart")
    assert result == NEW_CMD, f"Expected '{NEW_CMD}', got '{result}'"


def test_get_command_returns_empty_when_absent():
    settings = {"hooks": {"SubagentStart": [_entry(NEW_CMD)]}}
    result = get_fmapi_hook_command(settings, "UserPromptSubmit")
    assert result == "", f"Expected empty string for missing hook type, got '{result}'"
