---
name: fmapi-codingagent-reauth
description: Re-authenticate Databricks OAuth session for FMAPI
user_invocable: true
---

# FMAPI Re-authentication

Re-authenticate your Databricks OAuth session without re-running the full setup.

## Instructions

1. Run the reauth command:

```bash
setup-fmapi-claudecode reauth
```

2. This command will:
   - Discover the existing FMAPI configuration
   - Trigger `databricks auth login` to start an OAuth flow in the browser
   - Verify the new session is valid
   - Print a success or failure message

3. If no existing FMAPI configuration is found, inform the user they need to run `/fmapi-codingagent-setup` first.
