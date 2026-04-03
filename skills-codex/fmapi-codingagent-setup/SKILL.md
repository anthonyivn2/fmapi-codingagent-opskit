---
name: fmapi-codingagent-setup
description: Configure Codex to use Databricks Foundation Model API — interactive or non-interactive setup
user_invocable: true
---

# FMAPI Setup

Configure Codex to use Databricks Foundation Model API (FMAPI).

## Instructions

1. Ask the user how they want to run setup:

### Interactive mode (default)

Run with no arguments. The CLI will prompt for all required values, pre-populating defaults from any existing configuration:

```bash
setup-fmapi-codex
```

### Non-interactive mode

Pass `--host` to enable non-interactive mode. All other flags auto-default if omitted:

```bash
setup-fmapi-codex \
  --host "https://my-workspace.cloud.databricks.com"
```

## Available CLI Flags

| Flag | Description | Example |
|---|---|---|
| `--host URL` | Databricks workspace URL | `--host https://my-workspace.cloud.databricks.com` |
| `--profile NAME` | Databricks CLI profile name | `--profile my-profile` |
| `--model MODEL` | Model (default: `databricks-gpt-5-2`) | `--model databricks-gpt-5-2` |
| `--ttl MINUTES` | Token refresh interval in minutes (default: `55`, max: `60`, 55 recommended) | `--ttl 55` |
| `--settings-location PATH` | Where to write settings (`home`, `cwd`, or a custom path) | `--settings-location home` |
| `--ai-gateway` | Use AI Gateway v2 for API routing (beta, default: off) | `--ai-gateway` |
| `--workspace-id ID` | Databricks workspace ID for AI Gateway (auto-detected if omitted) | `--workspace-id 1234567890` |
| `--config PATH` | Load configuration from a local JSON file | `--config ./my-config.json` |
| `--config-url URL` | Load configuration from a remote JSON URL (HTTPS only) | `--config-url https://example.com/cfg.json` |
| `--verbose` | Show debug-level output | `--verbose` |
| `--quiet` / `-q` | Suppress informational output (errors always shown) | `--quiet` |
| `--no-color` | Disable colored output | `--no-color` |
| `--dry-run` | Show what would happen without making changes | `--dry-run --host https://...` |

When `--host`, `--config`, or `--config-url` is provided, the CLI runs non-interactively. Other flags auto-default if omitted (profile defaults to `fmapi-codex-profile`). CLI flags override config file values. `--config` and `--config-url` are mutually exclusive. `--dry-run` implies non-interactive mode.

## Other Commands

| Command | Description |
|---|---|
| `setup-fmapi-codex status` | Check FMAPI configuration health (use `$fmapi-codingagent-status` instead) |
| `setup-fmapi-codex reauth` | Re-authenticate OAuth session (use `$fmapi-codingagent-reauth` instead) |
| `setup-fmapi-codex self-update` | Update to the latest version |
| `setup-fmapi-codex uninstall` | Remove all FMAPI artifacts |
| `setup-fmapi-codex --help` | Show help message |
