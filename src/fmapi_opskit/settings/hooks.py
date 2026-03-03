"""Hook merge/cleanup/uninstall logic for settings.json hooks section."""

from __future__ import annotations

import re

# Matches FMAPI hook entries (both current and legacy filenames)
_FMAPI_HOOK_PATTERN = re.compile(r"fmapi-auth-precheck|fmapi-subagent-precheck")


def is_fmapi_hook_entry(entry: dict) -> bool:
    """Check if a hook entry is an FMAPI-managed hook."""
    hooks = entry.get("hooks", [])
    for hook in hooks:
        cmd = hook.get("command", "")
        if _FMAPI_HOOK_PATTERN.search(cmd):
            return True
    return False


def _build_hook_entry(hook_command: str) -> dict:
    """Build a single FMAPI hook entry."""
    return {
        "hooks": [
            {
                "type": "command",
                "command": hook_command,
            }
        ]
    }


def merge_fmapi_hooks(settings: dict, hook_command: str) -> dict:
    """Filter out old FMAPI entries, append new, for both SubagentStart and UserPromptSubmit.

    Returns the modified settings dict (mutates in place).
    """
    hooks = settings.setdefault("hooks", {})
    new_entry = _build_hook_entry(hook_command)

    for hook_type in ("SubagentStart", "UserPromptSubmit"):
        # Get existing entries, filter out FMAPI ones
        existing = hooks.get(hook_type, [])
        filtered = [e for e in existing if not is_fmapi_hook_entry(e)]
        # Append the new FMAPI entry
        filtered.append(new_entry)
        hooks[hook_type] = filtered

    return settings


def remove_fmapi_hooks(settings: dict) -> dict:
    """Remove FMAPI hook entries, keep user hooks, clean empty sections.

    Returns the modified settings dict (mutates in place).
    """
    hooks = settings.get("hooks")
    if not hooks:
        return settings

    for hook_type in ("SubagentStart", "UserPromptSubmit"):
        entries = hooks.get(hook_type, [])
        filtered = [e for e in entries if not is_fmapi_hook_entry(e)]
        if filtered:
            hooks[hook_type] = filtered
        else:
            hooks.pop(hook_type, None)

    if not hooks:
        settings.pop("hooks", None)

    return settings


def get_fmapi_hook_command(settings: dict, hook_type: str) -> str:
    """Get the FMAPI hook command path for a given hook type.

    Returns the command path string, or empty string if not found.
    """
    hooks = settings.get("hooks", {})
    entries = hooks.get(hook_type, [])
    for entry in entries:
        if is_fmapi_hook_entry(entry):
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if _FMAPI_HOOK_PATTERN.search(cmd):
                    return cmd
    return ""
