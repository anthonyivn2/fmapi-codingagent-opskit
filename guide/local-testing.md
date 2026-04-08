# Local Testing Guide

This guide explains how to test `fmapi-codingagent-opskit` in two common scenarios:

1. using the package the way a normal user installs it
2. modifying this repository locally and testing your local changes before release

## Prerequisites

Make sure you have these available:

- `uv`
- `jq`
- Databricks CLI (`databricks`)
- Codex CLI if you are testing Codex flows
- Claude Code if you are testing Claude Code flows

From the repository root, install dev dependencies:

```bash
uv sync --group dev
```

## Testing As A Regular Installed User

This path is useful when you want to validate the real end-user install flow.

### 1. Install the package

From the repository root:

```bash
uv pip install .
```

Or if you want the CLI in an isolated tool environment:

```bash
uv tool install .
```

### 2. Verify the installed commands

```bash
setup-fmapi-codex --version
setup-fmapi-claudecode --version
```

Expected result: both commands print the installed package version.

### 3. Run a safe dry run

Codex example:

```bash
setup-fmapi-codex \
  --dry-run \
  --host https://<your-workspace>.cloud.databricks.com \
  --profile default \
  --model gpt-5.4 \
  --model-reasoning-effort high \
  --provider-id Databricks \
  --provider-name "Databricks AI Gateway"
```

Claude Code example:

```bash
setup-fmapi-claudecode \
  --dry-run \
  --host https://<your-workspace>.cloud.databricks.com \
  --profile fmapi-claudecode-profile
```

Use dry run first to confirm:

- the correct workspace URL is used
- the expected settings file path is shown
- the helper script path is shown
- Codex-specific values match your intended TOML shape

### 4. Run the real setup

Codex example:

```bash
setup-fmapi-codex \
  --host https://<your-workspace>.cloud.databricks.com \
  --profile default \
  --model gpt-5.4 \
  --model-reasoning-effort low \
  --provider-id Databricks \
  --provider-name "Databricks AI Gateway"
```

After setup, inspect the generated file:

- Codex config: `~/.codex/config.toml`
- Codex helper: `~/.codex/fmapi-key-helper.sh`
- Claude Code config: `~/.claude/settings.json`
- Claude Code helper: `~/.claude/fmapi-key-helper.sh`

For the current Codex flow, the generated TOML should look conceptually like this:

```toml
profile = "default"

[profiles.default]
model_provider = "Databricks"
model = "gpt-5.4"
model_reasoning_effort = "low"

[model_providers.Databricks]
name = "Databricks AI Gateway"
base_url = "https://..."
wire_api = "responses"
```

### 5. Validate the helper

Run the helper directly:

```bash
~/.codex/fmapi-key-helper.sh
```

Expected result: it prints an access token or completes successfully when the CLI is authenticated.

### 6. Validate the agent CLI

If testing Codex:

```bash
codex
```

If testing Claude Code, launch Claude Code normally and confirm the installed settings are picked up.

## Testing Local Repository Changes

This path is useful when you are actively editing this repository and want to test your local changes without publishing a package.

When testing local source changes, prefer `uv run setup-fmapi-codex` over `setup-fmapi-codex`. This ensures you are executing the code from your current working tree instead of an older globally installed CLI.

### Option A: Run the local entrypoint directly with `uv run`

This is the fastest feedback loop.

Codex example:

```bash
uv run setup-fmapi-codex \
  --dry-run \
  --host https://<your-workspace>.cloud.databricks.com \
  --profile default \
  --model gpt-5.4 \
  --model-reasoning-effort high \
  --provider-id Databricks \
  --provider-name "Databricks AI Gateway"
```

This runs the code from your working tree instead of a separately installed release.

### Option B: Reinstall the package from your local working tree

If you want to test the real installed command names after a local change:

```bash
uv pip install --reinstall .
```

Or for a tool install:

```bash
uv tool install --force .
```

Then rerun the setup commands normally.

## Recommended Local Dev Workflow

When making code changes, use this order:

### 1. Run targeted tests

Examples:

```bash
uv run pytest tests/test_toml_manager.py
uv run pytest tests/test_codex_adapter.py
uv run pytest tests/test_config_validation.py
uv run pytest tests/test_auth.py
```

### 2. Run lint checks

```bash
uv run ruff check src tests
```

### 3. Run a dry run through the local CLI

```bash
uv run setup-fmapi-codex --dry-run --host https://<your-workspace>.cloud.databricks.com
```

### 4. Run the real flow against a local test environment

Use a non-production workspace or a disposable local config backup when possible.

For local repository changes, run the real setup through the repo entrypoint as well:

```bash
uv run setup-fmapi-codex \
  --host https://<your-workspace>.cloud.databricks.com \
  --profile default \
  --model gpt-5.4
```

## Testing Config-File Based Setup

You can also test the `--config` path with a local JSON file.

Create a file such as `tmp-codex-config.json`:

```json
{
  "version": 1,
  "host": "https://<your-workspace>.cloud.databricks.com",
  "profile": "default",
  "provider_id": "Databricks",
  "provider_name": "Databricks AI Gateway",
  "model": "gpt-5.4",
  "model_reasoning_effort": "low",
  "ttl": 30
}
```

Then run:

```bash
uv run setup-fmapi-codex --config tmp-codex-config.json
```

Afterward, inspect `~/.codex/config.toml` and confirm the generated values match the JSON input.

## Safe Backup And Restore

Before running a real setup against your personal config, back it up.

Codex:

```bash
cp ~/.codex/config.toml ~/.codex/config.toml.bak 2>/dev/null || true
cp ~/.codex/fmapi-key-helper.sh ~/.codex/fmapi-key-helper.sh.bak 2>/dev/null || true
```

Claude Code:

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak 2>/dev/null || true
cp ~/.claude/fmapi-key-helper.sh ~/.claude/fmapi-key-helper.sh.bak 2>/dev/null || true
```

Restore if needed:

```bash
cp ~/.codex/config.toml.bak ~/.codex/config.toml 2>/dev/null || true
cp ~/.codex/fmapi-key-helper.sh.bak ~/.codex/fmapi-key-helper.sh 2>/dev/null || true
```

## Troubleshooting

### `setup-fmapi-codex` uses old behavior

You may still be invoking a previously installed version. Use:

```bash
uv run setup-fmapi-codex --version
which setup-fmapi-codex
```

If needed, reinstall from the current repo:

```bash
uv pip install --reinstall .
```

If you are testing code changes in this repository, use:

```bash
uv run setup-fmapi-codex ...
```

This is the recommended path for local development testing.

### Tests pass but runtime behavior looks stale

Make sure you are testing the local source with:

```bash
uv run setup-fmapi-codex ...
```

### Auth helper fails

Confirm Databricks CLI auth works first:

```bash
databricks auth profiles
```

Then retry the generated helper script.

## Suggested Validation Before Opening A PR

Run at least:

```bash
uv run pytest tests/test_toml_manager.py tests/test_codex_adapter.py tests/test_config_validation.py
uv run ruff check src tests
```

If you changed setup flow behavior, also run one manual `--dry-run` and one real setup against a safe workspace.
