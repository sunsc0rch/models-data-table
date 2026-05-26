# AI Coding Models Leaderboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Textual TUI that displays a sortable table of AI coding models scraped from artificialanalysis.ai, OpenRouter, and swebench.com, with clipboard copy of opencode-ready config snippets.

**Architecture:** Modular scrapers (one file per source) each implement `BaseScraper._fetch()` and are registered in `SCRAPER_REGISTRY`. Results are fuzzy-merged into `ModelRecord` dataclasses and cached to `cache.json`. The TUI reads only from cache; refresh runs scrapers async in background.

**Tech Stack:** Python 3.11+, Textual, httpx, beautifulsoup4, rapidfuzz, pyperclip, pytest, respx, pytest-asyncio

---

## File Map

| File | Responsibility |
|---|---|
| `core/models.py` | `ModelRecord` dataclass — shared type across all layers |
| `core/cache.py` | read/write `cache.json` |
| `core/merger.py` | fuzzy-merge lists of `ModelRecord` from multiple scrapers |
| `scrapers/base.py` | `BaseScraper` ABC with error-safe `fetch()` wrapper |
| `scrapers/__init__.py` | `SCRAPER_REGISTRY` — the only file to edit when adding a source |
| `scrapers/openrouter.py` | OpenRouter REST API → free models, context, output |
| `scrapers/swebench.py` | swebench.com/verified HTML → SWE-bench % |
| `scrapers/artificialanalysis.py` | artificialanalysis.ai HTML → params, context, provider |
| `ui/table_view.py` | Textual screen: DataTable, keybindings, refresh worker |
| `app.py` | Textual App entry point |
| `requirements.txt` | pinned deps |
| `tests/test_models.py` | ModelRecord tests |
| `tests/test_cache.py` | cache read/write tests |
| `tests/test_merger.py` | merger fuzzy-match tests |
| `tests/scrapers/test_openrouter.py` | OpenRouter scraper with mocked HTTP |
| `tests/scrapers/test_swebench.py` | SWEBench scraper with mocked HTML |
| `tests/scrapers/test_artificialanalysis.py` | AA scraper with mocked HTML |

---

## Task 1: Project setup

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `core/__init__.py`, `scrapers/__init__.py` (empty stubs for now), `ui/__init__.py`
- Create: `tests/__init__.py`, `tests/scrapers/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
textual>=0.61.0
httpx>=0.27.0
beautifulsoup4>=4.12.0
rapidfuzz>=3.9.0
pyperclip>=1.8.2
pytest>=8.0.0
respx>=0.21.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Create .gitignore**

```
cache.json
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
```

- [ ] **Step 3: Create pytest.ini**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 4: Create package stubs**

```bash
mkdir -p core scrapers ui tests/scrapers
touch core/__init__.py ui/__init__.py tests/__init__.py tests/scrapers/__init__.py
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore pytest.ini core/__init__.py ui/__init__.py tests/__init__.py tests/scrapers/__init__.py
git commit -m "chore: project setup, deps, pytest config"
```

---

## Task 2: ModelRecord dataclass

**Files:**
- Create: `core/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py
from dataclasses import fields
from core.models import ModelRecord

def test_model_record_requires_name():
    r = ModelRecord(name="gpt-4o")
    assert r.name == "gpt-4o"

def test_model_record_all_optional_except_name():
    r = ModelRecord(name="x")
    assert r.provider is None
    assert r.params_b is None
    assert r.context_k is None
    assert r.output_tokens is None
    assert r.swe_bench_pct is None
    assert r.free_providers == []
    assert r.openrouter_id is None
    assert r.openrouter_name is None

def test_model_record_full():
    r = ModelRecord(
        name="devstral",
        provider="Mistral",
        params_b=22.0,
        context_k=262,
        output_tokens=8192,
        swe_bench_pct=46.8,
        free_providers=["OpenRouter"],
        openrouter_id="mistralai/devstral-2512:free",
        openrouter_name="Devstral 2",
    )
    assert r.params_b == 22.0
    assert r.swe_bench_pct == 46.8
    assert "OpenRouter" in r.free_providers
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.models'`

- [ ] **Step 3: Implement ModelRecord**

```python
# core/models.py
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelRecord:
    name: str
    provider: Optional[str] = None
    params_b: Optional[float] = None
    context_k: Optional[int] = None
    output_tokens: Optional[int] = None
    swe_bench_pct: Optional[float] = None
    free_providers: list[str] = field(default_factory=list)
    openrouter_id: Optional[str] = None
    openrouter_name: Optional[str] = None
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_models.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/models.py tests/test_models.py
git commit -m "feat: ModelRecord dataclass"
```

