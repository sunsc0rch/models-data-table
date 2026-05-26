from core.models import ModelRecord
from core.merger import merge


def test_merge_single_list():
    records = [ModelRecord(name="gpt-4o", provider="OpenAI")]
    result = merge([records])
    assert len(result) == 1
    assert result[0].provider == "OpenAI"


def test_merge_fills_missing_fields():
    from_aa = [ModelRecord(name="Claude Sonnet 4", provider="Anthropic", params_b=200.0)]
    from_or = [ModelRecord(name="Claude Sonnet 4", context_k=200, free_providers=["OpenRouter"])]
    result = merge([from_aa, from_or])
    assert len(result) == 1
    assert result[0].provider == "Anthropic"
    assert result[0].params_b == 200.0
    assert result[0].context_k == 200
    assert "OpenRouter" in result[0].free_providers


def test_merge_fuzzy_matches_similar_names():
    from_aa = [ModelRecord(name="Devstral Small 2025", provider="Mistral")]
    from_swe = [ModelRecord(name="devstral-small-2025", swe_bench_pct=46.8)]
    result = merge([from_aa, from_swe])
    assert len(result) == 1
    assert result[0].swe_bench_pct == 46.8


def test_merge_keeps_distinct_models():
    a = [ModelRecord(name="gpt-4o")]
    b = [ModelRecord(name="claude-3-5-sonnet")]
    result = merge([a, b])
    assert len(result) == 2


def test_merge_deduplicates_free_providers():
    a = [ModelRecord(name="llama-3", free_providers=["OpenRouter"])]
    b = [ModelRecord(name="llama-3", free_providers=["OpenRouter"])]
    result = merge([a, b])
    assert result[0].free_providers.count("OpenRouter") == 1


def test_merge_empty_inputs():
    assert merge([[], []]) == []
    assert merge([]) == []


def test_merge_does_not_merge_distinct_versions():
    a = [ModelRecord(name="gpt-4")]
    b = [ModelRecord(name="gpt-4o")]
    result = merge([a, b])
    assert len(result) == 2
