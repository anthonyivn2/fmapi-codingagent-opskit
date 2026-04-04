"""Tests for Codex skill registration and deregistration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from fmapi_opskit.agents.codex import SKILL_NAMES, CodexAdapter


@pytest.fixture
def codex_adapter() -> CodexAdapter:
    return CodexAdapter()


def test_codex_skill_names_match_claudecode():
    """Codex and Claude Code should have the same skill names."""
    from fmapi_opskit.agents.claudecode import SKILL_NAMES as CLAUDE_SKILL_NAMES

    assert set(SKILL_NAMES) == set(CLAUDE_SKILL_NAMES)
    assert len(SKILL_NAMES) == 6


def test_codex_register_plugin_copies_skills(tmp_path, codex_adapter):
    """register_plugin should copy skills from skills-codex/ to ~/.agents/skills/."""
    # Create source skill
    source = tmp_path / "repo" / "skills-codex" / "fmapi-codingagent-status"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: fmapi-codingagent-status\n---\nTest skill\n")

    home = tmp_path / "home"
    home.mkdir()

    with patch("fmapi_opskit.agents.codex.Path.home", return_value=home):
        codex_adapter.register_plugin(tmp_path / "repo")

    target = home / ".agents" / "skills" / "fmapi-codingagent-status" / "SKILL.md"
    assert target.is_file()
    assert "Test skill" in target.read_text()


def test_codex_deregister_plugin_removes_skills(tmp_path, codex_adapter):
    """deregister_plugin should remove skill directories from ~/.agents/skills/."""
    home = tmp_path / "home"
    skills_dir = home / ".agents" / "skills"

    # Create installed skills
    for name in SKILL_NAMES:
        skill_path = skills_dir / name
        skill_path.mkdir(parents=True)
        (skill_path / "SKILL.md").write_text(f"---\nname: {name}\n---\n")

    with patch("fmapi_opskit.agents.codex.Path.home", return_value=home):
        codex_adapter.deregister_plugin()

    # All should be removed
    for name in SKILL_NAMES:
        assert not (skills_dir / name).exists()


def test_codex_register_plugin_no_source_dir(tmp_path, codex_adapter):
    """register_plugin should handle missing skills-codex/ gracefully."""
    # No skills-codex/ directory exists
    codex_adapter.register_plugin(tmp_path)
    # Should not raise


def test_codex_register_plugin_preserves_existing_skills(tmp_path, codex_adapter):
    """register_plugin should not remove other skills in ~/.agents/skills/."""
    home = tmp_path / "home"
    skills_dir = home / ".agents" / "skills"

    # Create an existing non-FMAPI skill
    other_skill = skills_dir / "my-custom-skill"
    other_skill.mkdir(parents=True)
    (other_skill / "SKILL.md").write_text("Custom skill content")

    # Create source skill
    source = tmp_path / "repo" / "skills-codex" / "fmapi-codingagent-status"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("---\nname: fmapi-codingagent-status\n---\n")

    with patch("fmapi_opskit.agents.codex.Path.home", return_value=home):
        codex_adapter.register_plugin(tmp_path / "repo")

    # Custom skill should still exist
    assert (other_skill / "SKILL.md").read_text() == "Custom skill content"
