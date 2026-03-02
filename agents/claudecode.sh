#!/bin/bash
# agents/claudecode.sh — Claude Code agent adapter
# Defines all Claude Code-specific variables and functions.
# Sourced by setup-fmapi-claudecode.sh after lib/core.sh; do not run directly.

# ── Agent identity ───────────────────────────────────────────────────────────
AGENT_NAME="Claude Code"
AGENT_ID="claudecode"
AGENT_CLI_CMD="claude"
AGENT_CLI_INSTALL_CMD="curl -fsSL https://claude.ai/install.sh | bash"

# ── Settings paths ───────────────────────────────────────────────────────────
AGENT_SETTINGS_DIR=".claude"
AGENT_SETTINGS_FILENAME="settings.json"
AGENT_HELPER_FILENAME="fmapi-key-helper.sh"
AGENT_HOOK_PRECHECK_FILENAME="fmapi-auth-precheck.sh"

# ── Defaults ─────────────────────────────────────────────────────────────────
AGENT_DEFAULT_PROFILE="fmapi-claudecode-profile"
AGENT_DEFAULT_MODEL="databricks-claude-opus-4-6"
AGENT_DEFAULT_OPUS="databricks-claude-opus-4-6"
AGENT_DEFAULT_SONNET="databricks-claude-sonnet-4-6"
AGENT_DEFAULT_HAIKU="databricks-claude-haiku-4-5"

# ── Endpoint filtering (for list-models table) ──────────────────────────────
AGENT_ENDPOINT_FILTER="claude|anthropic"
AGENT_ENDPOINT_TITLE="Anthropic Claude"
AGENT_BASE_URL_SUFFIX="/serving-endpoints/anthropic"

# ── Environment variable names (written to settings.json .env block) ─────────
AGENT_ENV_MODEL="ANTHROPIC_MODEL"
AGENT_ENV_BASE_URL="ANTHROPIC_BASE_URL"
AGENT_ENV_OPUS="ANTHROPIC_DEFAULT_OPUS_MODEL"
AGENT_ENV_SONNET="ANTHROPIC_DEFAULT_SONNET_MODEL"
AGENT_ENV_HAIKU="ANTHROPIC_DEFAULT_HAIKU_MODEL"
AGENT_ENV_TTL="CLAUDE_CODE_API_KEY_HELPER_TTL_MS"

# Required env keys for doctor checks
AGENT_REQUIRED_ENV_KEYS=("ANTHROPIC_MODEL" "ANTHROPIC_BASE_URL" "ANTHROPIC_DEFAULT_OPUS_MODEL" "ANTHROPIC_DEFAULT_SONNET_MODEL" "ANTHROPIC_DEFAULT_HAIKU_MODEL")

# Legacy keys to remove from .env on write
AGENT_LEGACY_CLEANUP_KEYS=("ANTHROPIC_AUTH_TOKEN")

# ── Functions ────────────────────────────────────────────────────────────────

# Return settings file search paths (sets _SETTINGS_CANDIDATES array).
agent_settings_candidates() {
  _SETTINGS_CANDIDATES=(
    "$HOME/${AGENT_SETTINGS_DIR}/${AGENT_SETTINGS_FILENAME}"
    "./${AGENT_SETTINGS_DIR}/${AGENT_SETTINGS_FILENAME}"
  )
}

# Read model/TTL from a settings file into CFG_* variables.
# Usage: agent_read_env /path/to/settings.json
agent_read_env() {
  local settings_file="$1"
  CFG_MODEL=$(jq -r --arg key "$AGENT_ENV_MODEL" '.env[$key] // empty' "$settings_file" 2>/dev/null) || true
  CFG_OPUS=$(jq -r --arg key "$AGENT_ENV_OPUS" '.env[$key] // empty' "$settings_file" 2>/dev/null) || true
  CFG_SONNET=$(jq -r --arg key "$AGENT_ENV_SONNET" '.env[$key] // empty' "$settings_file" 2>/dev/null) || true
  CFG_HAIKU=$(jq -r --arg key "$AGENT_ENV_HAIKU" '.env[$key] // empty' "$settings_file" 2>/dev/null) || true

  local cfg_ttl_ms=""
  cfg_ttl_ms=$(jq -r --arg key "$AGENT_ENV_TTL" '.env[$key] // empty' "$settings_file" 2>/dev/null) || true
  [[ -n "$cfg_ttl_ms" ]] && CFG_TTL=$(( cfg_ttl_ms / 60000 ))
}

