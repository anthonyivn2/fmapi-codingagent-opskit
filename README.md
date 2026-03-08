# Coding Agents with Databricks Foundation Model API

Databricks serves frontier and open-source LLMs through its [Foundation Model API (FMAPI)](https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis) — and those same models can power coding agents like Claude Code, OpenAI Codex, Gemini CLI, and many others! This repo automates the setup so you can point your favorite coding agent at your Databricks workspace with built-in governance, security, and usage tracking.

> *In case you are wondering, yes, this repo is built alongside coding agents powered by LLMs from Databricks Foundation Model API. We like to dogfood our own products.*

**Status: Experimental** — Currently handles FMAPI setup for coding agents. Considering expanding to cover AI Gateway policies, inference table configuration, and OTEL telemetry ingestion via [Databricks Zerobus](https://docs.databricks.com/aws/en/ingestion/zerobus-overview). Feedback and ideas are welcomed — open an issue or reach out!

## What You Get

- **Leverage Popular Coding Agents against models hosted in your Databricks workspace** &mdash; route all API calls through Databricks Foundation Model API
- **One-command setup** &mdash; installs dependencies, authenticates via OAuth, and configures everything
- **Automatic OAuth token management** &mdash; no PATs to rotate or manage
- **Built-in diagnostics and model validation** &mdash; `doctor`, `list-models`, `validate-models`
- **Plugin slash commands** &mdash; manage your FMAPI config without leaving Claude Code
- **Built-in Usage Tracking and Payload Logging through Databricks AI Gateway** &mdash; Leverage Databricks's [AI Gateway Usage Tracking](https://docs.databricks.com/aws/en/ai-gateway/configure-ai-gateway-endpoints#configure-ai-gateway-using-the-ui) to track and audit Coding Agent usage for your organization, and track your Coding Agent request and response payload through the use of [AI Gateway Inference Table](https://docs.databricks.com/aws/en/ai-gateway/inference-tables)

## Supported Agents

FMAPI supports all of the coding agents listed below. The CLI automates the configuration for each agent &mdash; support for OpenAI Codex and Gemini CLI is planned.

| Coding Agent | CLI Command | Status |
|---|---|---|
| Claude Code | `setup-fmapi-claudecode` | Implemented |
| OpenAI Codex | — | Planned |
| Gemini CLI | — | Planned |

## Claude Code

**Prerequisites:** macOS (Xcode Command Line Tools recommended), Linux, or WSL (Windows Subsystem for Linux; experimental), and a Databricks workspace with FMAPI enabled. Everything else is installed automatically.

### Install

Install with a single command:

```bash
bash <(curl -sL https://raw.githubusercontent.com/anthonyivn2/fmapi-codingagent-setup/main/install.sh)
```

By default, the installer automatically installs the **latest released version**. To install a specific version:

```bash
bash <(curl -sL https://raw.githubusercontent.com/anthonyivn2/fmapi-codingagent-setup/main/install.sh) --version 0.1.0
```

This clones the repo to `~/.fmapi-codingagent-setup/`, installs [uv](https://docs.astral.sh/uv/) if needed, and registers the CLI globally via `uv tool install`. To install to a custom location, set `FMAPI_HOME`:

```bash
FMAPI_HOME=~/my-custom-path bash <(curl -sL https://raw.githubusercontent.com/anthonyivn2/fmapi-codingagent-setup/main/install.sh)
```

Then run setup:

```bash
setup-fmapi-claudecode
```

Setup walks you through the process interactively: it asks for your Databricks workspace URL, a CLI profile name, which models to use (Opus, Sonnet, Haiku), and where to write the settings file. Sensible defaults are provided for everything except the workspace URL.

Once complete you can proceed to run Claude Code as per usual:

```bash
claude
```

<details>
<summary><strong>Install from Source</strong></summary>

Clone the repo manually to any location. Requires [uv](https://docs.astral.sh/uv/) to be installed:

```bash
git clone https://github.com/anthonyivn2/fmapi-codingagent-setup.git
cd fmapi-codingagent-setup
uv tool install . --force
setup-fmapi-claudecode
```

This installs the CLI globally. All commands below work the same regardless of install method.

If you don't have `uv`, install it first: `curl -LsSf https://astral.sh/uv/install.sh | sh`

</details>

<details>
<summary><strong>WSL (Windows) Notes — Experimental</strong></summary>

WSL 1 and WSL 2 are both supported. WSL support is **experimental** — it has not yet been validated on real WSL environments. Please report any issues. The CLI auto-detects WSL and handles browser-based OAuth authentication.

If the browser does not open automatically during OAuth login:

1. **Install `wslu`** (recommended): `sudo apt-get install -y wslu` — provides `wslview` for opening URLs from WSL in your Windows browser.
2. **Or set the `BROWSER` variable**: `export BROWSER='powershell.exe /c start'`

WSL 2 with WSLg (GUI support) typically works without extra configuration.

Run `doctor` to verify your WSL environment:

```bash
setup-fmapi-claudecode doctor
```

</details>

### What Setup Does

1. **Installs dependencies** &mdash; Claude Code, Databricks CLI, and jq. Skips anything already installed. Uses Homebrew on macOS, `apt-get`/`yum` and curl installers on Linux.

2. **Authenticates with Databricks** &mdash; Checks your OAuth session and guides browser login when needed.

3. **Writes `.claude/settings.json`** &mdash; Configures Claude Code to route API calls through your Databricks workspace, including model selection and the path to the token helper. If the file already exists, new values are merged in without overwriting other settings.

4. **Configures automatic token access** &mdash; Writes `fmapi-key-helper.sh` alongside the settings file so Claude Code can request tokens automatically.

5. **Runs a setup health check** &mdash; Verifies authentication and model reachability so setup is ready to use.

6. **Prints a skills hint** &mdash; Shows how to install slash command skills via `setup-fmapi-claudecode install-skills`. See [Plugin Skills](#plugin-skills).

7. **Finishes with actionable output** &mdash; Shows next steps if anything needs attention.

### Managing Your Setup

#### Status Dashboard

```bash
setup-fmapi-claudecode status
```

- **Configuration** &mdash; workspace URL, profile, and model names
- **Auth** &mdash; whether the OAuth session is active or expired
- **File locations** &mdash; paths to settings and helper files

#### Re-authentication

```bash
setup-fmapi-claudecode reauth
```

Triggers `databricks auth login` for your configured profile and verifies the new session is valid.

#### Diagnostics

```bash
setup-fmapi-claudecode doctor
```

Runs ten categories of checks, each reporting **PASS**, **FAIL**, **WARN**, or **SKIP** with actionable fix suggestions:

- **Dependencies** &mdash; jq, databricks, claude, and curl are installed; reports versions
- **Xcode CLT** &mdash; macOS only; verifies Xcode Command Line Tools are installed (skipped on other platforms)
- **Python** &mdash; reports Python version and source (system or uv-managed); warns if below 3.10
- **Environment** &mdash; OS, WSL version, and headless state detection
- **Configuration** &mdash; settings file is valid JSON, all required FMAPI keys present, helper script exists and is executable
- **Profile** &mdash; Databricks CLI profile exists in `~/.databrickscfg`
- **Auth** &mdash; OAuth token is valid
- **Connectivity** &mdash; HTTP reachability to the Databricks serving endpoints API. When AI Gateway v2 is configured, also tests gateway endpoint reachability
- **Models** &mdash; all configured model names exist as endpoints and are READY
- **Runtime files** &mdash; helper and token-cache files are present and healthy

Exits with code 1 if any checks fail.

#### Model Management

List all serving endpoints in your workspace:

```bash
setup-fmapi-claudecode list-models
```

Currently configured models are highlighted in green. Use this to discover available model IDs when running setup.

Validate that your configured models exist and are ready:

```bash
setup-fmapi-claudecode validate-models
```

Reports per-model status: **PASS** (exists and READY), **WARN** (exists but not READY), **FAIL** (not found), or **SKIP** (not configured). Exits with code 1 if any models fail validation.

#### Re-running Setup

You can safely re-run setup at any time to update the workspace URL, profile, or models, or to recover from a missing or corrupted settings file.

When you re-run setup interactively with an existing configuration, it shows a summary of your current settings and asks whether to keep them or reconfigure:

```
  Existing configuration found:

  Workspace  https://my-workspace.cloud.databricks.com
  Profile    profile-name
  TTL        ...
  Model      ...
  Opus       ...
  Sonnet     ...
  Haiku      ...
  Settings   ...

  ? Keep this configuration?
  ❯ Yes, reinstall  re-run setup with existing config
    No, reconfigure start fresh with all prompts
```

Selecting **Yes, reinstall** runs the reinstall path (including helper migration when needed) and then re-runs the full setup (dependencies, auth, settings, smoke test) without prompting for each value. Selecting **No, reconfigure** shows all prompts with your existing values as defaults. First-time users (no existing config) see the normal prompt flow.

For a fully non-interactive re-run using your previously saved configuration:

```bash
setup-fmapi-claudecode reinstall
```

For a lightweight local refresh that only rewrites generated helper/settings artifacts:

```bash
setup-fmapi-claudecode reinstall --refresh-only
```

#### Uninstalling

```bash
setup-fmapi-claudecode uninstall
```

The uninstall command removes all FMAPI artifacts in order:

1. **Helper scripts** &mdash; deletes `fmapi-key-helper.sh` and any legacy `.fmapi-pat-cache` files
2. **Settings** &mdash; removes FMAPI-specific keys (`apiKeyHelper`, `ANTHROPIC_*`, etc.) from `.claude/settings.json`. Non-FMAPI settings are preserved; if no other settings remain, the file is deleted entirely
3. **Install directory** &mdash; removes `~/.fmapi-codingagent-setup/` (the default location created by `install.sh`)

Skills are managed separately. To remove them: `setup-fmapi-claudecode uninstall-skills`

Before removing anything, it lists all discovered artifacts and asks for confirmation. Re-running `uninstall` when nothing is installed is safe &mdash; it reports "Nothing to uninstall" and exits.

##### Manual Cleanup

If you installed to a custom location using `FMAPI_HOME`, the uninstall command only removes the default path. Delete your custom install directory manually:

```bash
rm -rf /path/to/your/custom/install
```

To fully clean up all possible FMAPI-related paths by hand (e.g. if the CLI is already uninstalled):

```bash
# Remove the install directory (default location)
rm -rf ~/.fmapi-codingagent-setup

# Remove the helper script (default location)
rm -f ~/.claude/fmapi-key-helper.sh

# Remove skill files
rm -rf ~/.claude/skills/fmapi-codingagent-*

# Remove FMAPI keys from settings (edit or delete)
# If FMAPI is the only config in ~/.claude/settings.json:
rm -f ~/.claude/settings.json
# Otherwise, remove apiKeyHelper and the ANTHROPIC_* / CLAUDE_CODE_* env keys from the JSON file
```

#### Updating

```bash
setup-fmapi-claudecode self-update
```

Fetches the latest changes from the remote repository and updates in place. Shows how many commits are new and reports the version change. Requires the installation to be a git clone (both the quick installer and manual clone work).

Re-running the installer (`bash <(curl ...) install.sh`) also works for updating. It shows a before/after version comparison:

```
  ok Updated from v1.0.0 → v1.1.0.
```

Or if already current:

```
  ok Already up to date at v1.1.0.
```

When updating an existing install that already has FMAPI configured, the installer does not run setup automatically. If needed, run refresh manually:

```bash
setup-fmapi-claudecode reinstall
```

### Plugin Skills

Run `setup-fmapi-claudecode install-skills` to enable these slash commands (copies skill files to `~/.claude/skills/`). To remove them, use `setup-fmapi-claudecode uninstall-skills`.

Available skills:

| Skill | Description |
|---|---|
| `/fmapi-codingagent-status` | Check FMAPI configuration health &mdash; OAuth session, workspace, and model settings |
| `/fmapi-codingagent-reauth` | Re-authenticate the Databricks OAuth session |
| `/fmapi-codingagent-setup` | Run full FMAPI setup (interactive or non-interactive with CLI flags) |
| `/fmapi-codingagent-doctor` | Run comprehensive diagnostics (dependencies, environment, config, auth, connectivity, and models) |
| `/fmapi-codingagent-list-models` | List all serving endpoints available in the workspace |
| `/fmapi-codingagent-validate-models` | Validate that configured models exist and are ready |

### Advanced Setup

#### Non-Interactive Setup

Pass `--host` to enable non-interactive mode. All other flags auto-default if omitted:

```bash
setup-fmapi-claudecode --host https://my-workspace.cloud.databricks.com
```

Override any default with additional flags &mdash; see [CLI Reference](#cli-reference) for the full list.

#### AI Gateway v2 (Beta)

Route API calls through Databricks AI Gateway v2 instead of the default serving endpoints. AI Gateway v2 uses a dedicated endpoint format (`https://<workspace-id>.ai-gateway.cloud.databricks.com/anthropic`) and may offer additional gateway features.

```bash
# Auto-detect workspace ID
setup-fmapi-claudecode --host https://my-workspace.cloud.databricks.com --ai-gateway

# Explicit workspace ID
setup-fmapi-claudecode --host https://my-workspace.cloud.databricks.com --ai-gateway --workspace-id 1234567890
```

In interactive mode, setup prompts you to choose between "Serving Endpoints (default)" and "AI Gateway v2 (beta)". When AI Gateway is selected, the workspace ID is auto-detected from the Databricks API. If auto-detection fails, you are prompted to enter it manually (or use `--workspace-id` in non-interactive mode).

The `--ai-gateway` flag can also be set via config files using the `"ai_gateway": true` key alongside an optional `"workspace_id"` value. See [`example-config.json`](example-config.json).

**Note:** AI Gateway v2 is in beta. OAuth token management (`apiKeyHelper`) works the same way &mdash; only the base URL changes.

#### Config File Setup

Load configuration from a JSON file instead of passing individual flags. Useful for teams standardizing setup across users.

```bash
# From a local config file
setup-fmapi-claudecode --config ./my-config.json

# From a remote URL (HTTPS only)
setup-fmapi-claudecode --config-url https://example.com/fmapi-config.json

# Config file with CLI overrides (CLI flags take priority)
setup-fmapi-claudecode --config ./my-config.json --model databricks-claude-sonnet-4-6
```

Both `--config` and `--config-url` enable non-interactive mode. See [`example-config.json`](example-config.json) for the full format and all supported keys.

Priority when combining sources: CLI flags > config file > existing `settings.json` > hardcoded defaults. If the config file is missing `host` and no `--host` flag is provided, setup errors out.

### CLI Reference

```
Usage: setup-fmapi-claudecode [OPTIONS] [COMMAND]

Commands:
  status                Show FMAPI configuration health dashboard
  reauth                Re-authenticate Databricks OAuth session
  doctor                Run comprehensive diagnostics
  list-models           List all serving endpoints in the workspace
  validate-models       Validate configured models exist and are ready
  install-skills        Install FMAPI slash command skills to ~/.claude/skills/
  uninstall-skills      Remove FMAPI slash command skills from ~/.claude/skills/
  reinstall             Rerun setup using previously saved configuration
  self-update           Update to the latest version
  uninstall             Remove FMAPI helper scripts and settings

Setup options (used when no subcommand, skip interactive prompts):
  --host URL            Databricks workspace URL (required for non-interactive)
  --profile NAME        CLI profile name (default: fmapi-claudecode-profile)
  --model MODEL         Primary model (default: databricks-claude-opus-4-6)
  --opus MODEL          Opus model (default: databricks-claude-opus-4-6)
  --sonnet MODEL        Sonnet model (default: databricks-claude-sonnet-4-6)
  --haiku MODEL         Haiku model (default: databricks-claude-haiku-4-5)
  --ttl MINUTES         Token refresh interval in minutes (default: 55, max: 60, 55 recommended)
  --settings-location   Where to write settings: "home", "cwd", or path (default: home)
  --ai-gateway          Use AI Gateway v2 for API routing (beta, default: off)
  --workspace-id ID     Databricks workspace ID for AI Gateway (auto-detected if omitted)

Config file options:
  --config PATH         Load configuration from a local JSON file
  --config-url URL      Load configuration from a remote JSON URL (HTTPS only)

Global options:
  --verbose             Show debug-level output
  --quiet, -q           Suppress informational output (errors always shown)
  --no-color            Disable colored output (also respects NO_COLOR env var)
  --dry-run             Show what would happen without making changes
  --version             Show version
  --help                Show help message
```

### How It Works

FMAPI keeps Claude Code authenticated with Databricks automatically via `apiKeyHelper` (`fmapi-key-helper.sh`). The helper first fetches a token, silently refreshes near-expiry tokens by expiring the Databricks CLI cache entry in-place, then retries once. If no valid token is available, it attempts non-interactive auto re-auth (`BROWSER=none`) and polls briefly before falling back to manual re-auth instructions.

By default, Claude checks for a fresh token every 55 minutes (configurable with `--ttl`, up to 60 minutes). If your login session is still expired after helper auto-recovery, run `setup-fmapi-claudecode reauth` (or `/fmapi-codingagent-reauth` inside Claude Code) and continue.

### Troubleshooting

> **Not sure what's wrong?** Run `doctor` first &mdash; it checks dependencies, environment, config files, auth, connectivity, and models in one pass:
> ```bash
> setup-fmapi-claudecode doctor
> ```

---

#### "Workspace URL must start with https://"

The CLI requires the full URL with scheme. Use the format:

```
https://my-workspace.cloud.databricks.com
```

Do not include a trailing slash or path segments.

---

#### Token errors in Claude Code

If Claude shows token/authentication errors (after helper auto-refresh/auto-reauth attempts), use this quick recovery flow:

1. Re-authenticate:
   ```bash
   setup-fmapi-claudecode reauth
   ```
   Or use `/fmapi-codingagent-reauth` inside Claude Code.
2. Check current status:
   ```bash
   setup-fmapi-claudecode status
   ```
3. Refresh setup files:
   ```bash
   setup-fmapi-claudecode reinstall --refresh-only
   ```
   Or run full setup to regenerate and validate everything:
   ```bash
   setup-fmapi-claudecode
   ```
4. If you use other Databricks tools, ensure shell-level auth overrides are not set when launching Claude Code:
   ```bash
   unset DATABRICKS_TOKEN DATABRICKS_HOST DATABRICKS_AUTH_TYPE
   ```

---

#### Databricks CLI error: `cache: load: parse: invalid character ...`

This usually means local Databricks CLI auth data is corrupted.

Re-authenticate first. If the error persists, run this recovery command and retry:

```bash
rm -f ~/.databricks/token-cache.json
setup-fmapi-claudecode reauth
```

---

#### Claude Code returns "authentication failed" or 401 errors

Your OAuth session has likely expired. OAuth sessions expire after a period of inactivity.

1. Re-authenticate:
   ```bash
   setup-fmapi-claudecode reauth
   ```
2. Verify the session is now valid:
   ```bash
   setup-fmapi-claudecode status
   ```
3. Restart Claude Code:
   ```bash
   claude
   ```

---

#### Model not found or "endpoint does not exist"

The configured model name does not match any serving endpoint in your workspace.

1. List available endpoints to find the correct name:
   ```bash
   setup-fmapi-claudecode list-models
   ```
2. Re-run setup and select the correct model IDs:
   ```bash
   setup-fmapi-claudecode
   ```

---

#### Claude Code starts but responses are slow or time out

This is usually a serving endpoint issue, not a setup issue. Check that your endpoints are in READY state:

```bash
setup-fmapi-claudecode validate-models
```

If any model shows **WARN** (exists but not READY), the endpoint may be provisioning or unhealthy. Check the endpoint status in your Databricks workspace UI.

---

#### "databricks: command not found"

The Databricks CLI is not installed or not on your `PATH`. Setup installs it automatically, but if that failed:

- **macOS:** `brew install databricks`
- **Linux:** `curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh`

Then re-run setup.

---

#### Still stuck?

If none of the above help, run a full diagnostic and review the output:

```bash
setup-fmapi-claudecode doctor --verbose
```

The `--verbose` flag adds debug-level detail to every check. Look for any **FAIL** lines &mdash; each includes a suggested fix.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). While the version is `0.x`, minor releases may include breaking changes. Stability guarantees begin at `1.0.0`.

- **Releases**: See the [GitHub Releases](https://github.com/anthonyivn2/fmapi-codingagent-opskit/releases) page for all releases, or [CHANGELOG.md](CHANGELOG.md) for a detailed history.
- **Install a specific version**: Pass `--version X.Y.Z` to the installer (see [Install](#install)).

### Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch from `main`
3. Open a pull request against `main`

All pull requests require review from the code owner before merging. See [RELEASING.md](RELEASING.md) for the release process.

## Other Agents

OpenAI Codex and Gemini CLI are planned &mdash; see the [Supported Agents](#supported-agents) table for current status. Contributions welcome.
