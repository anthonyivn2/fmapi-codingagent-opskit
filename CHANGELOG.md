# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-04-09

### Fixed

- Used Databricks CLI force-refresh support during helper-driven token refresh when available.
- Resolved relative `apiKeyHelper` paths correctly during Codex config discovery.

### Changed

- Pinned Databricks CLI installs to `0.296.0`.

## [0.1.2] - 2026-04-04

### Added

- Added OpenAI Codex support with a dedicated Codex adapter and `setup-fmapi-codex` entrypoint.
- Added TOML-based Codex configuration management for provider/profile setup, FMAPI auth command wiring, and uninstall cleanup.
- Added Codex skill installation support by copying FMAPI skills into `~/.agents/skills/`.
- Added configurable Codex provider IDs via `--provider-id`.
- Added Codex CLI minimum-version detection and upgrade checks during setup.
- Added a repository-level `AGENTS.md` with guidance for Codex and other coding agents.
- Added test coverage for Codex adapters, Codex skills, TOML settings management, host validation, and related setup paths.

### Changed

- Updated the setup workflow and config discovery logic to support both Claude Code and Codex through a shared adapter-driven architecture.
- Expanded documentation in `README.md` and `CLAUDE.md` to describe Codex support and current repository behavior.
- Improved uninstall behavior to better clean up FMAPI-managed configuration while preserving unrelated user settings.
- Improved smoke-test handling and setup writer behavior for multi-agent support.
- Ignored `.worktrees/` and macOS `.DS_Store` files in `.gitignore` to keep the working tree clean.
- Updated dependency lock metadata in `uv.lock`.

### Fixed

- Fixed host validation by rejecting invalid URL characters earlier in setup.
- Hardened shell template generation and helper-script handling around host values.
- Hardened helper reauth flow and made TTL expiry buffering configurable.
- Improved uninstall and smoke-test robustness across setup flows.

## [0.1.1] - 2026-03-08

### Fixed

- Fixed 403 errors caused by near-expiry OAuth tokens being discarded instead of refreshed.
- Fixed token refresh to preserve the refresh token for silent OAuth renewal.
- Fixed annotated Git tag checkout warnings in the bootstrap installer.

### Changed

- Replaced age-based token cache eviction (240s max-age) with JWT expiry-based validation (300s buffer).
- Simplified `fmapi-key-helper.sh` by removing headless/WSL branching and `pkill`-based process handling.
- Updated `doctor` and `status` dashboards to report token freshness from actual JWT expiry.
- Cleaned up test suite: removed obsolete tests, added prompt and model-selection coverage (123 → 108 tests).

### Added

- Interactive model selection during setup now lists available workspace endpoints with a custom entry option.

## [0.1.0] - 2025-05-01

### Added

- One-command setup via `bash <(curl ...)` bootstrap installer
- Claude Code adapter with full settings.json management
- Automatic OAuth token management via `fmapi-key-helper.sh` helper script
- Auth pre-check hooks for `SubagentStart` and `UserPromptSubmit` events
- Non-interactive setup mode with `--host`, `--config`, and `--config-url` flags
- AI Gateway v2 (beta) support with `--ai-gateway` and `--workspace-id` flags
- Config file loading from local JSON or remote HTTPS URL
- `status` command — configuration health dashboard
- `doctor` command — 10-category diagnostic checks with actionable fix suggestions
- `reauth` command — OAuth session re-authentication
- `list-models` command — workspace serving endpoint listing
- `validate-models` command — per-model readiness validation
- `reinstall` command — re-run setup with saved configuration
- `self-update` command — git pull and uv tool reinstall
- `uninstall` command — clean artifact removal preserving non-FMAPI settings
- `install-skills` / `uninstall-skills` — manage six plugin slash commands
- Six Claude Code slash command skills (status, reauth, setup, doctor, list-models, validate-models)
- WSL (Windows Subsystem for Linux) experimental support
- Dry-run mode showing planned changes without writing files
- Legacy PAT cleanup and migration from prior installations
- Stale OAuth token recovery with automatic cache repair

[Unreleased]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/releases/tag/v0.1.0
