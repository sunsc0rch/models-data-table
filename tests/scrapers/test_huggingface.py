import pytest
import respx
import httpx
from scrapers.huggingface import HuggingFaceScraper, HF_API, HF_MODEL_IDS

SAMPLE_RESPONSE = {"safetensors": {"total": 70553706496}}


def _mock_all(mock, status: int, body=None):
    """Register a mock for every URL in HF_MODEL_IDS."""
    seen = set()
    for hf_id in HF_MODEL_IDS.values():
        url = f"{HF_API}/{hf_id}"
        if url in seen:
            continue
        seen.add(url)
        if body is not None:
            mock.get(url).mock(return_value=httpx.Response(status, json=body))
        else:
            mock.get(url).mock(return_value=httpx.Response(status))


@pytest.mark.asyncio
async def test_hf_extracts_params():
    with respx.mock(assert_all_called=False) as mock:
        _mock_all(mock, 200, SAMPLE_RESPONSE)
        scraper = HuggingFaceScraper()
        records, err = await scraper.fetch()

    assert err is None
    assert len(records) > 0
    for r in records:
        assert r.params_b == pytest.approx(70.6, abs=1.0)


@pytest.mark.asyncio
async def test_hf_skips_gated_models():
    with respx.mock(assert_all_called=False) as mock:
        _mock_all(mock, 401)
        scraper = HuggingFaceScraper()
        records, err = await scraper.fetch()

    assert err is None
    assert len(records) == 0
