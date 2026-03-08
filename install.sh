#!/bin/bash
set -euo pipefail

REPO_URL="https://github.com/anthonyivn2/fmapi-codingagent-setup.git"
INSTALL_DIR="${FMAPI_HOME:-${HOME}/.fmapi-codingagent-setup}"
BRANCH=""
USER_SET_REF=false

# ── Colors (respect NO_COLOR) ────────────────────────────────────────────────
BOLD='\033[1m' DIM='\033[2m' GREEN='\033[32m' CYAN='\033[36m' RED='\033[31m' YELLOW='\033[33m' RESET='\033[0m'
if [[ ! -t 1 ]] || [[ -n "${NO_COLOR:-}" ]]; then
  BOLD='' DIM='' GREEN='' CYAN='' RED='' YELLOW='' RESET=''
fi

info()    { echo -e "  ${CYAN}::${RESET} $1"; }
success() { echo -e "  ${GREEN}${BOLD}ok${RESET} $1"; }
warn()    { echo -e "  ${YELLOW}${BOLD}!!${RESET}${YELLOW} $1${RESET}"; }
error()   { echo -e "\n  ${RED}${BOLD}!! ERROR${RESET}${RED} $1${RESET}\n" >&2; }

_is_tag_ref() {
  local repo="$1"
  local ref="$2"
  git -C "$repo" show-ref --verify --quiet "refs/tags/$ref"
}

_is_remote_tag_ref() {
  local repo="$1"
  local ref="$2"
  git -C "$repo" ls-remote --exit-code --tags origin "refs/tags/$ref" >/dev/null 2>&1
}

_fetch_ref() {
  local repo="$1"
  local ref="$2"
  if _is_remote_tag_ref "$repo" "$ref"; then
    git -C "$repo" fetch --quiet origin "+refs/tags/$ref:refs/tags/$ref"
  else
    git -C "$repo" fetch --quiet origin "$ref"
  fi
}

_checkout_ref() {
  local repo="$1"
  local ref="$2"
  if _is_tag_ref "$repo" "$ref"; then
    local tag_commit
    tag_commit=$(git -C "$repo" rev-parse "refs/tags/$ref^{}")
    git -C "$repo" checkout --quiet "$tag_commit" >/dev/null 2>&1
  else
    git -C "$repo" checkout --quiet "$ref"
  fi
}

# ── Helpers ──────────────────────────────────────────────────────────────────

# Detect existing FMAPI config in ~/.claude/settings.json
_has_fmapi_config() {
  local settings="$HOME/.claude/settings.json"
  [[ -f "$settings" ]] || return 1
  if command -v jq &>/dev/null; then
    local helper=""
    helper=$(jq -r '.apiKeyHelper // empty' "$settings" 2>/dev/null) || true
    [[ -n "$helper" ]] && return 0
    return 1
  fi
  grep -q "apiKeyHelper" "$settings" 2>/dev/null
}

# ── Parse flags ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      if [[ -n "$BRANCH" ]]; then error "--version and --branch are mutually exclusive."; exit 1; fi
      BRANCH="${2:-}"; if [[ -z "$BRANCH" ]]; then error "--version requires a value."; exit 1; fi
      # Accept with or without 'v' prefix
      [[ "$BRANCH" != v* ]] && BRANCH="v${BRANCH}"
      USER_SET_REF=true; shift 2 ;;
    --branch)
      if [[ -n "$BRANCH" ]]; then error "--version and --branch are mutually exclusive."; exit 1; fi
      BRANCH="${2:-}"; if [[ -z "$BRANCH" ]]; then error "--branch requires a value."; exit 1; fi
      USER_SET_REF=true; shift 2 ;;
    -h|--help)
      echo "Usage: bash <(curl -sL .../install.sh) [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --version VER   Install a specific release version (e.g., 0.1.0 or v0.1.0)"
      echo "  --branch NAME   Install from a git branch or tag (e.g., main, v0.1.0)"
      echo "  -h, --help      Show this help"
      echo ""
      echo "By default, the latest release tag is installed. Falls back to main if"
      echo "no releases exist."
      echo ""
      echo "Environment variables:"
      echo "  FMAPI_HOME      Install location (default: ~/.fmapi-codingagent-setup)"
      exit 0 ;;
    *) error "Unrecognized option: $1"; exit 1 ;;
  esac
done

# ── Check Xcode CLT (macOS only, non-blocking) ─────────────────────────────
if [[ "$(uname -s)" == "Darwin" ]]; then
  if xcode-select -p &>/dev/null; then
    success "Xcode Command Line Tools installed."
  else
    warn "Xcode Command Line Tools not found. Fix: xcode-select --install"
  fi
fi

# ── Require git ──────────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
  error "git is required but not installed."
  exit 1
fi

echo -e "\n${BOLD}  FMAPI Codingagent Setup — Installer${RESET}\n"

# ── Resolve version ─────────────────────────────────────────────────────────
if [[ -z "$BRANCH" ]]; then
  # Auto-detect latest release tag via git ls-remote
  LATEST_TAG=$(git ls-remote --tags --sort=-v:refname "$REPO_URL" 'v*' 2>/dev/null \
    | head -1 | sed 's/.*refs\/tags\///' | sed 's/\^{}//')
  if [[ -n "$LATEST_TAG" ]]; then
    BRANCH="$LATEST_TAG"
    info "Latest release: ${BOLD}${LATEST_TAG}${RESET}"
  else
    BRANCH="main"
    warn "No release tags found. Installing from main."
  fi
fi

