import json
import re
from bs4 import BeautifulSoup
from core.models import ModelRecord
from scrapers.base import BaseScraper

URL = "https://artificialanalysis.ai/leaderboards/models"
_NUXT_RE = re.compile(r"window\.__NUXT__\s*=\s*(\{.*\})", re.DOTALL)


class ArtificialAnalysisScraper(BaseScraper):
    name = "artificialanalysis"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get(URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        models = self._extract_models(soup)
        records = []
        for m in models:
            if (m.get("category") or "").lower() != "text":
                continue
            provider_obj = m.get("provider") or {}
            context = m.get("context_tokens")
            params = m.get("params_b")
            records.append(ModelRecord(
                name=m["name"],
                provider=provider_obj.get("name"),
                params_b=float(params) if params is not None else None,
                context_k=context // 1000 if context else None,
            ))
        return records

    def _extract_models(self, soup: BeautifulSoup) -> list[dict]:
        for script in soup.find_all("script"):
            text = script.string or ""
            match = _NUXT_RE.search(text)
            if not match:
                continue
            try:
                data = json.loads(match.group(1))
                for candidate in [data, *(data.get("data") or [])]:
                    if isinstance(candidate, dict) and "models" in candidate:
                        return candidate["models"]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        return []
