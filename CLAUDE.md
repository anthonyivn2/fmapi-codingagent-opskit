# CLAUDE.md

## Project Overview

This repo contains setup scripts and a Claude Code plugin that configure coding agents to use foundation models served through Databricks Foundation Model API (FMAPI). Currently only Claude Code is supported, with OpenAI Codex and Gemini CLI planned. The repo includes a setup script, plugin manifest, and skill definitions — no application code.

## Repository Structure

```
setup-fmapi-claudecode.sh                          # Thin entry point: source libs, parse CLI, dispatch
install.sh                                         # Bootstrap installer for bash <(curl ...) one-liner
VERSION                                            # Version file (single line, e.g., 1.0.0)
agents/
  claudecode.sh                                    # Claude Code agent adapter (AGENT_* vars + agent_* functions)
lib/
  core.sh                                          # Preamble, colors, logging, utilities, _install_hint
  help.sh                                          # show_help (help text, uses AGENT_* variables)
  config.sh                                        # Config discovery and file/URL loading
  shared.sh                                        # OAuth, endpoints, validation, shared helpers
  commands.sh                                      # All do_* command functions
  setup.sh                                         # Setup workflow (gather, install, auth, write, smoke test)
templates/
  fmapi-key-helper.sh.template                     # POSIX helper script template with __PROFILE__, __HOST__, __SETUP_SCRIPT__ placeholders
example-config.json                                # Example config file for --config / --config-url
.claude-plugin/plugin.json                         # Claude Code plugin manifest
skills/fmapi-codingagent-status/SKILL.md           # /fmapi-codingagent-status skill
skills/fmapi-codingagent-reauth/SKILL.md           # /fmapi-codingagent-reauth skill
skills/fmapi-codingagent-setup/SKILL.md            # /fmapi-codingagent-setup skill
skills/fmapi-codingagent-doctor/SKILL.md           # /fmapi-codingagent-doctor skill
skills/fmapi-codingagent-list-models/SKILL.md      # /fmapi-codingagent-list-models skill
skills/fmapi-codingagent-validate-models/SKILL.md  # /fmapi-codingagent-validate-models skill
README.md                                          # User-facing documentation
CLAUDE.md                                          # This file
.gitignore                                         # Ignores generated files and Python artifacts
```

## Supported Coding Agents

| Agent | Script | Status |
|---|---|---|
| Claude Code | `setup-fmapi-claudecode.sh` | Implemented |
| OpenAI Codex | — | Planned |
| Gemini CLI | — | Planned |

## Plugin Skills

The repo is a Claude Code plugin providing six slash-command skills:

| Skill | Description |
|---|---|
| `/fmapi-codingagent-status` | Show FMAPI configuration health dashboard (OAuth health, model config) |
| `/fmapi-codingagent-reauth` | Re-authenticate Databricks OAuth session |
| `/fmapi-codingagent-setup` | Run full FMAPI setup (interactive or non-interactive with CLI flags) |
| `/fmapi-codingagent-doctor` | Run comprehensive diagnostics (deps, config, profile, auth, connectivity, models) |
| `/fmapi-codingagent-list-models` | List all serving endpoints in the workspace |
| `/fmapi-codingagent-validate-models` | Validate configured models exist and are ready |

The plugin is automatically registered in `~/.claude/plugins/installed_plugins.json` when the setup script runs. It is deregistered on `--uninstall`.

## Key Concepts

- **`setup-fmapi-claudecode.sh`** — Thin entry point (~120 lines) that sources the agent adapter (`agents/claudecode.sh`) and `lib/*.sh` modules, parses CLI flags, and dispatches to the appropriate command or setup flow. Supports `--status`, `--reauth`, `--doctor`, `--list-models`, `--validate-models`, `--self-update`, `--uninstall`, `--config`, `--config-url`, and CLI flags for non-interactive setup. Passing `--host`, `--config`, or `--config-url` enables non-interactive mode where all other flags auto-default (profile defaults to `fmapi-claudecode-profile`).
- **`install.sh`** — Bootstrap installer for `bash <(curl ...)` one-liner. Clones the repo to `~/.fmapi-codingagent-setup/` (or `$FMAPI_HOME`). Idempotent: re-running updates an existing clone. Supports `--branch` for installing a specific branch or tag. Does not auto-run setup — prints next-step instructions only.
- **`VERSION`** — Single-line file containing the current version (e.g., `1.0.0`). Read by `lib/core.sh` into the `FMAPI_VERSION` global. Falls back to `dev` if missing.
- **`example-config.json`** — Example JSON config file showing all supported keys. Used with `--config` or hosted remotely for `--config-url` to enable reproducible, shareable team setups. Priority chain: CLI flags > config file > existing settings > hardcoded defaults.
- **`.claude-plugin/plugin.json`** — Plugin manifest that registers the repo as a Claude Code plugin with the `skills/` directory.
- **`skills/*/SKILL.md`** — Skill definitions that instruct Claude how to invoke the setup script with the appropriate flags.
- **`fmapi-key-helper.sh`** — A POSIX `/bin/sh` script generated alongside `settings.json` that Claude Code invokes automatically via the `apiKeyHelper` setting to obtain OAuth access tokens on demand. The Databricks CLI handles token refresh transparently.
- **`.claude/settings.json`** — Claude Code configuration file containing `apiKeyHelper` (path to helper script) and environment variables that route requests through Databricks FMAPI.

