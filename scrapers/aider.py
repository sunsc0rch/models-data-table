"""
Aider polyglot leaderboard — coding benchmark (pass rate %, 225 tasks).
URL: https://aider.chat/docs/leaderboards/
Static HTML, one row per model+effort combination.
We keep only the best score per normalised model name.
"""

import re
from bs4 import BeautifulSoup
from core.models import ModelRecord
from scrapers.base import BaseScraper

URL = "https://aider.chat/docs/leaderboards/"

# Qualifiers that describe reasoning effort/thinking budget, not the model itself.
_EFFORT_RE = re.compile(
    r"\s*\([^)]*(?:think|high|low|medium|no\s+think|32k|64k|128k|reasoning|effort|diff"
    r"|chat|reasoner|instruct)[^)]*\)",
    re.I,
)
_NOISE_RE = re.compile(r"\s*,\s*.*API.*$", re.I)
_API_PREFIX_RE = re.compile(r"^[a-z-]+/", re.I)
_DATE_SUFFIX_RE = re.compile(r"-(\d{8})(?:\b|$)")


def _normalise(name: str) -> str:
    # Skip combined models (e.g. "o3 + gpt-4.1")
    if " + " in name:
        return ""
    name = _NOISE_RE.sub("", name)
    name = _EFFORT_RE.sub("", name)
    name = _API_PREFIX_RE.sub("", name)
    name = _DATE_SUFFIX_RE.sub(r" \1", name)
    # hyphens between any word chars (letter or digit) → spaces
    name = re.sub(r"(?<=\w)-(?=\w)", " ", name)
    # collapse extra spaces
    name = re.sub(r"\s+", " ", name)
    return name.strip()


class AiderScraper(BaseScraper):
    name = "aider"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get(URL, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        best: dict[str, float] = {}  # normalised_name → best score

        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            texts = [c.get_text(strip=True) for c in cells]
            # Main data rows: ['▶', model_name, 'XX.X%', ...]
            if not texts[2].endswith("%"):
                continue
            raw_name = texts[1]
            try:
                score = float(texts[2].rstrip("%"))
            except ValueError:
                continue
            norm = _normalise(raw_name)
            if not norm:
                continue
            if norm not in best or score > best[norm]:
                best[norm] = score

        return [
            ModelRecord(name=name, swe_bench_pct=score)
            for name, score in best.items()
        ]