# Build the env JSON block for settings.json.
# Usage: agent_write_env_json model base_url opus sonnet haiku ttl_ms
agent_write_env_json() {
  local model="$1" base_url="$2" opus="$3" sonnet="$4" haiku="$5" ttl_ms="$6"
  jq -n \
    --arg model "$model" \
    --arg base "$base_url" \
    --arg opus "$opus" \
    --arg sonnet "$sonnet" \
    --arg haiku "$haiku" \
    --arg ttl "$ttl_ms" \
    '{
      "ANTHROPIC_MODEL": $model,
      "ANTHROPIC_BASE_URL": $base,
      "ANTHROPIC_DEFAULT_OPUS_MODEL": $opus,
      "ANTHROPIC_DEFAULT_SONNET_MODEL": $sonnet,
      "ANTHROPIC_DEFAULT_HAIKU_MODEL": $haiku,
      "ANTHROPIC_CUSTOM_HEADERS": "x-databricks-use-coding-agent-mode: true",
      "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1",
      "CLAUDE_CODE_API_KEY_HELPER_TTL_MS": $ttl
    }'
}

# Return JSON array of env keys to clean on uninstall.
agent_uninstall_env_keys_json() {
  echo '["ANTHROPIC_MODEL","ANTHROPIC_BASE_URL","ANTHROPIC_AUTH_TOKEN","ANTHROPIC_DEFAULT_OPUS_MODEL","ANTHROPIC_DEFAULT_SONNET_MODEL","ANTHROPIC_DEFAULT_HAIKU_MODEL","ANTHROPIC_CUSTOM_HEADERS","CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS","CLAUDE_CODE_API_KEY_HELPER_TTL_MS"]'
}

# Set hasCompletedOnboarding in ~/.claude.json.
agent_ensure_onboarding() {
  local claude_json="$HOME/.claude.json"

  if [[ -f "$claude_json" ]]; then
    local current=""
    current=$(jq -r '.hasCompletedOnboarding // empty' "$claude_json" 2>/dev/null) || true
    if [[ "$current" == "true" ]]; then
      debug "agent_ensure_onboarding: already set in ${claude_json}"
      return 0
    fi
  fi

  [[ "$VERBOSITY" -ge 1 ]] && echo -e "\n${BOLD}Onboarding flag${RESET}"

  if [[ -f "$claude_json" ]]; then
    local tmpfile=""
    tmpfile=$(mktemp "${claude_json}.XXXXXX")
    _CLEANUP_FILES+=("$tmpfile")
    jq '.hasCompletedOnboarding = true' "$claude_json" > "$tmpfile"
    chmod 600 "$tmpfile"
    mv "$tmpfile" "$claude_json"
  else
    echo '{"hasCompletedOnboarding":true}' | jq '.' > "$claude_json"
    chmod 600 "$claude_json"
  fi
  debug "agent_ensure_onboarding: set hasCompletedOnboarding=true in ${claude_json}"
  success "Onboarding flag set in ${claude_json}."
}

# Register plugin in ~/.claude/plugins/installed_plugins.json.
# Usage: agent_register_plugin script_dir
agent_register_plugin() {
  local script_dir="$1"
  if [[ ! -f "${script_dir}/.claude-plugin/plugin.json" ]]; then
    return 0
  fi

  local plugins_file="$HOME/.claude/plugins/installed_plugins.json"
  mkdir -p "$(dirname "$plugins_file")"

  local needs_install=true
  if [[ -f "$plugins_file" ]]; then
    local existing_path=""
    existing_path=$(jq -r '.["fmapi-codingagent"].installPath // empty' "$plugins_file" 2>/dev/null) || true
    [[ "$existing_path" == "$script_dir" ]] && needs_install=false
  fi

  if [[ "$needs_install" == true ]]; then
    if [[ -f "$plugins_file" ]]; then
      local plugin_tmp=""
      plugin_tmp=$(mktemp "${plugins_file}.XXXXXX")
      _CLEANUP_FILES+=("$plugin_tmp")
      jq --arg path "$script_dir" \
        '.["fmapi-codingagent"] = {"scope": "user", "installPath": $path}' \
        "$plugins_file" > "$plugin_tmp"
      mv "$plugin_tmp" "$plugins_file"
    else
      jq -n --arg path "$script_dir" \
        '{"fmapi-codingagent": {"scope": "user", "installPath": $path}}' > "$plugins_file"
    fi
    success "Plugin registered (skills: /fmapi-codingagent-status, /fmapi-codingagent-reauth, /fmapi-codingagent-setup, /fmapi-codingagent-doctor, /fmapi-codingagent-list-models, /fmapi-codingagent-validate-models)."
  fi
}