## Module Architecture

The setup script is split into an agent adapter and six sourced library modules. The entry point sources them in order: `core.sh` → `agents/<agent>.sh` → `help.sh` → `config.sh` → `shared.sh` → `commands.sh` → `setup.sh`. Each module depends only on modules sourced before it.

| Module | Contents |
|---|---|
| `lib/core.sh` | Cleanup trap, ANSI colors, `_OS_TYPE`/`_IS_WSL`/`_WSL_VERSION`/`VERBOSITY`/`DRY_RUN`/`FMAPI_VERSION` globals, logging (`info`, `success`, `error`, `debug`), utilities (`array_contains`, `require_cmd`, `_install_hint`, `prompt_value`, `select_option`) |
| `agents/claudecode.sh` | Agent adapter: `AGENT_*` variables (identity, defaults, env var names) and `agent_*` functions (write env, read env, install CLI, onboarding, plugin registration, doctor checks, dry-run sections) |
| `lib/help.sh` | `show_help()` — help text using `$AGENT_*` variables for agent-specific values |
| `lib/config.sh` | `discover_config()`, `_CONFIG_VALID_KEYS`, `load_config_file()`, `load_config_url()` |
| `lib/shared.sh` | `_get_oauth_token()`, `_detect_workspace_id()`, `_build_base_url()`, `_fetch_endpoints()`, `_validate_models_report()`, `_display_agent_endpoints()`, plus shared helpers: `_is_headless()`, `_require_fmapi_config()`, `_require_valid_oauth()` |
| `lib/commands.sh` | `do_status()`, `do_reauth()`, `do_uninstall()`, `do_list_models()`, `do_validate_models()`, `do_self_update()`, `do_doctor()` (with `_doctor_*` sub-functions) |
| `lib/setup.sh` | `gather_config_pre_auth()`, `gather_config_models()`, `install_dependencies()`, `authenticate()`, `resolve_workspace_id()`, `write_settings()`, `write_helper()`, `run_smoke_test()`, `print_summary()`, `print_dry_run_plan()`, `do_setup()` |

Key shared helpers that deduplicate repeated patterns:
- **`_install_hint(cmd)`** — Platform-appropriate install hint for any dependency (jq, databricks, agent CLI, curl). Uses `AGENT_CLI_CMD` and `AGENT_CLI_INSTALL_CMD` for the agent's CLI.
- **`_is_headless()`** — Detects headless SSH sessions (replaces 3 inline checks)
- **`_require_fmapi_config(caller)`** — Common preamble: require jq + databricks, discover config, validate profile
- **`_require_valid_oauth()`** — Check OAuth token validity with standard error message

The global `SCRIPT_DIR` is computed once in the entry point and used by `write_helper()`, `agent_register_plugin()`, and `print_dry_run_plan()` instead of `BASH_SOURCE[0]` (which would point to the sourced lib file, not the entry script).

## Agent Adapter Contract

Each agent gets its own adapter file under `agents/` that defines the full set of `AGENT_*` variables and `agent_*` functions. The shared `lib/` modules are completely agent-agnostic — they reference only `AGENT_*` / `agent_*` symbols, never hardcode agent-specific values.

### Required Variables

