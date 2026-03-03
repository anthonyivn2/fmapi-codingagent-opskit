# CLAUDE.md

## Project Overview

This repo contains a Python CLI tool and Claude Code plugin that configure coding agents to use foundation models served through Databricks Foundation Model API (FMAPI). Currently only Claude Code is supported, with OpenAI Codex and Gemini CLI planned. The CLI is distributed via `uv tool install` and provides setup, diagnostics, and management commands.

## Repository Structure

```
pyproject.toml                                     # Python project config (hatchling, typer, rich)
VERSION                                            # Version file (single line, e.g., 1.0.0)
install.sh                                         # Bootstrap installer for bash <(curl ...) one-liner
src/fmapi_opskit/
  __init__.py                                      # Package init
  cli.py                                           # Typer app: callback (global + setup flags) + 8 subcommands
  agents/
    base.py                                        # AgentConfig dataclass + AgentAdapter Protocol
    claudecode.py                                  # ClaudeCodeAdapter implementation
  core/
    version.py                                     # Read VERSION file
    platform.py                                    # OS/WSL/headless detection
    deps.py                                        # require_cmd, install_hint (platform-specific)
  config/
    models.py                                      # FmapiConfig dataclass, VALID_CONFIG_KEYS
    discovery.py                                   # discover_config: search settings, parse helper, read env
    loader.py                                      # load_config_file, load_config_url with validation
  settings/
    manager.py                                     # SettingsManager: read/write/merge settings.json
    hooks.py                                       # Hook merge/cleanup/uninstall logic
  auth/
    databricks.py                                  # Typed subprocess wrappers for databricks CLI
    oauth.py                                       # get_oauth_token, auth_login, check_oauth_status
  network/
    endpoints.py                                   # Fetch/filter serving endpoints via databricks CLI
    connectivity.py                                # HTTP reachability checks (urllib)
    gateway.py                                     # build_base_url, detect_workspace_id, detect_gateway_from_url
  commands/
    _common.py                                     # Shared command preamble helpers
    status.py                                      # Status dashboard
    reauth.py                                      # OAuth re-authentication
    doctor.py                                      # 8 diagnostic sub-checks
    list_models.py                                 # Endpoint table
    validate_models.py                             # Per-model validation
    uninstall.py                                   # Artifact cleanup
    self_update.py                                 # git pull + uv tool reinstall
  setup/
    gather.py                                      # gather_config_pre_auth, gather_config_models
    install_deps.py                                # Platform-specific dependency installation
    authenticate.py                                # OAuth flow, legacy PAT cleanup
    writer.py                                      # write_settings, write_helper, write_hooks
    smoke_test.py                                  # Post-setup verification
    summary.py                                     # print_summary, print_dry_run_plan
    workflow.py                                    # do_setup orchestrator
  ui/
    console.py                                     # Rich Console factory with theme, NO_COLOR/pipe handling
    logging.py                                     # info, success, warn, error, debug (Rich-based)
    prompts.py                                     # prompt_value, select_option (Rich Prompt)
    dashboard.py                                   # Status dashboard panels
    tables.py                                      # Endpoint tables, doctor diagnostic tables
    dry_run.py                                     # Dry-run plan display
  templates/
    renderer.py                                    # str.replace for __PLACEHOLDER__ tokens, atomic write + chmod
templates/
  fmapi-key-helper.sh.template                     # POSIX helper script template
  fmapi-auth-precheck.sh.template                  # POSIX auth pre-check hook template
example-config.json                                # Example config file for --config / --config-url
.claude-plugin/plugin.json                         # Claude Code plugin manifest
skills/fmapi-codingagent-status/SKILL.md           # /fmapi-codingagent-status skill
skills/fmapi-codingagent-reauth/SKILL.md           # /fmapi-codingagent-reauth skill
skills/fmapi-codingagent-setup/SKILL.md            # /fmapi-codingagent-setup skill
skills/fmapi-codingagent-doctor/SKILL.md           # /fmapi-codingagent-doctor skill
skills/fmapi-codingagent-list-models/SKILL.md      # /fmapi-codingagent-list-models skill
skills/fmapi-codingagent-validate-models/SKILL.md  # /fmapi-codingagent-validate-models skill
tests/
  conftest.py                                      # Fixtures: adapter, sample_settings, sample_config
  test_cli_flags.py                                # Typer CliRunner: help, mutual exclusion, validation
  test_config_validation.py                        # Config file loading: JSON, unknown keys, validation
  test_settings_manager.py                         # settings.json read/write/merge, legacy cleanup
  test_hooks_logic.py                              # Hook merge/uninstall (29+ cases)
  test_agent_adapter.py                            # Protocol compliance, env block, plugin paths
  test_platform.py                                 # OS/WSL/headless detection
  test_template_renderer.py                        # Placeholder substitution, permission checks
README.md                                          # User-facing documentation
CLAUDE.md                                          # This file
.gitignore                                         # Ignores generated files and Python artifacts
```

