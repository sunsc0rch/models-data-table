import pytest
import respx
import httpx
from scrapers.aider import AiderScraper

URL = "https://aider.chat/docs/leaderboards/"

SAMPLE_HTML = """
<html><body>
<table>
<tr><td>▶</td><td>gpt-5 (high)</td><td>88.0%</td><td>$29.08</td><td>cmd</td></tr>
<tr><td>▶</td><td>gpt-5 (medium)</td><td>86.7%</td><td>$17.69</td><td>cmd</td></tr>
<tr><td>▶</td><td>o3 (high)</td><td>81.3%</td><td>$1.00</td><td>cmd</td></tr>
<tr><td>▶</td><td>o3</td><td>76.9%</td><td>$0.50</td><td>cmd</td></tr>
<tr><td>▶</td><td>claude-opus-4-20250514 (no think)</td><td>70.7%</td><td>$2.00</td><td>cmd</td></tr>
<tr><td>▶</td><td>o3 + gpt-4.1</td><td>78.2%</td><td>$3.00</td><td>cmd</td></tr>
<tr><td>▶</td><td>bad row</td><td>not a percent</td></tr>
</table>
</body></html>
"""


@pytest.mark.asyncio
async def test_aider_extracts_scores():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = AiderScraper()
        records, err = await scraper.fetch()

    assert err is None
    assert len(records) > 0
    names = [r.name for r in records]
    # gpt-5 should appear once (best of high/medium)
    assert sum(1 for n in names if "gpt" in n.lower() and "5" in n) == 1


@pytest.mark.asyncio
async def test_aider_keeps_best_score_per_model():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = AiderScraper()
        records, _ = await scraper.fetch()

    by_name = {r.name: r for r in records}
    # gpt-5 best score is 88.0 (high), not 86.7 (medium)
    gpt5 = next((r for r in records if "gpt" in r.name.lower() and "5" in r.name), None)
    assert gpt5 is not None
    assert gpt5.swe_bench_pct == pytest.approx(88.0)


@pytest.mark.asyncio
async def test_aider_skips_combined_models():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = AiderScraper()
        records, _ = await scraper.fetch()

    names = [r.name for r in records]
    assert not any("+" in n for n in names)


@pytest.mark.asyncio
async def test_aider_error_on_failure():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(500))
        scraper = AiderScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is not None
