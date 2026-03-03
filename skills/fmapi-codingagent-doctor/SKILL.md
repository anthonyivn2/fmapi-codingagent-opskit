---
name: fmapi-codingagent-doctor
description: Run comprehensive FMAPI diagnostics — dependencies, configuration, profile, auth, connectivity, and model validation
user_invocable: true
---

# FMAPI Doctor

Run comprehensive diagnostics to identify issues with your Databricks Foundation Model API (FMAPI) configuration.

## Instructions

1. Run the doctor command:

```bash
setup-fmapi-claudecode doctor
```

2. Present the output to the user. The doctor runs eight diagnostic categories:

   - **Dependencies** — Checks that jq, databricks, claude, and curl are installed; reports versions
   - **Environment** — Detects OS, WSL version, and headless state
   - **Configuration** — Verifies settings file is valid JSON, all required FMAPI keys are present, and helper script exists and is executable
   - **Profile** — Confirms the Databricks CLI profile exists in `~/.databrickscfg`
   - **Auth** — Tests whether the OAuth token is valid
   - **Connectivity** — Tests HTTP reachability to the Databricks serving endpoints API. When AI Gateway v2 is configured, also tests gateway endpoint reachability.
   - **Models** — Validates all four configured model names exist and are ready
   - **Hooks** — Verifies SubagentStart and UserPromptSubmit pre-check hooks are configured and executable

3. Each check shows **PASS**, **FAIL**, **WARN**, or **SKIP** with an actionable fix suggestion for failures.

4. If the command exits with code 1, some checks failed. Guide the user through fixing the reported issues. Common fixes:
   - Missing dependencies: install via the suggested command
   - Auth failures: suggest `/fmapi-codingagent-reauth`
   - Missing config: suggest `/fmapi-codingagent-setup`
   - Model issues: suggest `/fmapi-codingagent-list-models` to discover available endpoints
