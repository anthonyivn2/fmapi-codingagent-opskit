---
name: fmapi-codingagent-validate-models
description: Validate that configured FMAPI models exist and are ready in the workspace
user_invocable: true
---

# FMAPI Validate Models

Validate that all configured model names exist as serving endpoints in your Databricks workspace and are in a READY state.

## Instructions

1. Run the validate-models command:

```bash
setup-fmapi-claudecode validate-models
```

2. Present the output to the user. The command checks each configured model (Model, Opus, Sonnet, Haiku) and reports:

   - **PASS** — Endpoint exists and is READY
   - **WARN** — Endpoint exists but is not in READY state
   - **FAIL** — Endpoint not found in the workspace
   - **SKIP** — Model not configured

3. If any models fail validation:
   - The command exits with code 1
   - Suggest running `/fmapi-codingagent-list-models` to discover available endpoint names
   - Suggest re-running `/fmapi-codingagent-setup` with correct model names

4. If the command fails before validation:
   - **No config found**: suggest `/fmapi-codingagent-setup` first
   - **OAuth expired**: suggest `/fmapi-codingagent-reauth`
