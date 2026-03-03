"""Tests for template rendering."""

from __future__ import annotations

import stat

import pytest

from fmapi_opskit.templates.renderer import TemplateError, render_template


@pytest.fixture
def template_file(tmp_path):
    """Create a simple template file with __KEY__ style placeholders."""
    p = tmp_path / "test.sh.template"
    p.write_text("#!/bin/sh\nPROFILE=__PROFILE__\nHOST=__HOST__\n")
    return p


def test_render_substitutes_all_placeholders(template_file, tmp_path):
    output = tmp_path / "output.sh"
    render_template(
        template_path=template_file,
        output_path=output,
        placeholders={"PROFILE": "test-profile", "HOST": "https://example.com"},
    )
    content = output.read_text()
    assert "PROFILE=test-profile" in content
    assert "HOST=https://example.com" in content


def test_render_sets_executable_permissions(template_file, tmp_path):
    output = tmp_path / "output.sh"
    render_template(
        template_path=template_file,
        output_path=output,
        placeholders={"PROFILE": "p", "HOST": "h"},
        mode=0o700,
    )
    mode = output.stat().st_mode
    assert mode & stat.S_IXUSR  # owner executable


def test_render_detects_unsubstituted_placeholders(template_file, tmp_path):
    output = tmp_path / "output.sh"
    with pytest.raises(TemplateError, match="[Uu]nsubstituted"):
        render_template(
            template_path=template_file,
            output_path=output,
            placeholders={"PROFILE": "p"},  # Missing HOST
        )


def test_render_creates_parent_directories(template_file, tmp_path):
    output = tmp_path / "deep" / "nested" / "output.sh"
    render_template(
        template_path=template_file,
        output_path=output,
        placeholders={"PROFILE": "p", "HOST": "h"},
    )
    assert output.is_file()


def test_render_no_placeholders_in_output(template_file, tmp_path):
    output = tmp_path / "output.sh"
    render_template(
        template_path=template_file,
        output_path=output,
        placeholders={"PROFILE": "p", "HOST": "h"},
    )
    content = output.read_text()
    assert "__PROFILE__" not in content
    assert "__HOST__" not in content


def test_render_template_not_found(tmp_path):
    with pytest.raises(TemplateError, match="not found"):
        render_template(
            template_path=tmp_path / "nonexistent.template",
            output_path=tmp_path / "out.sh",
            placeholders={},
        )
