"""Tests for hook merge/uninstall logic — ported from test-hooks.sh."""

from __future__ import annotations

import copy

from fmapi_opskit.settings.hooks import (
    get_fmapi_hook_command,
    is_fmapi_hook_entry,
    merge_fmapi_hooks,
    remove_fmapi_hooks,
)

NEW_HOOK = "/new/fmapi-auth-precheck.sh"
OLD_HOOK = "/old/fmapi-auth-precheck.sh"
LEGACY_HOOK = "/old/.claude/fmapi-subagent-precheck.sh"
USER_HOOK = "/user/hook.sh"


def _make_entry(command: str, matcher: str = "") -> dict:
    """Create a hook entry similar to what Claude Code uses."""
    entry: dict = {"hooks": [{"type": "command", "command": command}]}
    if matcher:
        entry["matcher"] = matcher
    return entry


def _fmapi_entry(command: str) -> dict:
    return _make_entry(command, "")


def _count_entries(settings: dict, hook_type: str) -> int:
    return len(settings.get("hooks", {}).get(hook_type, []))


def _get_commands(settings: dict, hook_type: str) -> list[str]:
    result = []
    for entry in settings.get("hooks", {}).get(hook_type, []):
        for hook in entry.get("hooks", []):
            result.append(hook.get("command", ""))
    return result


# --- Section: is_fmapi_hook_entry ---


class TestIsFmapiHookEntry:
    def test_matches_new_name(self):
        entry = _fmapi_entry("/path/to/fmapi-auth-precheck.sh")
        assert is_fmapi_hook_entry(entry)

    def test_matches_legacy_name(self):
        entry = _fmapi_entry("/path/to/fmapi-subagent-precheck.sh")
        assert is_fmapi_hook_entry(entry)

    def test_does_not_match_user_hook(self):
        entry = _fmapi_entry("/user/custom-hook.sh")
        assert not is_fmapi_hook_entry(entry)

    def test_does_not_match_empty(self):
        assert not is_fmapi_hook_entry({})

    def test_does_not_match_no_hooks(self):
        assert not is_fmapi_hook_entry({"matcher": "pattern"})


# --- Section: merge_fmapi_hooks - Fresh install ---


class TestMergeHooksFreshInstall:
    def test_fresh_install_creates_both_hook_types(self):
        settings = {"env": {"KEY": "val"}}
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 1
        assert _count_entries(settings, "UserPromptSubmit") == 1
        cmds = _get_commands(settings, "SubagentStart")
        assert cmds == [NEW_HOOK]
        # env preserved
        assert settings["env"]["KEY"] == "val"

    def test_fresh_install_on_empty_settings(self):
        settings = {}
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 1
        assert _count_entries(settings, "UserPromptSubmit") == 1


# --- Section: merge_fmapi_hooks - Idempotency ---


class TestMergeHooksIdempotency:
    def test_idempotency_replaces_old_no_duplicates(self):
        settings = {}
        merge_fmapi_hooks(settings, OLD_HOOK)
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 1
        assert _count_entries(settings, "UserPromptSubmit") == 1
        cmds = _get_commands(settings, "SubagentStart")
        assert cmds == [NEW_HOOK]

    def test_triple_write_produces_single_entry(self):
        settings = {}
        merge_fmapi_hooks(settings, NEW_HOOK)
        merge_fmapi_hooks(settings, NEW_HOOK)
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 1
        assert _count_entries(settings, "UserPromptSubmit") == 1


# --- Section: merge_fmapi_hooks - Preserve user hooks ---


