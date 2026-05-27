import json
import pytest
import respx
import httpx
from scrapers.artificialanalysis import ArtificialAnalysisScraper

URL = "https://artificialanalysis.ai/leaderboards/models"

MODELS = [
    {
        "id": "aaa",
        "name": "Claude Sonnet 4.5",
        "modelCreatorName": "Anthropic",
        "contextWindowTokens": 200000,
        "totalParameters": 200,
        "deprecated": False,
        "inputModalityText": True,
        "outputModalityText": True,
        "inputModalityImage": False,
        "outputModalityImage": False,
        "outputModalityVideo": False,
        "outputModalitySpeech": False,
    },
    {
        "id": "bbb",
        "name": "Gemini 2.5 Pro",
        "modelCreatorName": "Google",
        "contextWindowTokens": 1000000,
        "totalParameters": None,
        "deprecated": False,
        "inputModalityText": True,
        "outputModalityText": True,
        "inputModalityImage": True,
        "outputModalityImage": False,
        "outputModalityVideo": False,
        "outputModalitySpeech": False,
    },
    {
        "id": "ccc",
        "name": "DALL-E 3",
        "modelCreatorName": "OpenAI",
        "contextWindowTokens": None,
        "totalParameters": None,
        "deprecated": False,
        "inputModalityText": True,
        "outputModalityText": False,
        "inputModalityImage": False,
        "outputModalityImage": True,
        "outputModalityVideo": False,
        "outputModalitySpeech": False,
    },
    {
        "id": "ddd",
        "name": "OldModel",
        "modelCreatorName": "SomeCo",
        "contextWindowTokens": 4000,
        "totalParameters": 7,
        "deprecated": True,
        "inputModalityText": True,
        "outputModalityText": True,
        "inputModalityImage": False,
        "outputModalityImage": False,
        "outputModalityVideo": False,
        "outputModalitySpeech": False,
    },
]

RSC_PAYLOAD = json.dumps(
    f'32:["$","div",null,{{"className":"container","children":[["$","$L33",null,{{"models":{json.dumps(MODELS)},"other":"data"}}]]}}]'
)
SAMPLE_HTML = f'<html><body><script>self.__next_f.push([1,{RSC_PAYLOAD}])</script></body></html>'


@pytest.mark.asyncio
async def test_aa_extracts_text_models():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, err = await scraper.fetch()

    assert err is None
    names = [r.name for r in records]
    assert "Claude Sonnet 4.5" in names
    assert "Gemini 2.5 Pro" in names


@pytest.mark.asyncio
async def test_aa_excludes_image_output_models():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, _ = await scraper.fetch()

    names = [r.name for r in records]
    assert "DALL-E 3" not in names


@pytest.mark.asyncio
async def test_aa_excludes_deprecated():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, _ = await scraper.fetch()

    names = [r.name for r in records]
    assert "OldModel" not in names


@pytest.mark.asyncio
async def test_aa_extracts_provider_and_params():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, _ = await scraper.fetch()

    by_name = {r.name: r for r in records}
    assert by_name["Claude Sonnet 4.5"].provider == "Anthropic"
    assert by_name["Claude Sonnet 4.5"].params_b == 200.0
    assert by_name["Claude Sonnet 4.5"].context_k == 200
    assert by_name["Gemini 2.5 Pro"].params_b is None
    assert by_name["Gemini 2.5 Pro"].context_k == 1000


@pytest.mark.asyncio
async def test_aa_error_on_failure():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(500))
        scraper = ArtificialAnalysisScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is not None
