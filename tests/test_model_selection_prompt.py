"""Tests for interactive model selection UX during setup."""

from __future__ import annotations

from fmapi_opskit.setup.gather import GatherResult, gather_config_models


def _gather_defaults() -> GatherResult:
    gather = GatherResult()
    gather.default_model = "databricks-claude-opus-4-6"
    gather.default_opus = "databricks-claude-opus-4-6"
    gather.default_sonnet = "databricks-claude-sonnet-4-6"
    gather.default_haiku = "databricks-claude-haiku-4-5"
    return gather


def test_model_selection_allows_custom_last_option(monkeypatch):
    gather = _gather_defaults()
    captured: dict[str, object] = {}

    def fake_select(prompt, options, non_interactive=False, default_index=0):
        captured["prompt"] = prompt
        captured["options"] = options
        captured["default_index"] = default_index
        return len(options) - 1  # select custom option

    def fake_prefilled_value(label, default):
        assert label == "Custom model name"
        assert default == gather.default_model
        return "my-custom-model"

    monkeypatch.setattr("fmapi_opskit.setup.gather.select_option", fake_select)
    monkeypatch.setattr("fmapi_opskit.setup.gather.prompt_prefilled_value", fake_prefilled_value)

    result = gather_config_models(
        gather,
        cli_model="",
        cli_opus="cli-opus",
        cli_sonnet="cli-sonnet",
        cli_haiku="cli-haiku",
        non_interactive=False,
        available_models=["endpoint-a", "endpoint-b"],
    )

    assert result.model == "my-custom-model"
    assert result.opus == "cli-opus"
    assert result.sonnet == "cli-sonnet"
    assert result.haiku == "cli-haiku"
    assert captured["prompt"] == "Model"
    assert captured["default_index"] == 2
    assert captured["options"] == [
        ("endpoint-a", ""),
        ("endpoint-b", ""),
        ("Custom model name", "type your own endpoint name"),
    ]


def test_model_selection_defaults_to_current_model_when_available(monkeypatch):
    gather = _gather_defaults()
    gather.default_model = "endpoint-b"

    def fake_select(prompt, options, non_interactive=False, default_index=0):
        assert prompt == "Model"
        assert options[0][0] == "endpoint-a"
        assert options[1][0] == "endpoint-b"
        assert default_index == 1
        return 0

    monkeypatch.setattr("fmapi_opskit.setup.gather.select_option", fake_select)
    monkeypatch.setattr(
        "fmapi_opskit.setup.gather.prompt_value",
        lambda label, cli_val, default, non_interactive: cli_val or default,
    )

    result = gather_config_models(
        gather,
        cli_model="",
        cli_opus="cli-opus",
        cli_sonnet="cli-sonnet",
        cli_haiku="cli-haiku",
        non_interactive=False,
        available_models=["endpoint-a", "endpoint-b"],
    )

    assert result.model == "endpoint-a"


def test_model_selection_falls_back_to_text_prompt_without_available_models(monkeypatch):
    gather = _gather_defaults()

    prompts: list[str] = []

    def fake_prompt_value(label, cli_val, default, non_interactive):
        prompts.append(label)
        return f"value-for-{label}"

    monkeypatch.setattr("fmapi_opskit.setup.gather.prompt_value", fake_prompt_value)

    result = gather_config_models(
        gather,
        cli_model="",
        cli_opus="",
        cli_sonnet="",
        cli_haiku="",
        non_interactive=False,
        available_models=[],
    )

    assert prompts == ["Model", "Opus model", "Sonnet model", "Haiku model"]
    assert result.model == "value-for-Model"
    assert result.opus == "value-for-Opus model"
    assert result.sonnet == "value-for-Sonnet model"
    assert result.haiku == "value-for-Haiku model"
