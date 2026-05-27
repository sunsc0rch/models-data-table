import json
import pytest
import respx
import httpx
from scrapers.swebench import SWEBenchScraper

URL = "https://www.swebench.com/index.html"

SAMPLE_DATA = [
    {
        "name": "bash-only",
        "results": [
            {"name": "Claude Opus 4.7", "resolved": 76.8},
            {"name": "Gemini 3 Flash", "resolved": 75.8},
            {"name": "GPT-4o", "resolved": 50.8},
        ],
    },
    {
        "name": "other-leaderboard",
        "results": [
            {"name": "ShouldBeIgnored", "resolved": 99.0},
        ],
    },
]

SAMPLE_HTML = f'<html><body><script type="application/json" id="leaderboard-data">{json.dumps(SAMPLE_DATA)}</script></body></html>'


@pytest.mark.asyncio
async def test_swebench_extracts_scores():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = SWEBenchScraper()
        records, err = await scraper.fetch()

    assert err is None
    assert len(records) == 3
    names = [r.name for r in records]
    assert "Claude Opus 4.7" in names


@pytest.mark.asyncio
async def test_swebench_parses_percentages():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = SWEBenchScraper()
        records, _ = await scraper.fetch()

    by_name = {r.name: r for r in records}
    assert by_name["Claude Opus 4.7"].swe_bench_pct == pytest.approx(76.8)
    assert by_name["GPT-4o"].swe_bench_pct == pytest.approx(50.8)


@pytest.mark.asyncio
async def test_swebench_uses_bash_only_leaderboard():
    """Only bash-only leaderboard entries should be returned."""
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = SWEBenchScraper()
        records, _ = await scraper.fetch()

    names = [r.name for r in records]
    assert "ShouldBeIgnored" not in names


@pytest.mark.asyncio
async def test_swebench_returns_empty_when_no_script():
    html = "<html><body><p>No data here</p></body></html>"
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=html))
        scraper = SWEBenchScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is None


@pytest.mark.asyncio
async def test_swebench_error_on_failure():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(404))
        scraper = SWEBenchScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is not None
