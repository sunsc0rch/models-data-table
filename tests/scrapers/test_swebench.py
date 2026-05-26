import pytest
import respx
import httpx
from scrapers.swebench import SWEBenchScraper

URL = "https://www.swebench.com/verified.html"

SAMPLE_HTML = """
<html><body>
<table>
  <thead><tr><th>Model</th><th>% Resolved</th></tr></thead>
  <tbody>
    <tr><td>Claude Sonnet 4-5</td><td>72.10%</td></tr>
    <tr><td>GPT-4o (2024-11)</td><td>50.80%</td></tr>
    <tr><td>Devstral Small 2025</td><td>46.00%</td></tr>
  </tbody>
</table>
</body></html>
"""


@pytest.mark.asyncio
async def test_swebench_extracts_scores():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = SWEBenchScraper()
        records, err = await scraper.fetch()

    assert err is None
    assert len(records) == 3
    names = [r.name for r in records]
    assert "Claude Sonnet 4-5" in names


@pytest.mark.asyncio
async def test_swebench_parses_percentages():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = SWEBenchScraper()
        records, _ = await scraper.fetch()

    by_name = {r.name: r for r in records}
    assert by_name["Claude Sonnet 4-5"].swe_bench_pct == pytest.approx(72.10)
    assert by_name["GPT-4o (2024-11)"].swe_bench_pct == pytest.approx(50.80)


@pytest.mark.asyncio
async def test_swebench_error_on_failure():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(404))
        scraper = SWEBenchScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is not None
