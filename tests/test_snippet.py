"""Tests for the opencode.json snippet builder and provider resolver."""
import json
import pytest

from core.models import ModelRecord
from core.opencode_providers import (
    PROVIDER_TO_OPENCODE_KEY,
    resolve_api_provider,
    resolve_model_id,
)
from ui.table_view import _build_snippet


# ---------------------------------------------------------------------------
# resolve_api_provider
# ---------------------------------------------------------------------------

def test_resolve_openrouter_from_free_providers():
    r = ModelRecord(name="x", free_providers=["OpenRouter", "Groq"])
    assert resolve_api_provider(r) == "openrouter"


def test_resolve_takes_first_from_free_providers():
    r = ModelRecord(name="x", free_providers=["Groq", "OpenRouter"])
    assert resolve_api_provider(r) == "groq"


def test_resolve_fallback_to_openrouter_when_id_set():
    r = ModelRecord(name="x", openrouter_id="some/model:free")
    assert resolve_api_provider(r) == "openrouter"


def test_resolve_fallback_skipped_when_free_provider_known():
    r = ModelRecord(
        name="x",
        free_providers=["UnknownProvider"],
        openrouter_id="some/model:free",
    )
    assert resolve_api_provider(r) == "openrouter"


def test_resolve_returns_none_for_unknown_free_provider():
    r = ModelRecord(name="x", free_providers=["TotallyMadeUpProvider"])
    assert resolve_api_provider(r) is None


def test_resolve_returns_none_for_empty_record():
    r = ModelRecord(name="x")
    assert resolve_api_provider(r) is None


def test_resolve_all_known_mappings():
    """Every provider name in PROVIDER_PRIORITY should map to a non-empty key."""
    from core.free_providers_data import PROVIDER_PRIORITY
    for name in PROVIDER_PRIORITY:
        r = ModelRecord(name="x", free_providers=[name])
        key = resolve_api_provider(r)
        assert key, f"Provider {name!r} did not resolve to a key"
        assert key == key.lower(), f"Key for {name!r} should be lowercase: {key}"


# ---------------------------------------------------------------------------
# resolve_model_id
# ---------------------------------------------------------------------------

def test_model_id_uses_model_ids_for_provider():
    r = ModelRecord(
        name="Llama 3.3 70B",
        model_ids={"groq": "llama-3.3-70b-versatile"},
    )
    model_id, source = resolve_model_id(r, "groq")
    assert model_id == "llama-3.3-70b-versatile"
    assert source == "model_ids"


def test_model_id_openrouter_uses_model_ids_first():
    r = ModelRecord(
        name="x",
        openrouter_id="openrouter/fallback:free",
        model_ids={"openrouter": "specific/openrouter-id:free"},
    )
    model_id, source = resolve_model_id(r, "openrouter")
    assert model_id == "specific/openrouter-id:free"
    assert source == "model_ids"


def test_model_id_openrouter_falls_back_to_openrouter_id():
    r = ModelRecord(name="x", openrouter_id="openrouter/id:free")
    model_id, source = resolve_model_id(r, "openrouter")
    assert model_id == "openrouter/id:free"
    assert source == "openrouter_id"


def test_model_id_groq_without_model_ids_falls_back():
    r = ModelRecord(name="Llama 3.3 70B", openrouter_id="meta/llama:free")
    model_id, source = resolve_model_id(r, "groq")
    assert model_id == "Llama 3.3 70B:free"
    assert source == "fallback"


def test_model_id_no_api_provider_falls_back_to_openrouter_id():
    r = ModelRecord(name="x", openrouter_id="openrouter/id:free")
    model_id, source = resolve_model_id(r, None)
    assert model_id == "openrouter/id:free"
    assert source == "openrouter_id"


def test_model_id_no_provider_no_id_uses_name_with_free():
    r = ModelRecord(name="Custom Model")
    model_id, source = resolve_model_id(r, None)
    assert model_id == "Custom Model:free"
    assert source == "fallback"


def test_model_id_picks_correct_provider_among_many():
    r = ModelRecord(
        name="x",
        model_ids={
            "openrouter": "or-id:free",
            "groq":       "groq-id",
            "cerebras":   "cer-id",
        },
    )
    assert resolve_model_id(r, "openrouter")[0] == "or-id:free"
    assert resolve_model_id(r, "groq")[0] == "groq-id"
    assert resolve_model_id(r, "cerebras")[0] == "cer-id"


# ---------------------------------------------------------------------------
# _build_snippet
# ---------------------------------------------------------------------------

def _sample(**overrides) -> ModelRecord:
    defaults = dict(
        name="Devstral Small",
        openrouter_id="mistralai/devstral-small-2505:free",
        openrouter_name="Devstral Small",
        context_k=131,
        output_tokens=8192,
        free_providers=["OpenRouter"],
    )
    defaults.update(overrides)
    return ModelRecord(**defaults)


def _snippet(record, **kwargs) -> str:
    """Helper: extract just the snippet text from _build_snippet's tuple."""
    snippet, _ = _build_snippet(record, **kwargs)
    return snippet


