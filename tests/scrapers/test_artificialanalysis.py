import pytest
import respx
import httpx
from scrapers.artificialanalysis import ArtificialAnalysisScraper

URL = "https://artificialanalysis.ai/leaderboards/models"

SAMPLE_HTML = """
<html><body>
<script>
window.__NUXT__ = {"data":[{"models":[
  {"name":"Claude Sonnet 4-5","provider":{"name":"Anthropic"},"params_b":200,"context_tokens":200000,"category":"text"},
  {"name":"Gemini 2.5 Pro","provider":{"name":"Google"},"params_b":null,"context_tokens":1000000,"category":"text"},
  {"name":"DALL-E 3","provider":{"name":"OpenAI"},"params_b":null,"context_tokens":null,"category":"image"}
]}]};
</script>
</body></html>
"""


@pytest.mark.asyncio
async def test_aa_extracts_text_models():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, err = await scraper.fetch()

    assert err is None
    names = [r.name for r in records]
    assert "Claude Sonnet 4-5" in names
    assert "Gemini 2.5 Pro" in names


@pytest.mark.asyncio
async def test_aa_excludes_non_text_models():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, _ = await scraper.fetch()

    names = [r.name for r in records]
    assert "DALL-E 3" not in names


@pytest.mark.asyncio
async def test_aa_extracts_provider_and_params():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, _ = await scraper.fetch()

    by_name = {r.name: r for r in records}
    assert by_name["Claude Sonnet 4-5"].provider == "Anthropic"
    assert by_name["Claude Sonnet 4-5"].params_b == 200.0
    assert by_name["Claude Sonnet 4-5"].context_k == 200
    assert by_name["Gemini 2.5 Pro"].params_b is None


@pytest.mark.asyncio
async def test_aa_error_on_failure():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(500))
        scraper = ArtificialAnalysisScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is not None