| Variable | Example (Claude Code) | Description |
|---|---|---|
| `AGENT_NAME` | `"Claude Code"` | Display name |
| `AGENT_ID` | `"claudecode"` | Short ID (used in script names, paths) |
| `AGENT_CLI_CMD` | `"claude"` | CLI command to check/run |
| `AGENT_CLI_INSTALL_CMD` | `"curl -fsSL ... \| bash"` | Shell command to install the CLI |
| `AGENT_SETTINGS_DIR` | `".claude"` | Settings directory name |
| `AGENT_SETTINGS_FILENAME` | `"settings.json"` | Settings filename |
| `AGENT_HELPER_FILENAME` | `"fmapi-key-helper.sh"` | Helper script filename |
| `AGENT_DEFAULT_PROFILE` | `"fmapi-claudecode-profile"` | Default Databricks CLI profile name |
| `AGENT_DEFAULT_MODEL` | `"databricks-claude-opus-4-6"` | Default primary model |
| `AGENT_DEFAULT_OPUS` | `"databricks-claude-opus-4-6"` | Default opus model |
| `AGENT_DEFAULT_SONNET` | `"databricks-claude-sonnet-4-6"` | Default sonnet model |
| `AGENT_DEFAULT_HAIKU` | `"databricks-claude-haiku-4-5"` | Default haiku model |
| `AGENT_ENDPOINT_FILTER` | `"claude\|anthropic"` | Regex for endpoint table filtering |
| `AGENT_ENDPOINT_TITLE` | `"Anthropic Claude"` | Display title for endpoint listings |
| `AGENT_BASE_URL_SUFFIX` | `"/serving-endpoints/anthropic"` | URL suffix appended to workspace host |
| `AGENT_ENV_MODEL` | `"ANTHROPIC_MODEL"` | Env var name for primary model |
| `AGENT_ENV_BASE_URL` | `"ANTHROPIC_BASE_URL"` | Env var name for base URL |
| `AGENT_ENV_OPUS` | `"ANTHROPIC_DEFAULT_OPUS_MODEL"` | Env var name for opus model |
| `AGENT_ENV_SONNET` | `"ANTHROPIC_DEFAULT_SONNET_MODEL"` | Env var name for sonnet model |
| `AGENT_ENV_HAIKU` | `"ANTHROPIC_DEFAULT_HAIKU_MODEL"` | Env var name for haiku model |
| `AGENT_ENV_TTL` | `"CLAUDE_CODE_API_KEY_HELPER_TTL_MS"` | Env var name for TTL |
| `AGENT_REQUIRED_ENV_KEYS` | Array of 5 keys | Env keys checked by doctor |
| `AGENT_LEGACY_CLEANUP_KEYS` | `("ANTHROPIC_AUTH_TOKEN")` | Legacy env keys to remove on write |

### Required Functions

| Function | Description |
|---|---|
| `agent_settings_candidates()` | Set `_SETTINGS_CANDIDATES` array with settings file search paths |
| `agent_read_env(settings_file)` | Read model/TTL from settings into `CFG_*` variables |
| `agent_write_env_json(model, base_url, opus, sonnet, haiku, ttl_ms)` | Return the env JSON block for settings |
| `agent_uninstall_env_keys_json()` | Return JSON array of env keys to clean on uninstall |
| `agent_ensure_onboarding()` | Set agent-specific onboarding flags |
| `agent_register_plugin(script_dir)` | Register agent plugin |
| `agent_deregister_plugin()` | Remove agent plugin registration |
| `agent_install_cli()` | Install agent CLI if missing |
| `agent_doctor_extra()` | Agent-specific doctor checks (returns 0/1) |
| `agent_dry_run_env_display(model, base_url, opus, sonnet, haiku, ttl_ms)` | Print env vars for dry-run |
| `agent_dry_run_extra()` | Print agent-specific dry-run sections |

### Internal Variable Convention

Shared `lib/` modules use `FMAPI_*` for internal bash variables (e.g., `FMAPI_MODEL`, `FMAPI_OPUS_MODEL`). The agent adapter's `agent_write_env_json()` maps these to the actual env var names written to settings (e.g., `ANTHROPIC_MODEL`).

### Adding a New Agent

1. Create `agents/<agentid>.sh` implementing all variables and functions above.
2. Create `setup-fmapi-<agentid>.sh` entry point that sources `agents/<agentid>.sh` after `lib/core.sh`.
3. Add agent-specific artifacts (plugin manifests, skills) if applicable.
4. The shared `lib/` modules work unchanged.

## CLI Flags

