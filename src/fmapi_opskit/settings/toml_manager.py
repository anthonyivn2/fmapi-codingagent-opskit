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
        with base_url, wire_api, and command-backed OAuth auth.
        Cleans up old FMAPI providers/profiles if the name changed.
        """
        data = self.read()

        # Clean up old FMAPI providers with a different name
        # (handles name changes between installs)
        providers = data.get("model_providers", {})
        old_fmapi_ids = [
            pid
            for pid, prov in providers.items()
            if pid != provider_id
            and "fmapi-key-helper" in prov.get("auth", {}).get("command", "")
        ]
        for old_id in old_fmapi_ids:
            providers.pop(old_id, None)
            # Remove profiles that pointed to the old provider
            for pname in list(data.get("profiles", {})):
                if data["profiles"][pname].get("model_provider") == old_id:
                    del data["profiles"][pname]

        # Set top-level active profile
        data["profile"] = profile

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

        # Remove legacy env_key if present (replaced by auth.command)
        provider.pop("env_key", None)

        provider["auth"] = {
            "command": auth_command,
            "refresh_interval_ms": refresh_interval_ms,
            "timeout_ms": timeout_ms,
        }

        self.write(data)

    def remove_fmapi_provider(self) -> bool:
        """Remove FMAPI provider(s) from config.toml (name-agnostic).

        Scans all providers for ``fmapi-key-helper`` in ``auth.command``
        so uninstall works regardless of the provider ID chosen at setup.

        Returns True if the file was deleted (nothing remaining).
        """
        data = self.read()
        if not data:
            return False

        # Find FMAPI provider IDs by scanning auth.command
        providers = data.get("model_providers", {})
        fmapi_ids: list[str] = [
            pid
            for pid, prov in providers.items()
            if "fmapi-key-helper" in prov.get("auth", {}).get("command", "")
        ]

        if not fmapi_ids:
            return False

        # Remove matched provider blocks
        for pid in fmapi_ids:
            providers.pop(pid, None)
        if not providers:
            data.pop("model_providers", None)

        # Remove profiles that point to any removed provider
        profiles = data.get("profiles", {})
        removed_profile_names: list[str] = []
        for name in list(profiles):
            if profiles[name].get("model_provider") in fmapi_ids:
                del profiles[name]
                removed_profile_names.append(name)
        if not profiles:
            data.pop("profiles", None)

        # Remove top-level profile key if it pointed to a removed profile
        if data.get("profile") in removed_profile_names:
            del data["profile"]

        # If nothing remains, delete the file
        if not data:
            self.path.unlink(missing_ok=True)
            return True

        self.write(data)
        return False

    def get_provider_auth_command(self) -> str:
        """Get the FMAPI auth command path (name-agnostic scan)."""
        data = self.read()
        providers = data.get("model_providers", {})
        for provider in providers.values():
            command = provider.get("auth", {}).get("command", "")
            if command and "fmapi-key-helper" in command:
                return command
        return ""
