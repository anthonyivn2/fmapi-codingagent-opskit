---
name: fmapi-codingagent-validate-models
description: Validate that the configured FMAPI model exists and is ready in the workspace
user_invocable: true
---

# FMAPI Validate Models

Validate that the configured model name exists as a serving endpoint in your Databricks workspace and is in a READY state.

## Instructions

1. Run the validate-models command:

```bash
setup-fmapi-codex validate-models
```

2. Present the output to the user. The command checks the configured model and reports:

   - **PASS** — Endpoint exists and is READY
   - **WARN** — Endpoint exists but is not in READY state
   - **FAIL** — Endpoint not found in the workspace
   - **SKIP** — Model not configured

3. If the model fails validation:
   - The command exits with code 1
   - Suggest running `$fmapi-codingagent-list-models` to discover available endpoint names
   - Suggest re-running `$fmapi-codingagent-setup` with the correct model name

4. If the command fails before validation:
   - **No config found**: suggest `$fmapi-codingagent-setup` first
   - **OAuth expired**: suggest `$fmapi-codingagent-reauth`
