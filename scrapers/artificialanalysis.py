import json
import re
from core.models import ModelRecord
from scrapers.base import BaseScraper

URL = "https://artificialanalysis.ai/leaderboards/models"
_RSC_CHUNK_RE = re.compile(
    r'self\.__next_f\.push\(\[\d+,(.*?)\]\)</script>', re.DOTALL
)


class ArtificialAnalysisScraper(BaseScraper):
    name = "artificialanalysis"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get(URL, headers={"User-Agent": "Mozilla/5.0"})
        raw_models = self._extract_models(resp.text)
        records = []
        for m in raw_models:
            if m.get("deprecated"):
                continue
            if not (m.get("inputModalityText") and m.get("outputModalityText")):
                continue
            if m.get("outputModalityImage") or m.get("outputModalityVideo") or m.get("outputModalitySpeech"):
                continue
            ctx = m.get("contextWindowTokens")
            params = m.get("totalParameters")
            coding = m.get("codingIndex")
            records.append(ModelRecord(
                name=m["name"],
                provider=m.get("modelCreatorName"),
                params_b=float(params) if params is not None else None,
                context_k=ctx // 1000 if ctx else None,
                coding_index=float(coding) if coding is not None else None,
            ))
        return records

    def _extract_models(self, html: str) -> list[dict]:
        for raw in _RSC_CHUNK_RE.findall(html):
            if "contextWindowTokens" not in raw:
                continue
            try:
                decoded = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(decoded, str):
                continue
            idx = decoded.find('"models":[')
            if idx == -1:
                continue
            arr_start = decoded.index("[", idx)
            try:
                models, _ = json.JSONDecoder().raw_decode(decoded, arr_start)
                return models
            except (json.JSONDecodeError, ValueError):
                continue
        return []
