from bs4 import BeautifulSoup
from core.models import ModelRecord
from scrapers.base import BaseScraper

URL = "https://www.swebench.com/verified.html"


class SWEBenchScraper(BaseScraper):
    name = "swebench"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get(URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        records = []
        table = soup.find("table")
        if not table:
            return records
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        try:
            name_idx = next(i for i, h in enumerate(headers) if "model" in h.lower())
            pct_idx = next(i for i, h in enumerate(headers) if "resolved" in h.lower() or "%" in h)
        except StopIteration:
            return records
        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) <= max(name_idx, pct_idx):
                continue
            name = cells[name_idx].get_text(strip=True)
            pct_text = cells[pct_idx].get_text(strip=True).replace("%", "").strip()
            try:
                pct = float(pct_text)
            except ValueError:
                continue
            records.append(ModelRecord(name=name, swe_bench_pct=pct))
        return records