| Flag | Description |
|---|---|
| `--status` | Show configuration health dashboard |
| `--reauth` | Re-authenticate Databricks OAuth session |
| `--doctor` | Run comprehensive diagnostics (deps, config, profile, auth, connectivity, models) |
| `--list-models` | List all serving endpoints in the workspace |
| `--validate-models` | Validate configured models exist and are ready |
| `--reinstall` | Rerun setup using previously saved configuration |
| `--self-update` | Update to the latest version (requires git clone installation) |
| `--uninstall` | Remove all FMAPI artifacts and plugin registration |
| `-h`, `--help` | Show help |
| `--host URL` | Databricks workspace URL (enables non-interactive mode) |
| `--profile NAME` | Databricks CLI profile name (default: `fmapi-claudecode-profile`) |
| `--model MODEL` | Primary model (default: `databricks-claude-opus-4-6`) |
| `--opus MODEL` | Opus model (default: `databricks-claude-opus-4-6`) |
| `--sonnet MODEL` | Sonnet model (default: `databricks-claude-sonnet-4-6`) |
| `--haiku MODEL` | Haiku model (default: `databricks-claude-haiku-4-5`) |
| `--ttl MINUTES` | Token refresh interval in minutes (default: `60`, max: `60`, 60 recommended) |
| `--settings-location PATH` | Settings location: `home`, `cwd`, or custom path (default: `home`) |
| `--ai-gateway` | Use AI Gateway v2 for API routing (beta, default: off) |
| `--workspace-id ID` | Databricks workspace ID for AI Gateway (auto-detected if omitted) |
| `--config PATH` | Load configuration from a local JSON file |
| `--config-url URL` | Load configuration from a remote JSON URL (HTTPS only) |
| `--verbose` | Show debug-level output |
| `--quiet`, `-q` | Suppress informational output (errors always shown) |
| `--no-color` | Disable colored output (also respects `NO_COLOR` env var) |
| `--dry-run` | Show what would happen without making changes |

## Development Guidelines

