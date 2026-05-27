import json
from core.models import ModelRecord
from scrapers.base import BaseScraper

URL = "https://www.swebench.com/index.html"
LEADERBOARD_NAME = "bash-only"


class SWEBenchScraper(BaseScraper):
    name = "swebench"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get(URL)
        start = resp.text.find('id="leaderboard-data"')
        if start == -1:
            return []
        tag_end = resp.text.index(">", start) + 1
        close = resp.text.index("</script>", tag_end)
        data = json.loads(resp.text[tag_end:close])
        leaderboard = next(
            (lb for lb in data if lb.get("name") == LEADERBOARD_NAME), None
        )
        if not leaderboard:
            return []
        records = []
        for entry in leaderboard.get("results", []):
            name = entry.get("name") or entry.get("model")
            resolved = entry.get("resolved")
            if not name or resolved is None:
                continue
            records.append(ModelRecord(name=name, swe_bench_pct=float(resolved)))
        return records