def test_snippet_uses_openrouter_id_when_available():
    snippet = _snippet(_sample(), api_provider="openrouter")
    assert '"mistralai/devstral-small-2505:free"' in snippet


def test_snippet_uses_model_ids_for_non_openrouter_provider():
    r = _sample(
        name="Llama 3.3 70B",
        openrouter_id=None,
        model_ids={"groq": "llama-3.3-70b-versatile"},
    )
    snippet = _snippet(r, api_provider="groq")
    assert '"llama-3.3-70b-versatile"' in snippet
    assert '"Llama 3.3 70B:free"' not in snippet


def test_snippet_prefers_model_ids_over_openrouter_id():
    r = _sample(
        model_ids={"openrouter": "specific/id:free"},
        openrouter_id="generic/id:free",
    )
    snippet = _snippet(r, api_provider="openrouter")
    assert '"specific/id:free"' in snippet
    assert '"generic/id:free"' not in snippet


def test_snippet_falls_back_to_name_free_suffix():
    r = _sample(openrouter_id=None, model_ids={})
    snippet = _snippet(r)
    assert '"Devstral Small:free"' in snippet


def test_snippet_returns_id_source_model_ids():
    r = _sample(model_ids={"openrouter": "specific/id:free"})
    _, source = _build_snippet(r, api_provider="openrouter")
    assert source == "model_ids"


def test_snippet_returns_id_source_openrouter_id():
    r = _sample()  # openrouter_id set
    _, source = _build_snippet(r, api_provider="openrouter")
    assert source == "openrouter_id"


def test_snippet_returns_id_source_fallback():
    r = _sample(openrouter_id=None, model_ids={})
    _, source = _build_snippet(r, api_provider="groq")
    assert source == "fallback"


def test_snippet_default_indent_is_8_spaces():
    snippet = _snippet(_sample(), api_provider="openrouter")
    first_line = snippet.split("\n", 1)[0]
    assert first_line.startswith("        ")
    assert first_line.startswith(" " * 8) and not first_line.startswith(" " * 9)


def test_snippet_nested_indent_10_and_12():
    snippet = _snippet(_sample(), api_provider="openrouter")
    lines = snippet.split("\n")
    name_line = next(line for line in lines if '"name"' in line)
    context_line = next(line for line in lines if '"context"' in line)
    assert name_line.startswith(" " * 10), f"expected 10 spaces, got: {name_line!r}"
    assert context_line.startswith(" " * 12), f"expected 12 spaces, got: {context_line!r}"


def test_snippet_custom_indent():
    snippet = _snippet(_sample(), api_provider="openrouter", indent=4)
    first_line = snippet.split("\n", 1)[0]
    assert first_line.startswith("    ") and not first_line.startswith("     ")


def test_snippet_trailing_comma_default():
    snippet = _snippet(_sample(), api_provider="openrouter")
    assert snippet.rstrip().endswith(",")


def test_snippet_no_trailing_comma():
    snippet = _snippet(_sample(), api_provider="openrouter", trailing_comma=False)
    assert snippet.rstrip().endswith("}")
    assert not snippet.rstrip().endswith(",}")


def test_snippet_uses_openrouter_name_for_display():
    snippet = _snippet(_sample(openrouter_name="Devstral 2"), api_provider="openrouter")
    assert '"name": "Devstral 2"' in snippet


def test_snippet_falls_back_to_name_for_display():
    r = _sample(name="Llama 3", openrouter_name=None, openrouter_id=None, model_ids={})
    snippet = _snippet(r)
    assert '"name": "Llama 3"' in snippet


def test_snippet_context_defaults_to_128k():
    r = _sample(context_k=None)
    snippet = _snippet(r, api_provider="openrouter")
    assert '"context": 128000' in snippet


def test_snippet_output_defaults_to_8k():
    r = _sample(output_tokens=None)
    snippet = _snippet(r, api_provider="openrouter")
    assert '"output": 8192' in snippet


def test_snippet_context_uses_value():
    snippet = _snippet(_sample(context_k=200), api_provider="openrouter")
    assert '"context": 200000' in snippet


def test_snippet_output_uses_value():
    snippet = _snippet(_sample(output_tokens=4096), api_provider="openrouter")
    assert '"output": 4096' in snippet


def test_snippet_is_valid_json():
    snippet = _snippet(_sample(), api_provider="openrouter")
    wrapped = "{" + snippet.rstrip(",") + "}"
    parsed = json.loads(wrapped)
    [(_, value)] = parsed.items()
    assert value["name"] == "Devstral Small"
    assert value["limit"]["context"] == 131000
    assert value["limit"]["output"] == 8192


def test_snippet_format_matches_opencode_json():
    """Full integration: the snippet should slot into opencode.json verbatim."""
    snippet = _snippet(_sample(), api_provider="openrouter")
    assert snippet == (
        '        "mistralai/devstral-small-2505:free": {\n'
        '          "name": "Devstral Small",\n'
        '          "limit": {\n'
        '            "context": 131000,\n'
        '            "output": 8192\n'
        '          }\n'
        '        },'
    )
