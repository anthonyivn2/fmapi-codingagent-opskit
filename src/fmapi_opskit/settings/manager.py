"""SettingsManager — read/write/merge settings.json (replaces jq operations)."""

from __future__ import annotations

import json
from pathlib import Path


class SettingsManager:
    """Manages the agent settings.json file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.is_file()

    def read(self) -> dict:
        """Read and parse settings.json. Returns empty dict if missing."""
        if not self.path.is_file():
            return {}
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def write(self, data: dict) -> None:
        """Atomically write settings.json with owner-only permissions."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2) + "\n")
        tmp_path.chmod(0o600)
        tmp_path.rename(self.path)

    def merge_env(
        self,
        new_env: dict[str, str],
        api_key_helper: str,
        legacy_cleanup_keys: tuple[str, ...] = (),
    ) -> None:
        """Merge env vars into settings, set apiKeyHelper, remove legacy keys."""
        settings = self.read()

        # Merge env block
        env = settings.get("env", {})
        env.update(new_env)

        # Remove legacy keys
        for key in legacy_cleanup_keys:
            env.pop(key, None)

        settings["env"] = env
        settings["apiKeyHelper"] = api_key_helper

        # Remove old _fmapi_meta if present
        settings.pop("_fmapi_meta", None)

        self.write(settings)

    def set_api_key_helper(self, helper_path: str) -> None:
        """Set the apiKeyHelper value."""
        settings = self.read()
        settings["apiKeyHelper"] = helper_path
        self.write(settings)

    def remove_fmapi_keys(self, uninstall_keys: tuple[str, ...]) -> bool:
        """Remove FMAPI-specific keys from settings. Returns True if file was deleted."""
        settings = self.read()
        if not settings:
            return False

        # Remove env keys
        env = settings.get("env", {})
        for key in uninstall_keys:
            env.pop(key, None)
        if not env:
            settings.pop("env", None)
        else:
            settings["env"] = env

        # Remove FMAPI-specific top-level keys
        settings.pop("_fmapi_meta", None)
        settings.pop("apiKeyHelper", None)

        # If nothing left, delete the file
        if not settings:
            self.path.unlink(missing_ok=True)
            return True

        self.write(settings)
        return False

    def get_env_value(self, key: str) -> str:
        """Get a single env value from settings."""
        settings = self.read()
        return settings.get("env", {}).get(key, "")

    def get_api_key_helper(self) -> str:
        """Get the apiKeyHelper path from settings."""
        return self.read().get("apiKeyHelper", "")