# Remove plugin from ~/.claude/plugins/installed_plugins.json.
agent_deregister_plugin() {
  local plugins_file="$HOME/.claude/plugins/installed_plugins.json"
  if [[ -f "$plugins_file" ]] && jq -e '.["fmapi-codingagent"]' "$plugins_file" &>/dev/null; then
    local ptmp=""
    ptmp=$(mktemp "${plugins_file}.XXXXXX")
    _CLEANUP_FILES+=("$ptmp")
    jq 'del(.["fmapi-codingagent"])' "$plugins_file" > "$ptmp"
    local plen=""
    plen=$(jq 'length' "$ptmp")
    if [[ "$plen" == "0" ]]; then
      rm -f "$ptmp" "$plugins_file"
      success "Removed plugin registration (file deleted — no other plugins)."
    else
      mv "$ptmp" "$plugins_file"
      success "Removed plugin registration from ${plugins_file}."
    fi
  fi
}

# Install the agent CLI if missing.
agent_install_cli() {
  if command -v "$AGENT_CLI_CMD" &>/dev/null; then
    success "${AGENT_NAME} already installed."
  else
    info "Installing ${AGENT_NAME} ..."
    eval "$AGENT_CLI_INSTALL_CMD"
    success "${AGENT_NAME} installed."
  fi
}

# Doctor: check agent-specific configuration (hasCompletedOnboarding).
# Returns 0 on pass, 1 on failure.
agent_doctor_extra() {
  local claude_json="$HOME/.claude.json"
  if [[ -f "$claude_json" ]]; then
    local ob_val=""
    ob_val=$(jq -r '.hasCompletedOnboarding // empty' "$claude_json" 2>/dev/null) || true
    if [[ "$ob_val" == "true" ]]; then
      echo -e "  ${GREEN}${BOLD}PASS${RESET}  hasCompletedOnboarding is set  ${DIM}${claude_json}${RESET}"
      return 0
    else
      echo -e "  ${RED}${BOLD}FAIL${RESET}  hasCompletedOnboarding not set  ${DIM}Fix: re-run setup or add to ${claude_json}${RESET}"
      return 1
    fi
  else
    echo -e "  ${RED}${BOLD}FAIL${RESET}  ${claude_json} not found  ${DIM}Fix: re-run setup${RESET}"
    return 1
  fi
}

# Print env vars for dry-run display.
# Usage: agent_dry_run_env_display model base_url opus sonnet haiku ttl_ms
agent_dry_run_env_display() {
  local model="$1" base_url="$2" opus="$3" sonnet="$4" haiku="$5" ttl_ms="$6"
  echo -e "       ${AGENT_ENV_MODEL}=${BOLD}${model}${RESET}"
  echo -e "       ${AGENT_ENV_BASE_URL}=${BOLD}${base_url}${RESET}"
  echo -e "       ${AGENT_ENV_OPUS}=${BOLD}${opus}${RESET}"
  echo -e "       ${AGENT_ENV_SONNET}=${BOLD}${sonnet}${RESET}"
  echo -e "       ${AGENT_ENV_HAIKU}=${BOLD}${haiku}${RESET}"
  echo -e "       ${AGENT_ENV_TTL}=${BOLD}${ttl_ms}${RESET}"
}

# Dry-run: print onboarding and plugin registration sections.
agent_dry_run_extra() {
  # Onboarding
  echo -e "  ${BOLD}Onboarding${RESET}"
  local claude_json="$HOME/.claude.json"
  local onboarding_done=false
  if [[ -f "$claude_json" ]]; then
    local ob_val=""
    ob_val=$(jq -r '.hasCompletedOnboarding // empty' "$claude_json" 2>/dev/null) || true
    [[ "$ob_val" == "true" ]] && onboarding_done=true
  fi
  if [[ "$onboarding_done" == true ]]; then
    echo -e "  ${GREEN}${BOLD}ok${RESET}  hasCompletedOnboarding already set in ${DIM}${claude_json}${RESET}"
  else
    echo -e "  ${CYAN}::${RESET}  Would set hasCompletedOnboarding=true in ${DIM}${claude_json}${RESET}"
  fi
  echo ""

  # Plugin registration
  echo -e "  ${BOLD}Plugin registration${RESET}"
  local plugins_file="$HOME/.claude/plugins/installed_plugins.json"
  if [[ -f "$plugins_file" ]]; then
    local existing_path=""
    existing_path=$(jq -r '.["fmapi-codingagent"].installPath // empty' "$plugins_file" 2>/dev/null) || true
    if [[ "$existing_path" == "$SCRIPT_DIR" ]]; then
      echo -e "  ${GREEN}${BOLD}ok${RESET}  Already registered"
    else
      echo -e "  ${CYAN}::${RESET}  Would register plugin at ${BOLD}${SCRIPT_DIR}${RESET}"
    fi
  else
    echo -e "  ${CYAN}::${RESET}  Would register plugin at ${BOLD}${SCRIPT_DIR}${RESET}"
  fi
}
