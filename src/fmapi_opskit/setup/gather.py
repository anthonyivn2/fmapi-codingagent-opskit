"""Gather configuration — pre-auth and model selection."""

from __future__ import annotations

import sys
from pathlib import Path

from fmapi_opskit.agents.base import AgentAdapter
from fmapi_opskit.config.models import FileConfig, FmapiConfig
from fmapi_opskit.ui import logging as log
from fmapi_opskit.ui.console import get_console
from fmapi_opskit.ui.prompts import prompt_prefilled_value, prompt_value, select_option


def _first_non_empty(*values: str) -> str:
    """Return the first non-empty string from the arguments."""
    for v in values:
        if v:
            return v
    return ""


def _validate_settings_path(p: str) -> None:
    """Reject dangerous base paths for settings file placement."""
    dangerous = {"/", "/bin", "/sbin", "/usr", "/etc", "/var", "/tmp", "/dev", "/proc", "/sys"}
    if p in dangerous or any(p.startswith(d + "/") for d in ("/usr", "/etc")):
        log.error(f"Refusing to use system path as settings location: {p}")
        sys.exit(1)


class GatherResult:
    """Results from gather_config_pre_auth."""

    def __init__(self) -> None:
        self.host: str = ""
        self.profile: str = ""
        self.ttl_minutes: str = ""
        self.ttl_ms: str = ""
        self.ai_gateway_enabled: bool = False
        self.pending_workspace_id: str = ""
        self.settings_file: str = ""
        self.helper_file: str = ""
        # Model defaults (for gather_config_models)
        self.default_model: str = ""
        self.default_opus: str = ""
        self.default_sonnet: str = ""
        self.default_haiku: str = ""


def gather_config_pre_auth(
    adapter: AgentAdapter,
    cfg: FmapiConfig,
    file_cfg: FileConfig,
    *,
    cli_host: str,
    cli_profile: str,
    cli_ttl: str,
    cli_ai_gateway: str,
    cli_workspace_id: str,
    cli_settings_location: str,
    cli_model: str,
    cli_opus: str,
    cli_sonnet: str,
    cli_haiku: str,
    non_interactive: bool,
) -> GatherResult:
    """Gather pre-auth configuration (host, profile, TTL, routing, settings location)."""
    c = adapter.config
    result = GatherResult()

    # Resolve defaults: CLI > config file > discovered > hardcoded
    default_host = _first_non_empty(cli_host, file_cfg.host, cfg.host)
    default_profile = _first_non_empty(
        cli_profile, file_cfg.profile, cfg.profile, c.default_profile
    )
    default_ttl = _first_non_empty(cli_ttl, file_cfg.ttl, cfg.ttl, "55")

    # Store model defaults for gather_config_models
    result.default_model = _first_non_empty(cli_model, file_cfg.model, cfg.model, c.default_model)
    result.default_opus = _first_non_empty(cli_opus, file_cfg.opus, cfg.opus, c.default_opus)
    result.default_sonnet = _first_non_empty(
        cli_sonnet, file_cfg.sonnet, cfg.sonnet, c.default_sonnet
    )
    result.default_haiku = _first_non_empty(cli_haiku, file_cfg.haiku, cfg.haiku, c.default_haiku)

    # Workspace URL
    result.host = prompt_value("Databricks workspace URL", cli_host, default_host, non_interactive)
    if not result.host:
        log.error("Workspace URL is required.")
        sys.exit(1)
    result.host = result.host.rstrip("/")
    if not result.host.startswith("https://"):
        log.error("Workspace URL must start with https://")
        sys.exit(1)

    # API routing mode
    default_gw = _first_non_empty(cli_ai_gateway, file_cfg.ai_gateway, cfg.ai_gateway, "false")
    if non_interactive:
        result.ai_gateway_enabled = default_gw == "true"
    else:
        choice = select_option(
            "API routing mode",
            [
                ("Serving Endpoints", "default"),
                ("AI Gateway v2 (beta)", "requires account preview enablement"),
            ],
            default_index=1 if default_gw == "true" else 0,
        )
        result.ai_gateway_enabled = choice == 1
        if result.ai_gateway_enabled:
            console = get_console()
            console.print(
                "  [warning]NOTE[/warning]  AI Gateway v2 is a [bold]Beta[/bold] feature "
                "([dim]https://docs.databricks.com/aws/en/release-notes/release-types[/dim])."
            )
            console.print(
                "        Account admins must enable it from the account console Previews page."
            )

    # Only carry over discovered workspace_id if the host hasn't changed,
    # otherwise force re-detection for the new workspace.
    cfg_workspace_id = cfg.workspace_id if result.host == cfg.host.rstrip("/") else ""
    result.pending_workspace_id = _first_non_empty(
        cli_workspace_id, file_cfg.workspace_id, cfg_workspace_id
    )

    # CLI profile
    result.profile = prompt_value(
        "Databricks CLI profile name", cli_profile, default_profile, non_interactive
    )
    if not result.profile:
        log.error("Profile name is required.")
        sys.exit(1)
    import re

    if not re.match(r"^[a-zA-Z0-9_-]+$", result.profile):
        log.error(
            f"Invalid profile name: '{result.profile}'. "
            "Use letters, numbers, hyphens, and underscores."
        )
        sys.exit(1)

    # Token refresh interval
    result.ttl_minutes = prompt_value(
        "Token refresh interval in minutes (55 recommended)",
        cli_ttl,
        default_ttl,
        non_interactive,
    )
    if not result.ttl_minutes.isdigit() or int(result.ttl_minutes) <= 0:
        log.error("Token refresh interval must be a positive integer (minutes).")
        sys.exit(1)
    if int(result.ttl_minutes) > 60:
        log.error(
            "Token refresh interval cannot exceed 60 minutes. OAuth tokens expire after 1 hour."
        )
        sys.exit(1)
    if int(result.ttl_minutes) < 15:
        log.warn(
            "Token refresh interval under 15 minutes may cause failures during "
            "long-running subagent calls."
        )
    if int(result.ttl_minutes) == 60:
        log.warn(
            "A 60-minute refresh interval may hit token-expiry edge cases in long sessions. "
            "55 minutes is recommended."
        )
    result.ttl_ms = str(int(result.ttl_minutes) * 60000)

    # Settings location
    resolved_loc = _first_non_empty(cli_settings_location, file_cfg.settings_location)
    if resolved_loc:
        if resolved_loc == "home":
            settings_base = str(Path.home())
        elif resolved_loc == "cwd":
            settings_base = str(Path.cwd())
        else:
            expanded = resolved_loc.replace("~", str(Path.home()), 1)
            _validate_settings_path(expanded)
            Path(expanded).mkdir(parents=True, exist_ok=True)
            settings_base = str(Path(expanded).resolve())
    elif non_interactive:
        settings_base = str(Path.home())
    else:
        choice = select_option(
            "Settings location",
            [
                ("Home directory", f"~/{c.settings_dir}/{c.settings_filename}, default"),
                ("Current directory", f"./{c.settings_dir}/{c.settings_filename}"),
                ("Custom path", "enter your own path"),
            ],
        )
        if choice == 0:
            settings_base = str(Path.home())
        elif choice == 1:
            settings_base = str(Path.cwd())
        else:
            from rich.prompt import Prompt

            from fmapi_opskit.ui.console import get_console as gc

            custom = Prompt.ask("  [info]?[/info] Base path", console=gc())
            if not custom:
                log.error("Custom path is required.")
                sys.exit(1)
            custom = custom.replace("~", str(Path.home()), 1)
            _validate_settings_path(custom)
            Path(custom).mkdir(parents=True, exist_ok=True)
            settings_base = str(Path(custom).resolve())

    result.settings_file = f"{settings_base}/{c.settings_dir}/{c.settings_filename}"
    result.helper_file = f"{settings_base}/{c.settings_dir}/{c.helper_filename}"

    log.debug(f"gather: host={result.host} profile={result.profile}")
    log.debug(f"gather: settings={result.settings_file} helper={result.helper_file}")

    return result


