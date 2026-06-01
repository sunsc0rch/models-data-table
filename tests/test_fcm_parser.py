"""Tests for the free-coding-models sources.js parser (core.fcm_updater._parse)."""
from core.fcm_updater import _parse


# Minimal but realistic sources.js snippet covering 2 providers and 4 models.
# Note: ``models:`` references the unquoted variable name.
_SAMPLE = """
export const groqModels = [
  ['llama-3.3-70b-versatile', 'Llama 3.3 70B'],
  ['llama-3.1-8b-instant', 'Llama 3.1 8B'],
];

export const cerebrasModels = [
  ['llama-3.3-70b', 'Llama 3.3 70B'],
  ['qwen-3-32b', 'Qwen3 32B'],
];

export const sources = {
  groq: {
    name: 'Groq',
    models: groqModels,
  },
  cerebras: {
    name: 'Cerebras',
    models: cerebrasModels,
  },
  gemini: {
    name: 'Google AI Studio',
    models: geminiModels,
  },
};
"""


def test_parse_returns_both_providers_and_ids():
    providers, ids = _parse(_SAMPLE)
    assert "Llama 3.3 70B" in providers
    assert "Qwen3 32B" in providers


def test_parse_extracts_api_ids_per_provider():
    providers, ids = _parse(_SAMPLE)
    assert ids["Llama 3.3 70B"]["Groq"] == "llama-3.3-70b-versatile"
    assert ids["Llama 3.3 70B"]["Cerebras"] == "llama-3.3-70b"
    assert ids["Qwen3 32B"]["Cerebras"] == "qwen-3-32b"


def test_parse_groups_models_by_label():
    providers, ids = _parse(_SAMPLE)
    # Llama 3.3 70B appears in both Groq and Cerebras
    assert sorted(providers["Llama 3.3 70B"]) == ["Cerebras", "Groq"]


def test_parse_skips_listed_providers():
    """Providers in the SKIP set (gemini, opencode-zen) are excluded."""
    providers, ids = _parse(_SAMPLE)
    assert "Qwen3 32B" in providers
    # gemini provider is skipped, so no gemini provider entry should exist anywhere
    all_provider_names = {p for plist in providers.values() for p in plist}
    assert "Google AI Studio" not in all_provider_names


def test_parse_handles_empty_sources():
    providers, ids = _parse("export const nothing = 'hi';")
    assert providers == {}
    assert ids == {}


def test_parse_id_does_not_overwrite_with_duplicate():
    """If the same (label, provider) appears twice, keep the first api_id."""
    text = """
    export const x = [
      ['first-id', 'Model A'],
      ['second-id', 'Model A'],
    ];
    export const sources = {
      test: { name: 'Test', models: x },
    };
    """
    providers, ids = _parse(text)
    assert ids["Model A"]["Test"] == "first-id"


def test_fill_free_providers_normalizes_model_id_keys_to_opencode():
    """FCM stores 'Groq'; record.model_ids should store 'groq' to match api_provider."""
    from core.free_providers_data import FCM_MODEL_IDS, FCM_PROVIDERS
    from core.models import ModelRecord
    from core.static_data import _fill_free_providers, _rebuild_fcm_cache

    FCM_PROVIDERS.clear()
    FCM_PROVIDERS["Llama 3.3 70B"] = ["Groq"]
    FCM_MODEL_IDS.clear()
    FCM_MODEL_IDS["Llama 3.3 70B"] = {"Groq": "llama-3.3-70b-versatile"}
    _rebuild_fcm_cache()

    r = ModelRecord(name="Llama 3.3 70B")
    _fill_free_providers(r)
    assert r.model_ids.get("groq") == "llama-3.3-70b-versatile"
    assert "Groq" not in r.model_ids