- This is a **bash-only** project. No Python, no package manager, no build step.
- Each coding agent should have its own setup script following the naming convention `setup-fmapi-<agent>.sh`.
- Scripts must remain **idempotent** — re-running updates existing config rather than duplicating entries.
- The helper script (`fmapi-key-helper.sh`) must be POSIX `/bin/sh` compatible with `set -eu`. Do not use bash-specific features in the helper.
- Scripts use `set -euo pipefail` for strict error handling. Any new code must work under these constraints.
- All generated files must have owner-only permissions. Never store tokens in world-readable files.
- **Dependencies**: `jq`, `curl`, `tput`, `databricks` CLI. On macOS, `brew` is used for installation; on Linux, `apt-get`/`yum` and curl installers are used. Do not introduce additional dependencies without good reason.
- **Never commit** `.claude/settings.json`, `fmapi-key-helper.sh`, or other files containing tokens.
- Use [ShellCheck](https://www.shellcheck.net/) conventions when editing scripts.
- **Module boundaries**: Add new functions to the appropriate `lib/` module based on the architecture table above. Do not add functions to the entry point — it should remain a thin dispatcher.
- **`set -e` and functions**: Never end a function with `[[ ... ]] && { ...; exit 1; }` — use `if`/`then`/`fi` instead. The `&&` pattern returns 1 when the condition is false, which triggers `set -e` at the call site.
- **`BASH_SOURCE[0]`**: In sourced lib files, `BASH_SOURCE[0]` points to the lib file, not the entry script. Use the global `SCRIPT_DIR` variable instead for paths relative to the repository root.

## Testing Changes

There are no automated tests. To verify changes:

1. Run `bash setup-fmapi-claudecode.sh --help` and verify all flags documented.
2. Run `bash setup-fmapi-claudecode.sh --status` — should show "no config found" or current dashboard.
3. Run `bash setup-fmapi-claudecode.sh` end-to-end with a real Databricks workspace.
4. Confirm `.claude/settings.json` is written correctly with `apiKeyHelper` and env vars.
5. Verify the helper script exists with owner-only permissions.
6. Run `bash setup-fmapi-claudecode.sh --status` — confirm dashboard shows correct config.
7. Run `bash setup-fmapi-claudecode.sh --reauth` — confirm OAuth re-authentication works.
8. Re-run the setup script to confirm idempotency (defaults pre-populated).
9. Confirm `~/.claude/plugins/installed_plugins.json` has `fmapi-codingagent` entry.
10. Run `claude` and confirm it works with FMAPI.
11. Run `bash setup-fmapi-claudecode.sh --doctor` — confirm all 6 diagnostic categories display.
12. Run `bash setup-fmapi-claudecode.sh --list-models` — confirm endpoint table with highlighting.
13. Run `bash setup-fmapi-claudecode.sh --validate-models` — confirm per-model validation output.
14. Run `--doctor`, `--list-models`, `--validate-models` with no prior config — should error gracefully.
15. Run `bash setup-fmapi-claudecode.sh --uninstall` and confirm cleanup (including plugin deregistration).
16. Run `bash setup-fmapi-claudecode.sh --config example-config.json` — confirm non-interactive setup from config file.
17. Run `bash setup-fmapi-claudecode.sh --config nonexistent.json` — confirm "file not found" error.
18. Create an invalid JSON file and run `--config` against it — confirm "not valid JSON" error.
19. Create a config with an unknown key and run `--config` — confirm rejected with key listed.
20. Run `bash setup-fmapi-claudecode.sh --config example-config.json --model override-model` — confirm CLI overrides config.
21. Run `bash setup-fmapi-claudecode.sh --config x --config-url y` — confirm mutual exclusion error.
22. Run `bash setup-fmapi-claudecode.sh --status | cat` — verify no ANSI escape codes in output.
23. Run `NO_COLOR=1 bash setup-fmapi-claudecode.sh --status` — verify no colors.
24. Run `bash setup-fmapi-claudecode.sh --no-color --status` — verify no colors.
25. Run `bash setup-fmapi-claudecode.sh --quiet --status` — verify minimal output (errors only).
26. Run `bash setup-fmapi-claudecode.sh --verbose --status` — verify debug lines appear.
27. Run `bash setup-fmapi-claudecode.sh --dry-run --host https://example.com` — verify plan printed, no files changed.
28. Run `bash setup-fmapi-claudecode.sh --dry-run --status` — verify error about incompatible flags.
29. Run `SSH_CONNECTION=x bash setup-fmapi-claudecode.sh --doctor` — verify headless info line in Auth section.
30. Run `bash setup-fmapi-claudecode.sh --dry-run` (no --host) — verify error about missing host (non-interactive mode).
31. Run `bash setup-fmapi-claudecode.sh --self-update` — verify it fetches, checks, and reports up-to-date or pulls.
32. Run `bash setup-fmapi-claudecode.sh --dry-run --self-update` — verify error about incompatible flags.
33. Run `bash setup-fmapi-claudecode.sh --status` — verify version number appears in output.
34. Run `bash setup-fmapi-claudecode.sh --doctor` — verify version appears in Dependencies section.
35. Run `bash install.sh` locally — verify it clones to `~/.fmapi-codingagent-setup/` and prints next steps.
36. Re-run `bash install.sh` — verify it updates the existing clone (idempotent).
37. Run `bash install.sh --branch v1.0.0` — verify it installs a specific tag.
38. Run `FMAPI_HOME=/tmp/test bash install.sh` — verify it installs to custom location.
39. Run `bash ~/.fmapi-codingagent-setup/setup-fmapi-claudecode.sh --self-update` — verify it works from installed location.
40. Run `bash setup-fmapi-claudecode.sh --dry-run --host https://... --ai-gateway` — verify gateway routing with `<to be detected>` workspace ID.
41. Run `bash setup-fmapi-claudecode.sh --dry-run --host https://... --ai-gateway --workspace-id 123456` — verify gateway routing with explicit ID.
42. Run `bash setup-fmapi-claudecode.sh --workspace-id 123` (no --ai-gateway) — should error.
43. Run `bash setup-fmapi-claudecode.sh --workspace-id abc --ai-gateway` — should error (non-numeric).
44. Run `bash setup-fmapi-claudecode.sh --status` on a gateway config — verify routing mode, workspace ID, and base URL appear.
45. Run `bash setup-fmapi-claudecode.sh --doctor` on a gateway config — verify gateway connectivity check.
46. Run `bash setup-fmapi-claudecode.sh --reinstall` on a gateway config — should preserve gateway settings.
47. Run `bash setup-fmapi-claudecode.sh --config example-config.json` — verify `ai_gateway` and `workspace_id` keys accepted.
48. Run on WSL — verify `_IS_WSL` is `true` and `_WSL_VERSION` is detected correctly.
49. Run `--doctor` on WSL — verify Environment section shows WSL version, distro, and "(experimental)".
50. On WSL without `wslu` or `xdg-open`, run setup — verify browser opener warning appears.

## Abbreviations

FMAPI: Foundation Model API