---

## Task 3: Cache layer

**Files:**
- Create: `core/cache.py`
- Create: `tests/test_cache.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cache.py
import json
from pathlib import Path
import pytest
from core.models import ModelRecord
import core.cache as cache_mod


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "CACHE_PATH", tmp_path / "cache.json")


def test_read_returns_empty_when_no_cache():
    assert cache_mod.read() == []


def test_write_then_read_roundtrip():
    records = [
        ModelRecord(name="gpt-4o", provider="OpenAI", swe_bench_pct=72.1),
        ModelRecord(name="claude-3-5", free_providers=["OpenRouter"]),
    ]
    cache_mod.write(records)
    result = cache_mod.read()
    assert len(result) == 2
    assert result[0].name == "gpt-4o"
    assert result[0].swe_bench_pct == 72.1
    assert result[1].free_providers == ["OpenRouter"]


def test_write_skips_on_empty_list(tmp_path, monkeypatch):
    path = tmp_path / "cache.json"
    monkeypatch.setattr(cache_mod, "CACHE_PATH", path)
    cache_mod.write([])
    assert not path.exists()


def test_write_does_not_overwrite_existing_cache_with_empty(tmp_path, monkeypatch):
    path = tmp_path / "cache.json"
    monkeypatch.setattr(cache_mod, "CACHE_PATH", path)
    cache_mod.write([ModelRecord(name="existing")])
    assert path.exists()
    cache_mod.write([])
    result = cache_mod.read()
    assert len(result) == 1
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_cache.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.cache'`

- [ ] **Step 3: Implement cache.py**

```python
# core/cache.py
import json
from dataclasses import asdict
from pathlib import Path
from core.models import ModelRecord

CACHE_PATH = Path(__file__).parent.parent / "cache.json"


def read() -> list[ModelRecord]:
    if not CACHE_PATH.exists():
        return []
    data = json.loads(CACHE_PATH.read_text())
    return [ModelRecord(**r) for r in data]


def write(records: list[ModelRecord]) -> None:
    if not records:
        return
    CACHE_PATH.write_text(json.dumps([asdict(r) for r in records], indent=2))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_cache.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/cache.py tests/test_cache.py
git commit -m "feat: cache read/write layer"
```

---

## Task 4: Merger

**Files:**
- Create: `core/merger.py`
- Create: `tests/test_merger.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_merger.py
from core.models import ModelRecord
from core.merger import merge


def test_merge_single_list():
    records = [ModelRecord(name="gpt-4o", provider="OpenAI")]
    result = merge([records])
    assert len(result) == 1
    assert result[0].provider == "OpenAI"


def test_merge_fills_missing_fields():
    from_aa = [ModelRecord(name="Claude Sonnet 4", provider="Anthropic", params_b=200.0)]
    from_or = [ModelRecord(name="Claude Sonnet 4", context_k=200, free_providers=["OpenRouter"])]
    result = merge([from_aa, from_or])
    assert len(result) == 1
    assert result[0].provider == "Anthropic"
    assert result[0].params_b == 200.0
    assert result[0].context_k == 200
    assert "OpenRouter" in result[0].free_providers


def test_merge_fuzzy_matches_similar_names():
    from_aa = [ModelRecord(name="Devstral Small 2025", provider="Mistral")]
    from_swe = [ModelRecord(name="devstral-small-2025", swe_bench_pct=46.8)]
    result = merge([from_aa, from_swe])
    assert len(result) == 1
    assert result[0].swe_bench_pct == 46.8


def test_merge_keeps_distinct_models():
    a = [ModelRecord(name="gpt-4o")]
    b = [ModelRecord(name="claude-3-5-sonnet")]
    result = merge([a, b])
    assert len(result) == 2


def test_merge_deduplicates_free_providers():
    a = [ModelRecord(name="llama-3", free_providers=["OpenRouter"])]
    b = [ModelRecord(name="llama-3", free_providers=["OpenRouter"])]
    result = merge([a, b])
    assert result[0].free_providers.count("OpenRouter") == 1


def test_merge_empty_inputs():
    assert merge([[], []]) == []
    assert merge([]) == []
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/test_merger.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.merger'`

- [ ] **Step 3: Implement merger.py**

