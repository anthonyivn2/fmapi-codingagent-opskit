"""Tests for install.sh behavior and compatibility guards."""

from __future__ import annotations

from pathlib import Path


def _install_script_text() -> str:
    return (Path(__file__).resolve().parents[1] / "install.sh").read_text()


def test_install_script_uses_cache_busting_tool_install():
    script = _install_script_text()
    assert 'uv tool install "$INSTALL_DIR" --force --reinstall --no-cache' in script, (
        "install.sh should force a fresh uv tool reinstall to avoid stale cached helper templates"
    )


def test_install_script_does_not_execute_setup_command():
    script = _install_script_text()
    assert "if setup-fmapi-claudecode" not in script, (
        "install.sh should not execute setup-fmapi-claudecode during install/update"
    )
    assert "exec setup-fmapi-claudecode" not in script, (
        "install.sh should not exec setup-fmapi-claudecode automatically"
    )


def test_install_script_does_not_offer_agent_flag():
    script = _install_script_text()
    assert "--agent" not in script, "install.sh should not include an auto-run --agent mode"


def test_install_script_clones_without_branch_checkout_warning_for_tags():
    script = _install_script_text()
    assert 'git clone --quiet "$REPO_URL" "$INSTALL_DIR"' in script, (
        "install.sh should clone without --branch so annotated tag refs "
        "do not emit checkout warnings"
    )
    assert 'git clone --quiet --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"' not in script, (
        "install.sh should not use --branch during clone because "
        "annotated tags are not direct commits"
    )


def test_install_script_fetches_tag_refspec_before_checkout():
    script = _install_script_text()
    assert 'git -C "$repo" fetch --quiet origin "+refs/tags/$ref:refs/tags/$ref"' in script, (
        "install.sh should force-refresh local tags from remote so updates do not fail when "
        "release tags are moved"
    )
