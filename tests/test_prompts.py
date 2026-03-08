"""Tests for terminal prompt rendering helpers."""

from __future__ import annotations

from fmapi_opskit.ui.prompts import prompt_prefilled_value, select_option


def test_select_option_omits_empty_descriptions(monkeypatch):
    captured: dict[str, object] = {}

    class FakeMenu:
        def __init__(self, entries, **kwargs):
            captured["entries"] = entries

        def show(self):
            return 0

    class FakeConsole:
        def print(self, *args, **kwargs):
            return None

    monkeypatch.setattr("fmapi_opskit.ui.prompts.TerminalMenu", FakeMenu)
    monkeypatch.setattr("fmapi_opskit.ui.prompts.get_console", lambda: FakeConsole())

    choice = select_option(
        "Model",
        [("endpoint-a", ""), ("Custom model name", "type your own endpoint name")],
    )

    assert choice == 0
    assert captured["entries"] == [
        "  endpoint-a",
        "  Custom model name  (type your own endpoint name)",
    ]


def test_prompt_prefilled_value_uses_prompt_default_without_readline(monkeypatch):
    class FakeConsole:
        def print(self, *args, **kwargs):
            return None

    captured: dict[str, object] = {}

    def fake_ask(prompt, default=None, console=None):
        captured["prompt"] = prompt
        captured["default"] = default
        return "user-value"

    monkeypatch.setattr("fmapi_opskit.ui.prompts.get_console", lambda: FakeConsole())
    monkeypatch.setattr("fmapi_opskit.ui.prompts.Prompt.ask", fake_ask)
    monkeypatch.setattr("fmapi_opskit.ui.prompts.readline", None)

    value = prompt_prefilled_value("Custom model name", "existing-model")

    assert value == "user-value"
    assert captured["prompt"] == "  [info]?[/info] Custom model name"
    assert captured["default"] == "existing-model"


def test_prompt_prefilled_value_prefills_input_with_readline(monkeypatch):
    class FakeConsole:
        def print(self, *args, **kwargs):
            return None

    class FakeReadline:
        def __init__(self):
            self.hook = None
            self.inserted = ""

        def insert_text(self, text):
            self.inserted = text

        def set_startup_hook(self, hook):
            self.hook = hook
            if hook is not None:
                hook()

    fake_readline = FakeReadline()

    monkeypatch.setattr("fmapi_opskit.ui.prompts.get_console", lambda: FakeConsole())
    monkeypatch.setattr("fmapi_opskit.ui.prompts.readline", fake_readline)
    monkeypatch.setattr("builtins.input", lambda _: "custom-model")

    value = prompt_prefilled_value("Custom model name", "existing-model")

    assert value == "custom-model"
    assert fake_readline.hook is None
    assert fake_readline.inserted == "existing-model"