## Supported Coding Agents

| Agent | Adapter | Status |
|---|---|---|
| Claude Code | `agents/claudecode.py` | Implemented |
| OpenAI Codex | — | Planned |
| Gemini CLI | — | Planned |

## Plugin Skills

The repo is a Claude Code plugin providing six slash-command skills:

| Skill | Description |
|---|---|
| `/fmapi-codingagent-status` | Show FMAPI configuration health dashboard (OAuth health, model config) |
| `/fmapi-codingagent-reauth` | Re-authenticate Databricks OAuth session |
| `/fmapi-codingagent-setup` | Run full FMAPI setup (interactive or non-interactive with CLI flags) |
| `/fmapi-codingagent-doctor` | Run comprehensive diagnostics (deps, config, profile, auth, connectivity, models, hooks) |
| `/fmapi-codingagent-list-models` | List all serving endpoints in the workspace |
| `/fmapi-codingagent-validate-models` | Validate configured models exist and are ready |

The plugin is automatically registered in `~/.claude/plugins/installed_plugins.json` when setup runs. It is deregistered on `uninstall`.

## Key Concepts

- **`setup-fmapi-claudecode`** — Global CLI command installed via `uv tool install`. Provides subcommands (`status`, `reauth`, `doctor`, `list-models`, `validate-models`, `self-update`, `uninstall`, `reinstall`) and runs setup when invoked with no subcommand. Passing `--host`, `--config`, or `--config-url` enables non-interactive mode.
- **`install.sh`** — Bootstrap installer for `bash <(curl ...)` one-liner. Clones the repo, installs `uv` if needed, and runs `uv tool install` to make the CLI globally available. Idempotent: re-running updates an existing clone. Supports `--branch` and `--agent` flags.
- **`VERSION`** — Single-line file containing the current version (e.g., `1.0.0`). Read by `core/version.py`. Falls back to `dev` if missing.
- **`example-config.json`** — Example JSON config file showing all supported keys. Priority chain: CLI flags > config file > existing settings > hardcoded defaults.
- **`.claude-plugin/plugin.json`** — Plugin manifest that registers the repo as a Claude Code plugin with the `skills/` directory.
- **`fmapi-key-helper.sh`** — A POSIX `/bin/sh` script generated alongside `settings.json` that Claude Code invokes via `apiKeyHelper` to obtain OAuth access tokens on demand.
- **`fmapi-auth-precheck.sh`** — A POSIX `/bin/sh` script registered as both `SubagentStart` and `UserPromptSubmit` hooks. Verifies OAuth token validity before each operation. Always exits 0 (non-blocking).

## CLI Commands

```
setup-fmapi-claudecode [GLOBAL FLAGS] [SETUP FLAGS]     # runs setup (default)
setup-fmapi-claudecode status                            # health dashboard
setup-fmapi-claudecode doctor                            # diagnostics
setup-fmapi-claudecode reauth                            # OAuth refresh
setup-fmapi-claudecode list-models                       # endpoint table
setup-fmapi-claudecode validate-models                   # model validation
setup-fmapi-claudecode uninstall                         # cleanup
setup-fmapi-claudecode self-update                       # git pull + reinstall
setup-fmapi-claudecode reinstall                         # rerun with saved config
```

### Global Flags

`--verbose`, `--quiet`, `--no-color`, `--dry-run`

### Setup Flags (used when no subcommand)