class TestMergeHooksPreserveUser:
    def test_preserves_user_hooks_in_separate_entries(self):
        settings = {
            "hooks": {
                "SubagentStart": [_fmapi_entry(OLD_HOOK), _make_entry(USER_HOOK)],
            }
        }
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 2
        cmds = _get_commands(settings, "SubagentStart")
        assert USER_HOOK in cmds
        assert NEW_HOOK in cmds
        assert OLD_HOOK not in cmds

    def test_preserves_other_hook_types(self):
        settings = {
            "hooks": {
                "PreToolUse": [_make_entry("/lint.sh")],
                "SubagentStart": [_fmapi_entry(OLD_HOOK)],
            }
        }
        merge_fmapi_hooks(settings, NEW_HOOK)
        # PreToolUse untouched
        assert _count_entries(settings, "PreToolUse") == 1
        assert _get_commands(settings, "PreToolUse") == ["/lint.sh"]

    def test_multiple_user_entries_preserved(self):
        settings = {
            "hooks": {
                "SubagentStart": [
                    _make_entry("/user/a.sh"),
                    _fmapi_entry(OLD_HOOK),
                    _make_entry("/user/b.sh"),
                ],
            }
        }
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 3
        cmds = _get_commands(settings, "SubagentStart")
        assert "/user/a.sh" in cmds
        assert "/user/b.sh" in cmds
        assert NEW_HOOK in cmds

    def test_legacy_entries_replaced(self):
        settings = {
            "hooks": {
                "SubagentStart": [_fmapi_entry(LEGACY_HOOK)],
            }
        }
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 1
        cmds = _get_commands(settings, "SubagentStart")
        assert cmds == [NEW_HOOK]

    def test_mixed_old_and_new_resolved_to_single(self):
        settings = {
            "hooks": {
                "SubagentStart": [
                    _fmapi_entry(OLD_HOOK),
                    _fmapi_entry(NEW_HOOK),
                ],
            }
        }
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 1
        cmds = _get_commands(settings, "SubagentStart")
        assert cmds == [NEW_HOOK]

    def test_user_hooks_preserved_during_legacy_cleanup(self):
        settings = {
            "hooks": {
                "SubagentStart": [
                    _fmapi_entry(LEGACY_HOOK),
                    _make_entry("/user/custom-hook.sh"),
                ],
            }
        }
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 2
        cmds = _get_commands(settings, "SubagentStart")
        assert "/user/custom-hook.sh" in cmds
        assert NEW_HOOK in cmds


# --- Section: remove_fmapi_hooks - Uninstall ---


class TestRemoveHooks:
    def test_uninstall_removes_fmapi_keeps_user(self):
        settings = {
            "env": {"KEY": "val"},
            "hooks": {
                "SubagentStart": [_make_entry(USER_HOOK), _fmapi_entry(NEW_HOOK)],
                "UserPromptSubmit": [_fmapi_entry(NEW_HOOK)],
            },
        }
        remove_fmapi_hooks(settings)
        assert _count_entries(settings, "SubagentStart") == 1
        assert _get_commands(settings, "SubagentStart") == [USER_HOOK]
        assert "UserPromptSubmit" not in settings.get("hooks", {})
        assert settings["env"]["KEY"] == "val"

    def test_uninstall_only_fmapi_removes_hooks_section(self):
        settings = {
            "env": {"KEY": "val"},
            "hooks": {
                "SubagentStart": [_fmapi_entry(NEW_HOOK)],
                "UserPromptSubmit": [_fmapi_entry(NEW_HOOK)],
            },
        }
        remove_fmapi_hooks(settings)
        assert "hooks" not in settings
        assert settings["env"]["KEY"] == "val"

    def test_uninstall_no_hooks_section_unchanged(self):
        settings = {"env": {"KEY": "val"}}
        original = copy.deepcopy(settings)
        remove_fmapi_hooks(settings)
        assert settings == original

    def test_uninstall_preserves_other_hook_types(self):
        settings = {
            "hooks": {
                "SubagentStart": [_fmapi_entry(NEW_HOOK)],
                "UserPromptSubmit": [_fmapi_entry(NEW_HOOK)],
                "PreToolUse": [_make_entry("/lint.sh")],
            },
        }
        remove_fmapi_hooks(settings)
        assert "SubagentStart" not in settings["hooks"]
        assert "UserPromptSubmit" not in settings["hooks"]
        assert _count_entries(settings, "PreToolUse") == 1
        assert _get_commands(settings, "PreToolUse") == ["/lint.sh"]

    def test_uninstall_non_fmapi_entries_untouched(self):
        settings = {
            "hooks": {
                "SubagentStart": [_make_entry("/user/a.sh"), _make_entry("/user/b.sh")],
                "UserPromptSubmit": [_make_entry("/user/c.sh")],
            },
        }
        remove_fmapi_hooks(settings)
        assert _count_entries(settings, "SubagentStart") == 2
        assert _count_entries(settings, "UserPromptSubmit") == 1

    def test_uninstall_removes_legacy_entries(self):
        settings = {
            "hooks": {
                "SubagentStart": [
                    _fmapi_entry(LEGACY_HOOK),
                    _make_entry(USER_HOOK),
                ],
            },
        }
        remove_fmapi_hooks(settings)
        assert _count_entries(settings, "SubagentStart") == 1
        assert _get_commands(settings, "SubagentStart") == [USER_HOOK]


