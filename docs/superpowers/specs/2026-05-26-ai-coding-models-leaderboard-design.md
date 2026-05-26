# AI Coding Models Leaderboard — Design Spec

Date: 2026-05-26

## Overview

A Python TUI application (Textual) that displays an interactive, sortable table of AI coding models from multiple providers. Data is scraped from three sources and cached locally. Users can refresh on demand, filter for free models, and copy an opencode-ready config snippet for any model.

## Scope

Coding models only. Models tagged as image, video, audio, or embedding are excluded at the scraper level.

## Architecture

**Approach: Modular scrapers + JSON cache**

Each data source is an independent module. Results are merged by model name and written to a local `cache.json`. The TUI reads only from the cache and never blocks on network requests.

```
models_data_table/
├── app.py                        # Textual App entry point
├── ui/
│   └── table_view.py             # main screen: table, toolbar, keybindings
├── scrapers/
│   ├── base.py                   # BaseScraper with fetch() -> list[dict]
│   ├── artificialanalysis.py     # params, context window, provider
│   ├── openrouter.py             # free models, context, output limits
│   └── swebench.py               # SWE-bench % scores
├── core/
│   ├── merger.py                 # merges results from all scrapers by model name
│   └── cache.py                  # read/write cache.json, skip write if data empty
├── cache.json                    # local cache (gitignored)
└── requirements.txt
```

## Data Sources

| Source | Data extracted | Method |
|---|---|---|
| artificialanalysis.ai | model name, provider, parameters (B), context (K) | HTML scraping (bs4) |
| openrouter.ai/api/v1/models | free models (`:free` suffix), context_length, max_completion_tokens | REST API (JSON) |
| swebench.com/verified | SWE-bench % | HTML scraping (bs4) |

**Model matching across sources:** fuzzy match by model name using `rapidfuzz`. Threshold: 85.

**Coding-only filter:** exclude models where OpenRouter tags include `image`, `video`, `audio`, or `multimodal-image-out`, or where artificialanalysis category is not text generation.

## Data Flow

```
[Refresh button / 'r' key]
        │
        ▼
asyncio.gather(
  artificialanalysis.fetch(),
  openrouter.fetch(),
  swebench.fetch()
)
        │
        ▼
merger.merge(results) → unified list[ModelRecord]
        │
        ▼
cache.write(cache.json)   ← skipped if all scrapers returned empty
        │
        ▼
TUI reloads table from cache
```

If a scraper fails, the TUI shows a warning banner (`⚠ swebench: failed`) but continues with partial data. The cache is not overwritten with empty data.

## TUI Interface

**Table columns** (all sortable by clicking header):

| Column | Source | Example |
|---|---|---|
| Model | artificialanalysis | `claude-sonnet-4-5` |
| Provider | artificialanalysis | Anthropic |
| Params (B) | artificialanalysis | 200B |
| Context (K) | artificialanalysis | 200K |
| SWE-bench % | swebench | 72.1% |
| Free via | openrouter | OpenRouter |

Default sort: SWE-bench % descending.

**Keybindings:**

| Key | Action |
|---|---|
| `↑` / `↓` | navigate rows |
| click header | sort by column (repeat = reverse) |
| `r` or `[Refresh]` button | run all scrapers in background, show progress bar |
| `Enter` | copy opencode snippet for selected model to clipboard |
| `f` | toggle filter: show only free models |
| `q` / `Ctrl+C` | quit |

## opencode Snippet Format

When the user presses Enter on a row, the following JSON is copied to clipboard (values sourced from OpenRouter API):

```json
"mistralai/devstral-2512:free": {
  "name": "Devstral 2",
  "limit": {
    "context": 262144,
    "output": 8192
  }
}
```

This matches the exact format of `provider.openrouter.models` in `~/.config/opencode/opencode.json`. If a model is available from multiple free providers, the snippet uses the OpenRouter model ID with `:free` suffix. `context` and `output` values come directly from OpenRouter API fields `context_length` and `top_provider.max_completion_tokens`.

## Dependencies

```
textual
httpx
beautifulsoup4
rapidfuzz
pyperclip
```

## Error Handling

- Scraper timeout: 30s per source
- Failed scraper: logged to status bar, does not block other scrapers
- Cache missing on first run: TUI shows "No data — press R to refresh"
- Empty scraper result: cache.json not overwritten
- Clipboard unavailable: snippet printed to status bar instead

## Not in Scope

- Paid model pricing data
- Model history / changelog tracking
- SQLite storage
- Auto-refresh on schedule (manual only)
- Direct write to opencode.json (clipboard only)