`--host`, `--profile`, `--model`, `--opus`, `--sonnet`, `--haiku`, `--ttl`, `--settings-location`, `--ai-gateway`, `--workspace-id`, `--config`, `--config-url`

### Validation Rules

- `--verbose` + `--quiet` — mutually exclusive
- `--dry-run` + subcommand — error (dry-run only for setup)
- `--config` + `--config-url` — mutually exclusive
- `--workspace-id` without `--ai-gateway` — error
- `--workspace-id` non-numeric — error

## Package Architecture

### Agent Adapter Pattern

- `AgentConfig` — frozen dataclass with all 25+ configuration fields (identity, defaults, env var names)
- `AgentAdapter` — Protocol with 11 methods (write_env, read_env, settings_candidates, install_cli, etc.)
- `ClaudeCodeAdapter` — concrete implementation for Claude Code

### Settings Manager

- `SettingsManager(path: Path)` — read/write/merge settings.json via stdlib `json`
- `merge_env(new_env, api_key_helper, legacy_cleanup_keys)` — atomic env block update
- `remove_fmapi_keys(uninstall_keys)` — clean uninstall, returns bool for file deletion
- Atomic writes: write to `.tmp` then `Path.rename()`, `chmod 0o600`

### Hook Logic (`settings/hooks.py`)

- `is_fmapi_hook_entry(entry)` — regex match on `fmapi-auth-precheck|fmapi-subagent-precheck`
- `merge_fmapi_hooks(settings, hook_command)` — filter old entries, append new for both hook types
- `remove_fmapi_hooks(settings)` — remove FMAPI entries, preserve user hooks, clean empty sections

### Template Rendering

- `render_template(template_path, output_path, placeholders, mode)` — `str.replace()` for `__PLACEHOLDER__` tokens
- Placeholder keys are passed WITHOUT the `__` prefix (e.g., `{"PROFILE": "value"}`)
- Verifies no unsubstituted `__...__` placeholders remain
- Atomic write with correct permissions (0o700 for scripts)

### UI Layer (Rich)

- Themed Console with `no_color`, `quiet`, pipe detection
- `info()`, `success()`, `warn()`, `error()`, `debug()` helpers using Rich markup
- `Rich.Prompt.ask()` for interactive input
- `Rich.Table` for endpoint listings and diagnostics
- `Rich.Panel` for status dashboard

## Development Guidelines

- This is a **Python** project using **Typer** + **Rich**. Use `uv` for dependency management.
- The helper script (`fmapi-key-helper.sh`) and auth pre-check script must remain POSIX `/bin/sh` compatible. Do not use bash-specific features in templates.
- All generated files must have owner-only permissions (`0o600` for settings, `0o700` for scripts).
- **Never commit** `.claude/settings.json`, `fmapi-key-helper.sh`, or other files containing tokens.
- Use type hints for all function parameters and return values.
- Follow Ruff lint rules: `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `SIM` with line-length 100.
- **Dependencies**: `typer`, `rich` (Python). Runtime: `databricks` CLI, `jq` (for generated helper scripts). No additional Python dependencies without good reason.
- **Module boundaries**: Add new functions to the appropriate subpackage. Keep `cli.py` as a thin dispatcher.

## Development Workflow

```bash
# Install dev dependencies
uv sync --group dev

# Run the CLI
uv run setup-fmapi-claudecode --help

# Run tests
uv run pytest

# Lint and format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Install globally for testing
uv tool install . --force
setup-fmapi-claudecode --help
```

## Testing

The test suite covers core modules with 84 tests:

| Test File | Coverage |
|---|---|
| `test_cli_flags.py` | CLI help, version, mutual exclusion, validation |
| `test_config_validation.py` | Config file loading, JSON parsing, key validation |
| `test_settings_manager.py` | Settings read/write/merge, permissions, legacy cleanup |
| `test_hooks_logic.py` | Hook merge/uninstall (29+ cases, ported from bash tests) |
| `test_agent_adapter.py` | AgentConfig fields, ClaudeCodeAdapter methods |
| `test_platform.py` | OS/WSL/headless detection |
| `test_template_renderer.py` | Placeholder substitution, permissions, error handling |

Run with: `uv run pytest` or `uv run pytest -v` for verbose output.

## Abbreviations

FMAPI: Foundation Model API
