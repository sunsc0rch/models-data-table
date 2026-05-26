from dataclasses import fields
from core.models import ModelRecord


def test_model_record_requires_name():
    r = ModelRecord(name="gpt-4o")
    assert r.name == "gpt-4o"


def test_model_record_all_optional_except_name():
    r = ModelRecord(name="x")
    assert r.provider is None
    assert r.params_b is None
    assert r.context_k is None
    assert r.output_tokens is None
    assert r.swe_bench_pct is None
    assert r.free_providers == []
    assert r.openrouter_id is None
    assert r.openrouter_name is None


def test_model_record_full():
    r = ModelRecord(
        name="devstral",
        provider="Mistral",
        params_b=22.0,
        context_k=262,
        output_tokens=8192,
        swe_bench_pct=46.8,
        free_providers=["OpenRouter"],
        openrouter_id="mistralai/devstral-2512:free",
        openrouter_name="Devstral 2",
    )
    assert r.params_b == 22.0
    assert r.swe_bench_pct == 46.8
    assert "OpenRouter" in r.free_providers
