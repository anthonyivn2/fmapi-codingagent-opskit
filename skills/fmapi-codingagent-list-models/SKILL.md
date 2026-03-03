---
name: fmapi-codingagent-list-models
description: List all serving endpoints available in your Databricks workspace
user_invocable: true
---

# FMAPI List Models

List all serving endpoints available in your Databricks workspace to discover model names for FMAPI configuration.

## Instructions

1. Run the list-models command:

```bash
setup-fmapi-claudecode list-models
```

2. Present the output to the user. The command displays a table of all serving endpoints with:

   - **ENDPOINT NAME** — The name of the serving endpoint
   - **STATE** — Whether the endpoint is READY or NOT_READY
   - **TYPE** — The endpoint type

3. The table uses visual markers:
   - **`>` (green)** — Currently configured model (in your settings)

4. If the command fails:
   - **No config found**: suggest `/fmapi-codingagent-setup` first
   - **OAuth expired**: suggest `/fmapi-codingagent-reauth`
   - **No endpoints found**: the workspace may not have FMAPI enabled