```python
# core/merger.py
from dataclasses import fields
from rapidfuzz import process, fuzz
from core.models import ModelRecord

THRESHOLD = 85


def merge(scraper_results: list[list[ModelRecord]]) -> list[ModelRecord]:
    merged: dict[str, ModelRecord] = {}

    for records in scraper_results:
        for record in records:
            match = process.extractOne(
                record.name,
                merged.keys(),
                scorer=fuzz.token_sort_ratio,
                score_cutoff=THRESHOLD,
            ) if merged else None

            if match:
                merged[match[0]] = _combine(merged[match[0]], record)
            else:
                merged[record.name] = record

    return list(merged.values())


def _combine(base: ModelRecord, other: ModelRecord) -> ModelRecord:
    for f in fields(base):
        if f.name == "name":
            continue
        other_val = getattr(other, f.name)
        base_val = getattr(base, f.name)
        if f.name == "free_providers":
            setattr(base, f.name, list(set(base_val + other_val)))
        elif other_val is not None and base_val is None:
            setattr(base, f.name, other_val)
    return base
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_merger.py -v
```

Expected: 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add core/merger.py tests/test_merger.py
git commit -m "feat: fuzzy merger for ModelRecord lists"
```

---

## Task 5: BaseScraper and registry

**Files:**
- Create: `scrapers/base.py`
- Modify: `scrapers/__init__.py`

- [ ] **Step 1: Implement BaseScraper**

```python
# scrapers/base.py
from abc import ABC, abstractmethod
import httpx
from core.models import ModelRecord


class BaseScraper(ABC):
    name: str = "base"
    timeout: int = 30

    async def fetch(self) -> tuple[list[ModelRecord], Exception | None]:
        """Returns (records, error). On error returns ([], exception)."""
        try:
            return await self._fetch(), None
        except Exception as exc:
            return [], exc

    @abstractmethod
    async def _fetch(self) -> list[ModelRecord]:
        ...

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, **kwargs)
            resp.raise_for_status()
            return resp
```

- [ ] **Step 2: Create SCRAPER_REGISTRY in scrapers/__init__.py**

```python
# scrapers/__init__.py
# To add a new source: import it here and append an instance to SCRAPER_REGISTRY.
from scrapers.openrouter import OpenRouterScraper
from scrapers.swebench import SWEBenchScraper
from scrapers.artificialanalysis import ArtificialAnalysisScraper

SCRAPER_REGISTRY = [
    OpenRouterScraper(),
    SWEBenchScraper(),
    ArtificialAnalysisScraper(),
]
```

Note: this file will fail to import until the three scraper modules exist (Tasks 6-8). That's expected.

- [ ] **Step 3: Commit**

```bash
git add scrapers/base.py scrapers/__init__.py
git commit -m "feat: BaseScraper ABC and scraper registry"
```

---

## Task 6: OpenRouter scraper

**Files:**
- Create: `scrapers/openrouter.py`
- Create: `tests/scrapers/test_openrouter.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/scrapers/test_openrouter.py
import pytest
import respx
import httpx
from scrapers.openrouter import OpenRouterScraper

API_URL = "https://openrouter.ai/api/v1/models"

SAMPLE_RESPONSE = {
    "data": [
        {
            "id": "mistralai/devstral-2512:free",
            "name": "Devstral 2",
            "architecture": {"modality": "text->text"},
            "context_length": 262144,
            "top_provider": {"max_completion_tokens": 8192},
        },
        {
            "id": "openai/gpt-4o",
            "name": "GPT-4o",
            "architecture": {"modality": "text+image->text"},
            "context_length": 128000,
            "top_provider": {"max_completion_tokens": 16384},
        },
        {
            "id": "stability/stable-diffusion:free",
            "name": "Stable Diffusion",
            "architecture": {"modality": "text->image"},
            "context_length": 77,
            "top_provider": {"max_completion_tokens": None},
        },
        {
            "id": "mistralai/mistral-7b-instruct:free",
            "name": "Mistral 7B",
            "architecture": {"modality": "text->text"},
            "context_length": 32768,
            "top_provider": {"max_completion_tokens": 4096},
        },
    ]
}


@pytest.mark.asyncio
async def test_openrouter_returns_free_text_models():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=SAMPLE_RESPONSE))
        scraper = OpenRouterScraper()
        records, err = await scraper.fetch()

    assert err is None
    names = [r.name for r in records]
    assert "Devstral 2" in names
    assert "Mistral 7B" in names


