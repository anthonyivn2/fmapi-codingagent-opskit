# Releasing

This document describes how to create a new release of `fmapi-codingagent-opskit`.

## Version Locations

The version string must match in all three files:

| File | Format | Example |
|---|---|---|
| `VERSION` | Single line, no prefix | `0.2.0` |
| `pyproject.toml` | `version = "X.Y.Z"` in `[project]` | `version = "0.2.0"` |
| `.claude-plugin/plugin.json` | `"version": "X.Y.Z"` | `"version": "0.2.0"` |

## Versioning Policy

This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **MAJOR** — incompatible changes to CLI flags, settings format, or hook behavior
- **MINOR** — new commands, flags, or features (backward-compatible)
- **PATCH** — bug fixes, documentation, and internal improvements

> **Note:** While the version is `0.x`, minor releases may include breaking changes. Stability guarantees begin at `1.0.0`.

## Release Checklist

### 1. Create a release branch

```bash
git checkout main
git pull origin main
git checkout -b release/vX.Y.Z
```

### 2. Bump version in all three files

Update the version string in each file listed in [Version Locations](#version-locations). All three must match.

```bash
# Verify they match after editing
grep -n 'version' VERSION pyproject.toml .claude-plugin/plugin.json
```

### 3. Update CHANGELOG.md

1. Rename `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD` (use today's date)
2. Add a new empty `[Unreleased]` section above it
3. Update the comparison links at the bottom:

```markdown
[Unreleased]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/compare/vX.Y.Z...HEAD
[X.Y.Z]: https://github.com/anthonyivn2/fmapi-codingagent-opskit/compare/vPREVIOUS...vX.Y.Z
```

### 4. Run quality checks

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pytest
```

All checks must pass before proceeding.

### 5. Open a release PR

Open a pull request from `release/vX.Y.Z` into `main`. Use the **Release** PR template (`.github/PULL_REQUEST_TEMPLATE/release.md`).

```bash
gh pr create --title "Release vX.Y.Z" \
  --template release.md \
  --base main \
  --head release/vX.Y.Z
```

Get code owner approval, then merge.

### 6. Tag the merge commit

After the PR is merged, tag the merge commit on `main`:

```bash
git checkout main
git pull origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

### 7. Create a GitHub Release

1. Go to the repo's [Releases](https://github.com/anthonyivn2/fmapi-codingagent-opskit/releases) page
2. Click **Draft a new release**
3. Select the `vX.Y.Z` tag
4. Title: `vX.Y.Z`
5. Body: copy the changelog entry for this version
6. Check **Set as a pre-release** (while version is `0.x`)
7. Publish

Or via CLI:

```bash
gh release create vX.Y.Z --title "vX.Y.Z" \
  --notes "$(sed -n '/^## \[X.Y.Z\]/,/^## \[/{ /^## \[X.Y.Z\]/d; /^## \[/d; p; }' CHANGELOG.md)" \
  --prerelease
```

### 8. Verify the install

Verify the default install picks up the new release automatically:

```bash
bash <(curl -sL https://raw.githubusercontent.com/anthonyivn2/fmapi-codingagent-opskit/main/install.sh)
setup-fmapi-claudecode --version
```

Also verify pinned version install:

```bash
bash <(curl -sL https://raw.githubusercontent.com/anthonyivn2/fmapi-codingagent-opskit/main/install.sh) --version X.Y.Z
setup-fmapi-claudecode --version
```

Both should show `X.Y.Z`.

## Hotfix Process

For urgent fixes to a released version:

1. Branch from the release tag: `git checkout -b hotfix/vX.Y.Z vX.Y.Z`
2. Apply the fix and bump the **PATCH** version
3. Follow the same release checklist (steps 2–8)

## Branch Protection Setup (One-Time)

Configure these rules on `main` via **GitHub Settings > Branches > Add rule**:

1. **Branch name pattern:** `main`
2. **Require a pull request before merging**
   - Required approvals: **1**
   - Dismiss stale pull request approvals when new commits are pushed: **enabled**
   - Require review from Code Owners: **enabled**
3. **Do not restrict who can push** — leave admin bypass enabled (sole maintainer escape hatch)
4. Save changes