# ── Clone or update ──────────────────────────────────────────────────────────
IS_UPDATE=false
pre_version=""
post_version=""

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  IS_UPDATE=true
  # Capture pre-update version
  if [[ -f "${INSTALL_DIR}/VERSION" ]]; then
    pre_version=$(tr -d '[:space:]' < "${INSTALL_DIR}/VERSION")
  fi

  info "Existing installation found at ${DIM}${INSTALL_DIR}${RESET}"
  info "Updating..."
  _fetch_ref "$INSTALL_DIR" "$BRANCH"
  _checkout_ref "$INSTALL_DIR" "$BRANCH"
  if ! _is_tag_ref "$INSTALL_DIR" "$BRANCH"; then
    git -C "$INSTALL_DIR" pull --quiet origin "$BRANCH"
  fi

  # Capture post-update version
  if [[ -f "${INSTALL_DIR}/VERSION" ]]; then
    post_version=$(tr -d '[:space:]' < "${INSTALL_DIR}/VERSION")
  fi

  if [[ -n "$pre_version" && -n "$post_version" && "$pre_version" != "$post_version" ]]; then
    success "Updated from v${pre_version} → v${post_version}."
  else
    success "Already up to date at v${post_version:-${pre_version:-unknown}}."
  fi
else
  if [[ -d "$INSTALL_DIR" ]]; then
    error "${INSTALL_DIR} exists but is not a git repo. Remove it first or set FMAPI_HOME."
    exit 1
  fi
  info "Cloning to ${DIM}${INSTALL_DIR}${RESET}..."
  git clone --quiet "$REPO_URL" "$INSTALL_DIR"
  _checkout_ref "$INSTALL_DIR" "$BRANCH"
  success "Installed."
fi

# ── Verify ───────────────────────────────────────────────────────────────────
# Verify the Python package exists
if [[ ! -f "${INSTALL_DIR}/pyproject.toml" ]]; then
  error "Installation verification failed: pyproject.toml not found in ${INSTALL_DIR}."
  exit 1
fi

local_version="unknown"
if [[ -f "${INSTALL_DIR}/VERSION" ]]; then
  local_version=$(tr -d '[:space:]' < "${INSTALL_DIR}/VERSION")
fi

# ── Install uv if not available ──────────────────────────────────────────────
if command -v uv &>/dev/null; then
  success "uv already installed."
else
  info "Installing uv (Python package manager) ..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Ensure uv is on PATH for this session
  export PATH="$HOME/.local/bin:$PATH"
  if command -v uv &>/dev/null; then
    success "uv installed."
  else
    error "Failed to install uv. Install manually: https://docs.astral.sh/uv/"
    exit 1
  fi
fi

# ── Python info ──────────────────────────────────────────────────────────────
python_info=$(uv python list --only-installed 2>/dev/null | head -1 || true)
if [[ -n "$python_info" ]]; then
  info "Python available: ${DIM}${python_info}${RESET}"
else
  info "No Python installation detected — uv will download one automatically."
fi

# ── Install CLI as global tool ───────────────────────────────────────────────
info "Installing setup-fmapi-claudecode CLI ..."
# Ensure uv tool bin is on PATH for this session
UV_TOOL_BIN_DIR="$(uv tool dir --bin 2>/dev/null || echo "$HOME/.local/bin")"
export PATH="${UV_TOOL_BIN_DIR}:$PATH"

uv tool install "$INSTALL_DIR" --force --reinstall --no-cache --quiet 2>/dev/null || \
  uv tool install "$INSTALL_DIR" --force --reinstall --no-cache
success "CLI installed globally as setup-fmapi-claudecode."

# Check if the tool bin directory is on the user's default PATH
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$UV_TOOL_BIN_DIR" 2>/dev/null || \
   ! command -v setup-fmapi-claudecode &>/dev/null; then
  echo ""
  echo -e "  ${RED}${BOLD}NOTE:${RESET} ${UV_TOOL_BIN_DIR} may not be on your PATH."
  echo -e "  Add it to your shell profile to use the CLI in new terminals:"
  echo ""
  echo -e "    ${CYAN}echo 'export PATH=\"${UV_TOOL_BIN_DIR}:\$PATH\"' >> ~/.zshrc${RESET}"
  echo -e "    ${DIM}(or ~/.bashrc for bash)${RESET}"
  echo ""
fi

# ── Print next steps ─────────────────────────────────────────────────────────
echo ""
success "fmapi-codingagent-setup v${local_version} installed to ${INSTALL_DIR}"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo ""
echo -e "  Run setup for Claude Code:"
echo -e "    ${CYAN}setup-fmapi-claudecode${RESET}"

echo ""
echo -e "  Run non-interactive setup (example):"
echo -e "    ${CYAN}setup-fmapi-claudecode --host https://your-workspace.cloud.databricks.com${RESET}"

echo ""
echo -e "  Update to the latest version:"
echo -e "    ${CYAN}setup-fmapi-claudecode self-update${RESET}"

# ── Reinstall hint (update + existing config) ─────────────────────────────────
if [[ "$IS_UPDATE" == true ]] && _has_fmapi_config; then
  echo ""
  echo -e "  ${BOLD}Already configured?${RESET} If needed, re-run refresh manually:"
  echo -e "    ${CYAN}setup-fmapi-claudecode reinstall${RESET}"
fi

# ── Installation files hint ───────────────────────────────────────────────────
echo ""
echo -e "  ${DIM}Installation files:${RESET}"
echo -e "    ${DIM}Repository clone  ${INSTALL_DIR}${RESET}"
echo -e "    ${DIM}CLI tool          ${UV_TOOL_BIN_DIR}/setup-fmapi-claudecode${RESET}"
echo ""
echo -e "  ${DIM}To uninstall everything later:${RESET}"
echo -e "    ${DIM}setup-fmapi-claudecode uninstall${RESET}"

echo ""
