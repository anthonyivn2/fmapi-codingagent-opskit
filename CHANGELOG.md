# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-03-08

### Fixed

- Hardened OAuth helper token cache and re-auth lifecycle behavior.
- Added JWT-only expiry handling for OAuth token freshness checks.
- Reduced OAuth re-auth delay in helper flow.
- Avoided annotated Git tag checkout warnings in installer tag installs.
- Fixed `_fetch_token` discarding valid near-expiry tokens (caused 403 errors in Claude Code).
- Fixed near-expiry token refresh to clear Databricks CLI token cache and force a real OAuth refresh.

### Changed

- Replaced age-based token cache eviction (240s max-age) with expiry-based validation (300s buffer).
- Updated `doctor` and `status` dashboard to report token freshness based on actual expiry instead of cache age.
- Simplified auth, doctor, reauth, and test helper internals.

### Added

- UI prompt test coverage for setup flows.
- Interactive setup model selection now lists available endpoint names and includes a final custom model option.
- Custom model entry now supports prefilled type-over input and endpoint rows omit redundant availability labels.

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

[Unreleased]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/releases/tag/v0.1.0
