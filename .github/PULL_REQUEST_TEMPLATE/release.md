## Release vX.Y.Z

### Pre-merge checklist

- [ ] Version bumped in all three files and they match:
  - [ ] `VERSION`
  - [ ] `pyproject.toml` (`version = "X.Y.Z"`)
  - [ ] `.claude-plugin/plugin.json` (`"version": "X.Y.Z"`)
- [ ] `CHANGELOG.md` updated:
  - [ ] `[Unreleased]` renamed to `[X.Y.Z] - YYYY-MM-DD`
  - [ ] New empty `[Unreleased]` section added
  - [ ] Comparison links updated at bottom of file
- [ ] Quality checks pass:
  - [ ] `uv run ruff check src/ tests/`
  - [ ] `uv run ruff format --check src/ tests/`
  - [ ] `uv run pytest`

### Post-merge steps

- [ ] Tag the merge commit: `git tag -a vX.Y.Z -m "Release vX.Y.Z" && git push origin vX.Y.Z`
- [ ] Create GitHub Release from tag (mark as pre-release while `0.x`)
- [ ] Verify default install picks up new release: `bash <(curl -sL .../install.sh)`
- [ ] Verify pinned install: `bash <(curl -sL .../install.sh) --version X.Y.Z`
- [ ] Verify version: `setup-fmapi-claudecode --version` shows `X.Y.Z`
