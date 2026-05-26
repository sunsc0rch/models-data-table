import json
from pathlib import Path
import pytest
from core.models import ModelRecord
import core.cache as cache_mod


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "CACHE_PATH", tmp_path / "cache.json")


def test_read_returns_empty_when_no_cache():
    assert cache_mod.read() == []


def test_write_then_read_roundtrip():
    records = [
        ModelRecord(name="gpt-4o", provider="OpenAI", swe_bench_pct=72.1),
        ModelRecord(name="claude-3-5", free_providers=["OpenRouter"]),
    ]
    cache_mod.write(records)
    result = cache_mod.read()
    assert len(result) == 2
    assert result[0].name == "gpt-4o"
    assert result[0].swe_bench_pct == 72.1
    assert result[1].free_providers == ["OpenRouter"]


def test_write_skips_on_empty_list(tmp_path, monkeypatch):
    path = tmp_path / "cache.json"
    monkeypatch.setattr(cache_mod, "CACHE_PATH", path)
    cache_mod.write([])
    assert not path.exists()


def test_write_does_not_overwrite_existing_cache_with_empty(tmp_path, monkeypatch):
    path = tmp_path / "cache.json"
    monkeypatch.setattr(cache_mod, "CACHE_PATH", path)
    cache_mod.write([ModelRecord(name="existing")])
    assert path.exists()
    cache_mod.write([])
    result = cache_mod.read()
    assert len(result) == 1