# --- Section: get_fmapi_hook_command - Discovery ---


class TestGetFmapiHookCommand:
    def test_finds_hook_in_subagent_start(self):
        settings = {
            "hooks": {
                "SubagentStart": [
                    _make_entry("/user/hook.sh"),
                    _fmapi_entry("/home/.claude/fmapi-auth-precheck.sh"),
                ],
            }
        }
        cmd = get_fmapi_hook_command(settings, "SubagentStart")
        assert cmd == "/home/.claude/fmapi-auth-precheck.sh"

    def test_finds_hook_in_user_prompt_submit(self):
        settings = {
            "hooks": {
                "UserPromptSubmit": [
                    _fmapi_entry("/home/.claude/fmapi-auth-precheck.sh"),
                ],
            }
        }
        cmd = get_fmapi_hook_command(settings, "UserPromptSubmit")
        assert cmd == "/home/.claude/fmapi-auth-precheck.sh"

    def test_finds_legacy_hook(self):
        settings = {
            "hooks": {
                "SubagentStart": [
                    _fmapi_entry("/home/.claude/fmapi-subagent-precheck.sh"),
                ],
            }
        }
        cmd = get_fmapi_hook_command(settings, "SubagentStart")
        assert cmd == "/home/.claude/fmapi-subagent-precheck.sh"

    def test_returns_empty_for_no_fmapi_hooks(self):
        settings = {
            "hooks": {
                "SubagentStart": [_make_entry("/user/hook.sh")],
            }
        }
        cmd = get_fmapi_hook_command(settings, "SubagentStart")
        assert cmd == ""

    def test_returns_empty_when_no_hooks_section(self):
        settings = {"env": {"KEY": "val"}}
        cmd = get_fmapi_hook_command(settings, "SubagentStart")
        assert cmd == ""

    def test_returns_empty_for_missing_hook_type(self):
        settings = {
            "hooks": {
                "SubagentStart": [_fmapi_entry(NEW_HOOK)],
            }
        }
        cmd = get_fmapi_hook_command(settings, "UserPromptSubmit")
        assert cmd == ""


# --- Section: End-to-end roundtrip ---


class TestRoundtrip:
    def test_write_then_uninstall_preserves_user(self):
        settings = {
            "hooks": {
                "SubagentStart": [_make_entry(USER_HOOK)],
            }
        }
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 2
        assert _count_entries(settings, "UserPromptSubmit") == 1

        remove_fmapi_hooks(settings)
        assert _count_entries(settings, "SubagentStart") == 1
        assert _get_commands(settings, "SubagentStart") == [USER_HOOK]
        assert "UserPromptSubmit" not in settings.get("hooks", {})

    def test_triple_write_idempotent(self):
        settings = {}
        merge_fmapi_hooks(settings, NEW_HOOK)
        merge_fmapi_hooks(settings, NEW_HOOK)
        merge_fmapi_hooks(settings, NEW_HOOK)
        assert _count_entries(settings, "SubagentStart") == 1
        assert _count_entries(settings, "UserPromptSubmit") == 1
        assert _get_commands(settings, "SubagentStart") == [NEW_HOOK]
        assert _get_commands(settings, "UserPromptSubmit") == [NEW_HOOK]
