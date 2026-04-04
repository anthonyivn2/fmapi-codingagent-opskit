# AGENTS.md

This file gives Codex and other coding agents practical guidance for working in this repository.

## Purpose

This repository provides a Python CLI that configures coding agents to use Databricks Foundation Model API (FMAPI). The main supported entrypoints are:

- `setup-fmapi-claudecode`
- `setup-fmapi-codex`

The codebase handles:

- interactive setup flows
- Databricks OAuth authentication
- agent-specific settings generation
- helper script rendering for token refresh
- diagnostics and uninstall flows

## Repository Layout

- `src/fmapi_opskit/cli.py` — Typer CLI entrypoint; keep this thin
- `src/fmapi_opskit/setup/` — setup orchestration, prompting, writing files, smoke tests
- `src/fmapi_opskit/agents/` — agent-specific adapters for Claude Code and Codex
- `src/fmapi_opskit/settings/` — JSON/TOML settings merge and cleanup logic
- `src/fmapi_opskit/auth.py` — authentication and token/cache handling
- `src/fmapi_opskit/network.py` — endpoint discovery and workspace/network helpers
- `src/fmapi_opskit/templates/` — generated shell script templates
- `src/fmapi_opskit/ui/` — Rich console output, prompts, tables, dashboard helpers
- `tests/` — pytest suite for CLI, adapters, auth, settings, prompts, and templates
- `skills/` and `skills-codex/` — agent skill definitions that get installed/copied for supported agents

## Working Agreements

- Make focused changes that match the existing design; do not refactor broadly unless asked.
- Prefer fixing root causes in shared workflow or adapter code rather than adding one-off patches.
- Keep `cli.py` as a dispatcher; put business logic in the appropriate module.
- Preserve backwards compatibility for both supported agents unless the task explicitly narrows scope.
- Do not commit generated user config or secrets.

## Code Style

- Language: Python 3.10+
- CLI framework: Typer
- Terminal UI: Rich
- Dependency/tooling: `uv`
- Linting: Ruff with `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `SIM`
- Max line length: `100`
- Use type hints for function parameters and return values.
- Follow existing naming and module boundaries before introducing new abstractions.

## Critical Constraints

- Generated shell scripts, especially `fmapi-key-helper.sh`, must remain POSIX `/bin/sh` compatible.
- Do not introduce bash-specific syntax into shell templates.
- Generated settings/config files should preserve owner-only permissions:
  - settings files: `0o600`
  - helper scripts: `0o700`
- Settings writers should preserve unrelated user configuration whenever possible.
- Uninstall/cleanup logic should be name-agnostic where practical and avoid deleting non-FMAPI user config.

## Where To Put Changes

- New CLI flags or commands: start in `src/fmapi_opskit/cli.py`, but move implementation into `src/fmapi_opskit/commands/` or another focused module.
- Agent-specific config behavior: `src/fmapi_opskit/agents/`
- JSON settings merge/remove behavior: `src/fmapi_opskit/settings/manager.py`
- TOML provider/profile merge/remove behavior: `src/fmapi_opskit/settings/toml_manager.py`
- Hook cleanup/merge behavior: `src/fmapi_opskit/settings/hooks.py`
- Setup flow changes: `src/fmapi_opskit/setup/workflow.py`
- Prompting/UI changes: `src/fmapi_opskit/ui/`
- Template changes: `src/fmapi_opskit/templates/`

## Testing Expectations

When changing code, run the narrowest relevant tests first, then broaden if needed.

Common commands:

- `uv sync --group dev`
- `uv run pytest`
- `uv run pytest tests/test_cli_flags.py`
- `uv run pytest tests/test_settings_manager.py`
- `uv run pytest tests/test_toml_manager.py`
- `uv run pytest tests/test_auth.py`
- `uv run pytest tests/test_template_renderer.py`
- `uv run ruff check src tests`
- `uv run ruff format src tests`

Testing guidance:

- If you change CLI parsing or command wiring, run the CLI tests.
- If you change JSON/TOML merge logic, run the relevant settings tests.
- If you change token/auth/helper behavior, run auth and helper-script tests.
- If you change templates, run template and related integration tests.
- Do not fix unrelated failing tests unless the user asks.

## Safe Defaults For Agents

- Before editing, read the relevant module and adjacent tests.
- Prefer updating existing tests or adding small targeted tests near the changed behavior.
- Avoid introducing new dependencies without a clear reason.
- Avoid network-dependent solutions in tests.
- Do not rewrite generated artifacts by hand when there is already a renderer/writer abstraction.

## Useful Context

- The executable name determines which agent adapter is used.
- Claude Code uses JSON settings management.
- Codex uses TOML provider/profile configuration and skill installation.
- The setup flow is intentionally shared, with adapters controlling agent-specific behavior.

## Validation Before Finishing

Before claiming a change is complete:

- confirm the changed files match the repository style
- run targeted tests for the touched area
- run `uv run ruff check src tests` if the change is non-trivial
- mention any unrun or failing validation clearly in the handoff