@pytest.mark.asyncio
async def test_openrouter_excludes_non_text_input():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=SAMPLE_RESPONSE))
        scraper = OpenRouterScraper()
        records, _ = await scraper.fetch()

    names = [r.name for r in records]
    assert "GPT-4o" not in names
    assert "Stable Diffusion" not in names


@pytest.mark.asyncio
async def test_openrouter_excludes_paid_models():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=SAMPLE_RESPONSE))
        scraper = OpenRouterScraper()
        records, _ = await scraper.fetch()

    ids = [r.openrouter_id for r in records]
    assert "openai/gpt-4o" not in ids


@pytest.mark.asyncio
async def test_openrouter_sets_context_and_output():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(200, json=SAMPLE_RESPONSE))
        scraper = OpenRouterScraper()
        records, _ = await scraper.fetch()

    devstral = next(r for r in records if r.openrouter_id == "mistralai/devstral-2512:free")
    assert devstral.context_k == 262
    assert devstral.output_tokens == 8192
    assert devstral.free_providers == ["OpenRouter"]


@pytest.mark.asyncio
async def test_openrouter_returns_error_on_failure():
    with respx.mock:
        respx.get(API_URL).mock(return_value=httpx.Response(500))
        scraper = OpenRouterScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is not None
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/scrapers/test_openrouter.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.openrouter'`

- [ ] **Step 3: Implement openrouter.py**

```python
# scrapers/openrouter.py
from core.models import ModelRecord
from scrapers.base import BaseScraper

API_URL = "https://openrouter.ai/api/v1/models"


class OpenRouterScraper(BaseScraper):
    name = "openrouter"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get(API_URL)
        records = []
        for model in resp.json()["data"]:
            model_id: str = model["id"]
            if ":free" not in model_id:
                continue
            modality: str = model.get("architecture", {}).get("modality", "text->text")
            input_mod = modality.split("->")[0] if "->" in modality else modality
            if input_mod != "text":
                continue
            context = model.get("context_length")
            output = (model.get("top_provider") or {}).get("max_completion_tokens")
            records.append(ModelRecord(
                name=model.get("name", model_id),
                openrouter_id=model_id,
                openrouter_name=model.get("name"),
                context_k=context // 1000 if context else None,
                output_tokens=output,
                free_providers=["OpenRouter"],
            ))
        return records
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/scrapers/test_openrouter.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/openrouter.py tests/scrapers/test_openrouter.py
git commit -m "feat: OpenRouter scraper (free text models)"
```

---

## Task 7: SWEBench scraper

**Files:**
- Create: `scrapers/swebench.py`
- Create: `tests/scrapers/test_swebench.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/scrapers/test_swebench.py
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/scrapers/test_swebench.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.swebench'`

- [ ] **Step 3: Implement swebench.py**

```python
# scrapers/swebench.py
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/scrapers/test_swebench.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/swebench.py tests/scrapers/test_swebench.py
git commit -m "feat: SWEBench scraper"
```

---

## Task 8: ArtificialAnalysis scraper

**Files:**
- Create: `scrapers/artificialanalysis.py`
- Create: `tests/scrapers/test_artificialanalysis.py`

Note: artificialanalysis.ai renders data via JavaScript. The scraper fetches their JSON data endpoint embedded in the page. If the endpoint changes, only this file needs updating.

- [ ] **Step 1: Write failing tests**

