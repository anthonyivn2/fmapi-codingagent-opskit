"""Tests for hook merge/uninstall logic."""

from __future__ import annotations

from fmapi_opskit.settings.hooks import (
    get_fmapi_hook_command,
    is_fmapi_hook_entry,
    merge_fmapi_hooks,
    remove_fmapi_hooks,
)

NEW = "/new/fmapi-auth-precheck.sh"
USER = "/user/hook.sh"


def _entry(cmd: str) -> dict:
    return {"hooks": [{"type": "command", "command": cmd}]}


def _cmds(s: dict, t: str) -> list[str]:
    return [h["command"] for e in s.get("hooks", {}).get(t, []) for h in e.get("hooks", [])]


def test_hook_lifecycle():
    # detection
    assert is_fmapi_hook_entry(_entry("/p/fmapi-auth-precheck.sh"))
    assert not is_fmapi_hook_entry(_entry(USER))

    # merge creates both types, idempotent
    s: dict = {}
    merge_fmapi_hooks(s, NEW)
    merge_fmapi_hooks(s, NEW)
    assert _cmds(s, "SubagentStart") == [NEW]
    assert _cmds(s, "UserPromptSubmit") == [NEW]

    # merge preserves user hooks
    s2 = {"hooks": {"SubagentStart": [_entry("/old/fmapi-auth-precheck.sh"), _entry(USER)]}}
    merge_fmapi_hooks(s2, NEW)
    cmds = _cmds(s2, "SubagentStart")
    assert NEW in cmds and USER in cmds

    # remove strips fmapi, keeps user
    remove_fmapi_hooks(s2)
    assert _cmds(s2, "SubagentStart") == [USER]

    # get_fmapi_hook_command
    s3 = {"hooks": {"SubagentStart": [_entry(NEW)]}}
    assert get_fmapi_hook_command(s3, "SubagentStart") == NEW
    assert get_fmapi_hook_command(s3, "UserPromptSubmit") == ""
