"""TomlSettingsManager — read/write/merge config.toml for Codex."""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

import tomli_w


class TomlSettingsManager:
    """Manages the agent config.toml file."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        return self.path.is_file()

    def read(self) -> dict:
        """Read and parse config.toml. Returns empty dict if missing."""
        if not self.path.is_file():
            return {}
        try:
            return tomllib.loads(self.path.read_text())
        except Exception:
            return {}

    def write(self, data: dict) -> None:
        """Atomically write config.toml with owner-only permissions."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(".tmp")
        tmp_path.write_bytes(tomli_w.dumps(data).encode())
        tmp_path.chmod(0o600)
        tmp_path.rename(self.path)

    def merge_provider(
        self,
        *,
        provider_id: str,
        provider_name: str,
        base_url: str,
        wire_api: str,
        auth_command: str,
        refresh_interval_ms: int,
        timeout_ms: int,
        profile: str,
        model: str,
    ) -> None:
        """Merge a model provider block into config.toml.

        Sets the profile to use the provider, and configures the provider
        with base_url, wire_api, and command-backed auth.
        """
        data = self.read()

        # Set up profiles section
        profiles = data.setdefault("profiles", {})
        prof = profiles.setdefault(profile, {})
        prof["model_provider"] = provider_id
        prof["model"] = model

        # Set up model_providers section
        providers = data.setdefault("model_providers", {})
        provider = providers.setdefault(provider_id, {})
        provider["name"] = provider_name
        provider["base_url"] = base_url
        provider["wire_api"] = wire_api
        provider["auth"] = {
            "command": auth_command,
            "refresh_interval_ms": refresh_interval_ms,
            "timeout_ms": timeout_ms,
        }

        self.write(data)

    def remove_fmapi_provider(self, provider_id: str = "databricks") -> bool:
        """Remove the FMAPI provider from config.toml.

        Returns True if the file was deleted (nothing remaining).
        """
        data = self.read()
        if not data:
            return False

        # Remove provider block
        providers = data.get("model_providers", {})
        providers.pop(provider_id, None)
        if not providers:
            data.pop("model_providers", None)

        # Remove profiles that point to this provider
        profiles = data.get("profiles", {})
        for name in list(profiles):
            if profiles[name].get("model_provider") == provider_id:
                del profiles[name]
        if not profiles:
            data.pop("profiles", None)

        # If nothing remains, delete the file
        if not data:
            self.path.unlink(missing_ok=True)
            return True

        self.write(data)
        return False

    def get_provider_auth_command(self, provider_id: str = "databricks") -> str:
        """Get the auth command path from the provider block."""
        data = self.read()
        providers = data.get("model_providers", {})
        provider = providers.get(provider_id, {})
        return provider.get("auth", {}).get("command", "")
