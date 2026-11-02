import json
import re
from core.models import ModelRecord
from scrapers.base import BaseScraper

URL = "https://artificialanalysis.ai/leaderboards/models"
_RSC_CHUNK_RE = re.compile(
    r'self\.__next_f\.push\(\[\d+,(.*?)\]\)</script>', re.DOTALL
)
# The models array key in the RSC payload, most recent first.
_MODELS_KEYS = ('"initialModels":[', '"models":[')
# Coding benchmark inside the per-model "scores" dict (0..1 fraction).
# AA no longer publishes a composite codingIndex; frontiercode-2-0 is their
# current frontier coding eval. Do NOT mix in other benchmarks (e.g.
# livecodebench) — different difficulty scales break the normalised ranking.
_CODING_SCORE_KEYS = ("frontiercode-2-0",)


class ArtificialAnalysisScraper(BaseScraper):
    name = "artificialanalysis"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get(URL, headers={"User-Agent": "Mozilla/5.0"})
        raw_models = self._extract_models(resp.text)
        records = []
        for m in raw_models:
            if m.get("deprecated"):
                continue
            if m.get("outputModalityImage") or m.get("outputModalityVideo") or m.get("outputModalitySpeech"):
                continue
            ctx = m.get("contextWindowTokens")
            params = m.get("totalParameters")
            records.append(ModelRecord(
                name=m["name"],
                provider=m.get("modelCreatorName"),
                params_b=float(params) if params is not None else None,
                context_k=ctx // 1000 if ctx else None,
                coding_index=self._coding_score(m),
            ))
        return records

    @staticmethod
    def _coding_score(m: dict) -> float | None:
        coding = m.get("codingIndex")
        if coding is not None:
            return float(coding)
        scores = m.get("scores") or {}
        for key in _CODING_SCORE_KEYS:
            val = scores.get(key)
            if val is not None:
                return float(val) * 100
        return None

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
            for key in _MODELS_KEYS:
                idx = decoded.find(key)
                if idx == -1:
                    continue
                arr_start = decoded.index("[", idx)
                try:
                    models, _ = json.JSONDecoder().raw_decode(decoded, arr_start)
                    return models
                except (json.JSONDecodeError, ValueError):
                    continue
        return []
