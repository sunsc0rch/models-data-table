import pytest
import respx
import httpx
from scrapers.openrouter import OpenRouterScraper

API_URL = "https://openrouter.ai/api/v1/models"

SAMPLE_RESPONSE = {
    "data": [
        {
            "id": "mistralai/devstral-2512:free",
            "name": "Devstral 2",
            "architecture": {"modality": "text->text"},
            "context_length": 262144,
            "top_provider": {"max_completion_tokens": 8192},
        },
        {
            "id": "openai/gpt-4o",
            "name": "GPT-4o",
            "architecture": {"modality": "text+image->text"},
            "context_length": 128000,
            "top_provider": {"max_completion_tokens": 16384},
        },
        {
            "id": "stability/stable-diffusion:free",
            "name": "Stable Diffusion",
            "architecture": {"modality": "text->image"},
            "context_length": 77,
            "top_provider": {"max_completion_tokens": None},
        },
        {
            "id": "mistralai/mistral-7b-instruct:free",
            "name": "Mistral 7B",
            "architecture": {"modality": "text->text"},
            "context_length": 32768,
            "top_provider": {"max_completion_tokens": 4096},
        },
    ]
}


@pytest.mark.asyncio
async def test_openrouter_returns_free_text_models():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=SAMPLE_RESPONSE))
        scraper = OpenRouterScraper()
        records, err = await scraper.fetch()

    assert err is None
    names = [r.name for r in records]
    assert "Devstral 2" in names
    assert "Mistral 7B" in names


@pytest.mark.asyncio
async def test_openrouter_excludes_non_text_input():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=SAMPLE_RESPONSE))
        scraper = OpenRouterScraper()
        records, _ = await scraper.fetch()

    names = [r.name for r in records]
    assert "GPT-4o" not in names
    assert "Stable Diffusion" not in names


@pytest.mark.asyncio
async def test_openrouter_excludes_paid_models():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=SAMPLE_RESPONSE))
        scraper = OpenRouterScraper()
        records, _ = await scraper.fetch()

    ids = [r.openrouter_id for r in records]
    assert "openai/gpt-4o" not in ids


@pytest.mark.asyncio
async def test_openrouter_sets_context_and_output():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=SAMPLE_RESPONSE))
        scraper = OpenRouterScraper()
        records, _ = await scraper.fetch()

    devstral = next(r for r in records if r.openrouter_id == "mistralai/devstral-2512:free")
    assert devstral.context_k == 262
    assert devstral.output_tokens == 8192
    assert devstral.free_providers == ["OpenRouter"]


@pytest.mark.asyncio
async def test_openrouter_returns_error_on_failure():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(500))
        scraper = OpenRouterScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is not None
