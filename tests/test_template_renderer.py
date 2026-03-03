"""Tests for template rendering."""

from __future__ import annotations

import os

import pytest

from fmapi_opskit.templates.renderer import TemplateError, render_template


def _make_template(tmp_path, content: str, name: str = "test.template"):
    p = tmp_path / name
    p.write_text(content)
    return p


def test_substitutes_all_placeholders(tmp_path):
    tpl = _make_template(tmp_path, "host=__HOST__ profile=__PROFILE__")
    out = tmp_path / "output.sh"
    render_template(tpl, out, {"HOST": "example.com", "PROFILE": "dev"})
    content = out.read_text()
    assert "example.com" in content, f"Substituted value 'example.com' not found in: {content}"
    assert "dev" in content, f"Substituted value 'dev' not found in: {content}"
    assert "__HOST__" not in content, f"Placeholder __HOST__ should be replaced, got: {content}"
    assert "__PROFILE__" not in content, (
        f"Placeholder __PROFILE__ should be replaced, got: {content}"
    )


def test_missing_template_raises(tmp_path):
    missing = tmp_path / "nope.template"
    with pytest.raises(TemplateError, match="not found"):
        render_template(missing, tmp_path / "out.sh", {})


def test_unsubstituted_placeholders_raises(tmp_path):
    tpl = _make_template(tmp_path, "val=__HOST__ extra=__MISSING__")
    with pytest.raises(TemplateError, match="Unsubstituted"):
        render_template(tpl, tmp_path / "out.sh", {"HOST": "ok"})


def test_output_has_correct_permissions(tmp_path):
    tpl = _make_template(tmp_path, "content=__KEY__")
    out = tmp_path / "script.sh"
    render_template(tpl, out, {"KEY": "val"}, mode=0o700)
    actual_mode = os.stat(out).st_mode & 0o777
    assert actual_mode == 0o700, f"Expected permissions 0o700, got {oct(actual_mode)}"


def test_creates_parent_directories(tmp_path):
    tpl = _make_template(tmp_path, "data=__KEY__")
    out = tmp_path / "deep" / "nested" / "output.sh"
    render_template(tpl, out, {"KEY": "val"})
    assert out.is_file(), f"Output file should be created at {out} with parent dirs"


def test_multiple_occurrences_replaced(tmp_path):
    tpl = _make_template(tmp_path, "first=__TOKEN__ second=__TOKEN__")
    out = tmp_path / "out.sh"
    render_template(tpl, out, {"TOKEN": "value"})
    content = out.read_text()
    assert content.count("value") == 2, (
        f"Expected 'value' to appear exactly 2 times, got {content.count('value')} in: {content}"
    )
    assert "__TOKEN__" not in content, f"Placeholder __TOKEN__ should be fully replaced: {content}"