class ModelResult:
    """Results from gather_config_models."""

    def __init__(self) -> None:
        self.model: str = ""
        self.opus: str = ""
        self.sonnet: str = ""
        self.haiku: str = ""


def _normalize_available_models(available_models: list[str] | None) -> list[str]:
    """Normalize available model names to unique non-empty values."""
    if not available_models:
        return []

    seen: set[str] = set()
    normalized: list[str] = []
    for model in available_models:
        name = model.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _prompt_model_value(
    label: str,
    cli_val: str,
    default: str,
    non_interactive: bool,
    available_models: list[str],
) -> str:
    """Prompt for a model value, using menu selection when models are available."""
    if cli_val:
        return cli_val
    if non_interactive:
        return default

    if not available_models:
        return prompt_value(label, "", default, False)

    options = [(name, "") for name in available_models]
    options.append(("Custom model name", "type your own endpoint name"))

    default_index = len(available_models)
    if default in available_models:
        default_index = available_models.index(default)

    choice = select_option(label, options, default_index=default_index)
    if choice == len(available_models):
        custom_label = "Custom model name" if label == "Model" else f"Custom {label.lower()} name"
        custom_value = prompt_prefilled_value(custom_label, default)
        if not custom_value:
            log.error(f"{label} is required.")
            sys.exit(1)
        return custom_value

    return available_models[choice]


def gather_config_models(
    gather: GatherResult,
    *,
    cli_model: str,
    cli_opus: str,
    cli_sonnet: str,
    cli_haiku: str,
    non_interactive: bool,
    available_models: list[str] | None = None,
) -> ModelResult:
    """Gather model configuration (after auth, endpoint listing)."""
    normalized_models = _normalize_available_models(available_models)

    result = ModelResult()
    result.model = _prompt_model_value(
        "Model",
        cli_model,
        gather.default_model,
        non_interactive,
        normalized_models,
    )
    result.opus = _prompt_model_value(
        "Opus model",
        cli_opus,
        gather.default_opus,
        non_interactive,
        normalized_models,
    )
    result.sonnet = _prompt_model_value(
        "Sonnet model",
        cli_sonnet,
        gather.default_sonnet,
        non_interactive,
        normalized_models,
    )
    result.haiku = _prompt_model_value(
        "Haiku model",
        cli_haiku,
        gather.default_haiku,
        non_interactive,
        normalized_models,
    )

    log.debug(
        f"models: model={result.model} opus={result.opus} "
        f"sonnet={result.sonnet} haiku={result.haiku}"
    )
    return result