```python
# tests/scrapers/test_artificialanalysis.py
import pytest
import respx
import httpx
from scrapers.artificialanalysis import ArtificialAnalysisScraper

URL = "https://artificialanalysis.ai/leaderboards/models"

SAMPLE_HTML = """
<html><body>
<script>
window.__NUXT__ = {"data":[{"models":[
  {"name":"Claude Sonnet 4-5","provider":{"name":"Anthropic"},"params_b":200,"context_tokens":200000,"category":"text"},
  {"name":"Gemini 2.5 Pro","provider":{"name":"Google"},"params_b":null,"context_tokens":1000000,"category":"text"},
  {"name":"DALL-E 3","provider":{"name":"OpenAI"},"params_b":null,"context_tokens":null,"category":"image"}
]}}];
</script>
</body></html>
"""


@pytest.mark.asyncio
async def test_aa_extracts_text_models():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, err = await scraper.fetch()

    assert err is None
    names = [r.name for r in records]
    assert "Claude Sonnet 4-5" in names
    assert "Gemini 2.5 Pro" in names


@pytest.mark.asyncio
async def test_aa_excludes_non_text_models():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, _ = await scraper.fetch()

    names = [r.name for r in records]
    assert "DALL-E 3" not in names


@pytest.mark.asyncio
async def test_aa_extracts_provider_and_params():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, text=SAMPLE_HTML))
        scraper = ArtificialAnalysisScraper()
        records, _ = await scraper.fetch()

    by_name = {r.name: r for r in records}
    assert by_name["Claude Sonnet 4-5"].provider == "Anthropic"
    assert by_name["Claude Sonnet 4-5"].params_b == 200.0
    assert by_name["Claude Sonnet 4-5"].context_k == 200
    assert by_name["Gemini 2.5 Pro"].params_b is None


@pytest.mark.asyncio
async def test_aa_error_on_failure():
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(500))
        scraper = ArtificialAnalysisScraper()
        records, err = await scraper.fetch()

    assert records == []
    assert err is not None
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
pytest tests/scrapers/test_artificialanalysis.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.artificialanalysis'`

- [ ] **Step 3: Implement artificialanalysis.py**

```python
# scrapers/artificialanalysis.py
import json
import re
from bs4 import BeautifulSoup
from core.models import ModelRecord
from scrapers.base import BaseScraper

URL = "https://artificialanalysis.ai/leaderboards/models"
# Pattern to extract the JSON payload from the __NUXT__ script tag
_NUXT_RE = re.compile(r"window\.__NUXT__\s*=\s*(\{.*?\});\s*$", re.DOTALL | re.MULTILINE)


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
                # Traverse data[0]["models"] or data["data"][0]["models"]
                for candidate in [data, *(data.get("data") or [])]:
                    if isinstance(candidate, dict) and "models" in candidate:
                        return candidate["models"]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        return []
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/scrapers/test_artificialanalysis.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scrapers/artificialanalysis.py tests/scrapers/test_artificialanalysis.py
git commit -m "feat: ArtificialAnalysis scraper"
```

---

## Task 9: TUI table view

**Files:**
- Create: `ui/table_view.py`

