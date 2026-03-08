"""Tests for interactive prompt helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fmapi_opskit.ui import prompts


class _DummyConsole:
    def print(self, *_args, **_kwargs) -> None:
        return None


class _FakeMenu:
    shown_result: int | None = None
    chosen_accept_key: str | None = None
    search_text: str | None = None
    last_entries: list[str] = []
    last_kwargs: dict = {}

    def __init__(self, entries: list[str], **kwargs) -> None:
        _FakeMenu.last_entries = entries
        _FakeMenu.last_kwargs = kwargs
        self._chosen_accept_key = _FakeMenu.chosen_accept_key
        self._search = SimpleNamespace(search_text=_FakeMenu.search_text)

    def show(self) -> int | None:
        return _FakeMenu.shown_result


def test_select_or_input_uses_hint_not_selectable_entry(monkeypatch):
    monkeypatch.setattr(prompts, "get_console", lambda: _DummyConsole())
    monkeypatch.setattr(prompts, "TerminalMenu", _FakeMenu)

    _FakeMenu.shown_result = 0
    _FakeMenu.chosen_accept_key = "enter"
    _FakeMenu.search_text = None

    result = prompts.select_or_input("Model", ["m1", "m2"], "", "m2", False)

    assert result == "m1"
    assert _FakeMenu.last_entries == ["  m1", "  m2"]
    assert _FakeMenu.last_kwargs["search_key"] is None
    assert _FakeMenu.last_kwargs["show_search_hint"] is False


def test_select_or_input_returns_typed_custom_value(monkeypatch):
    monkeypatch.setattr(prompts, "get_console", lambda: _DummyConsole())
    monkeypatch.setattr(prompts, "TerminalMenu", _FakeMenu)

    _FakeMenu.shown_result = None
    _FakeMenu.chosen_accept_key = "enter"
    _FakeMenu.search_text = "databricks-my-custom-model"

    result = prompts.select_or_input("Model", ["m1", "m2"], "", "", False)

    assert result == "databricks-my-custom-model"


def test_select_or_input_cancel_still_exits(monkeypatch):
    monkeypatch.setattr(prompts, "get_console", lambda: _DummyConsole())
    monkeypatch.setattr(prompts, "TerminalMenu", _FakeMenu)

    _FakeMenu.shown_result = None
    _FakeMenu.chosen_accept_key = None
    _FakeMenu.search_text = None

    with pytest.raises(SystemExit) as exc_info:
        prompts.select_or_input("Model", ["m1"], "", "", False)

    assert exc_info.value.code == 130