No unit tests for TUI (Textual's async pilot testing is complex and adds little value here — manual test in Task 10 covers it).

- [ ] **Step 1: Implement ui/table_view.py**

```python
# ui/table_view.py
import asyncio
import json
import pyperclip
from dataclasses import asdict
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, ProgressBar
from textual import work

import core.cache as cache
import core.merger as merger
from core.models import ModelRecord
from scrapers import SCRAPER_REGISTRY

COLUMNS = [
    ("Model", "name"),
    ("Provider", "provider"),
    ("Params (B)", "params_b"),
    ("Context (K)", "context_k"),
    ("SWE-bench %", "swe_bench_pct"),
    ("Free via", "free_providers"),
]

NON_CODING_OUTPUT = {"image", "video", "audio"}


class LeaderboardScreen(Screen):
    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("f", "toggle_free", "Free only"),
        Binding("enter", "copy_snippet", "Copy snippet"),
        Binding("q", "app.quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self._records: list[ModelRecord] = []
        self._free_only = False
        self._sort_col: str = "swe_bench_pct"
        self._sort_asc = False
        self._errors: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("", id="status")
        yield DataTable(cursor_type="row", id="table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        for label, _ in COLUMNS:
            table.add_column(label, key=label)
        self._records = cache.read()
        if not self._records:
            self.query_one("#status", Label).update(
                "No data — press [bold]R[/bold] to refresh"
            )
        else:
            self._render_table()

    def _render_table(self) -> None:
        records = self._records
        if self._free_only:
            records = [r for r in records if r.free_providers]
        records = sorted(
            records,
            key=lambda r: (getattr(r, self._sort_col) is None,
                           getattr(r, self._sort_col) or 0),
            reverse=not self._sort_asc,
        )
        table = self.query_one(DataTable)
        table.clear()
        for r in records:
            params = f"{r.params_b:.0f}B" if r.params_b is not None else "—"
            context = f"{r.context_k}K" if r.context_k is not None else "—"
            swe = f"{r.swe_bench_pct:.1f}%" if r.swe_bench_pct is not None else "—"
            free = ", ".join(r.free_providers) if r.free_providers else "—"
            table.add_row(r.name, r.provider or "—", params, context, swe, free)

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        col_map = {label: field for label, field in COLUMNS}
        field = col_map.get(str(event.label))
        if not field:
            return
        if self._sort_col == field:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = field
            self._sort_asc = False
        self._render_table()

    def action_toggle_free(self) -> None:
        self._free_only = not self._free_only
        status = self.query_one("#status", Label)
        status.update("[bold]Showing free models only[/bold]" if self._free_only else "")
        self._render_table()

    def action_copy_snippet(self) -> None:
        table = self.query_one(DataTable)
        row_idx = table.cursor_row
        visible = self._records
        if self._free_only:
            visible = [r for r in visible if r.free_providers]
        visible = sorted(
            visible,
            key=lambda r: (getattr(r, self._sort_col) is None,
                           getattr(r, self._sort_col) or 0),
            reverse=not self._sort_asc,
        )
        if row_idx >= len(visible):
            return
        record = visible[row_idx]
        snippet = _build_snippet(record)
        status = self.query_one("#status", Label)
        try:
            pyperclip.copy(snippet)
            status.update(f"Copied snippet for [bold]{record.name}[/bold]")
        except pyperclip.PyperclipException:
            status.update(f"Clipboard unavailable. Snippet:\n{snippet}")

    @work(exclusive=True)
    async def action_refresh(self) -> None:
        status = self.query_one("#status", Label)
        status.update("Refreshing…")
        results = await asyncio.gather(*[s.fetch() for s in SCRAPER_REGISTRY])
        errors = []
        record_lists = []
        for scraper, (records, err) in zip(SCRAPER_REGISTRY, results):
            record_lists.append(records)
            if err:
                errors.append(f"⚠ {scraper.name}: {type(err).__name__}")
        merged = merger.merge(record_lists)
        cache.write(merged)
        self._records = cache.read()
        self._render_table()
        msg = " | ".join(errors) if errors else f"Updated — {len(merged)} models"
        status.update(msg)


def _build_snippet(record: ModelRecord) -> str:
    model_id = record.openrouter_id or f"{record.name}:free"
    display_name = record.openrouter_name or record.name
    context = (record.context_k or 128) * 1000
    output = record.output_tokens or 8192
    body = json.dumps({"name": display_name, "limit": {"context": context, "output": output}}, indent=2)
    return f'"{model_id}": {body}'
```

- [ ] **Step 2: Commit**

```bash
git add ui/table_view.py
git commit -m "feat: Textual TUI table view with sort, filter, refresh, copy"
```

---

## Task 10: App entry point and manual test

**Files:**
- Create: `app.py`

- [ ] **Step 1: Implement app.py**

```python
# app.py
from textual.app import App
from ui.table_view import LeaderboardScreen


class LeaderboardApp(App):
    CSS = """
    #status {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text-muted;
    }
    DataTable {
        height: 1fr;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(LeaderboardScreen())


if __name__ == "__main__":
    LeaderboardApp().run()
```

- [ ] **Step 2: Run the full test suite**

```bash
pytest -v
```

Expected: all tests PASS, no errors.

- [ ] **Step 3: Launch the app and verify manually**

```bash
python app.py
```

Verify:
- Table loads from cache (or shows "No data" message if cache.json doesn't exist)
- Press `r` — progress shown, scrapers run, table populates
- Click a column header — table re-sorts; click again — reverses
- Press `f` — only free models shown; press `f` again — all models shown
- Navigate to a free model row, press `Enter` — check clipboard contains valid JSON snippet
- Press `q` — app exits cleanly

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: app entry point — leaderboard TUI complete"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Sortable table with all 6 columns
- ✅ Filter for free models (`f` key)
- ✅ Refresh with background async (`r` key, `@work`)
- ✅ opencode snippet copied to clipboard (`Enter`)
- ✅ Scraper registry — add new source in 2 steps
- ✅ Error per-scraper shown in status bar, cache not overwritten on empty
- ✅ Cache missing on first run shows helpful message
- ✅ Only coding models (text->text input modality filter in OpenRouter, category filter in AA)
- ✅ SWE-bench % from swebench.com
- ✅ Fuzzy merge across sources

**Types consistent across tasks:**
- `BaseScraper.fetch()` returns `tuple[list[ModelRecord], Exception | None]` — used consistently in `SCRAPER_REGISTRY` loop in `table_view.py`
- `ModelRecord` fields match usage in `merger._combine()`, `cache.py` (via `asdict`), `table_view._render_table()`
- `SCRAPER_REGISTRY` imported in `scrapers/__init__.py` and consumed in `ui/table_view.py`
