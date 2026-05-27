"""
Fetches free-coding-models sources.js from jsDelivr CDN and updates
the in-memory FCM_PROVIDERS dict used by static_data enrichment.

No local npm install required. Uses pure-Python regex parsing — no Node.js.
CDN URL (no auth, no proxy needed):
  https://cdn.jsdelivr.net/npm/free-coding-models@latest/sources.js
"""

import re
import httpx
from core.free_providers_data import FCM_PROVIDERS

CDN_URL = "https://cdn.jsdelivr.net/npm/free-coding-models@latest/sources.js"

_SKIP = {"gemini", "opencode-zen"}
_SHORT_NAMES: dict[str, str] = {
    "nvidia":        "NIM",
    "groq":          "Groq",
    "cerebras":      "Cerebras",
    "googleai":      "Google AI",
    "github-models": "GitHub",
    "mistral":       "Mistral",
    "cloudflare":    "Cloudflare",
    "openrouter":    "OpenRouter",
    "sambanova":     "SambaNova",
    "ovhcloud":      "OVHcloud",
    "codestral":     "Codestral",
    "zai":           "ZAI",
    "scaleway":      "Scaleway",
    "qwen":          "DashScope",
}


async def refresh() -> tuple[int, Exception | None]:
    """
    Fetch the latest sources.js from CDN, parse it, and update FCM_PROVIDERS
    in-place so that static_data enrichment picks up fresh provider data.
    Returns (label_count, error_or_None).
    """
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False) as client:
            resp = await client.get(CDN_URL)
            resp.raise_for_status()
        fresh = _parse(resp.text)
        if fresh:
            FCM_PROVIDERS.clear()
            FCM_PROVIDERS.update(fresh)
            # Rebuild the normalized cache used by static_data._fill_free_providers
            import core.static_data as sd
            sd._rebuild_fcm_cache()
        return len(fresh), None
    except Exception as exc:
        return 0, exc


def _parse(text: str) -> dict[str, list[str]]:
    """
    Pure-Python parser for the ES-module sources.js format.

    Extracts: variable_name → [label, ...] from each `export const NAME = [...]`
    Then maps: provider_key → (display_name, variable_name) from `export const sources = {...}`
    Returns: {label: [provider_short_name, ...]}
    """
    # ── Step 1: variable → labels ───────────────────────────────────────────
    var_labels: dict[str, list[str]] = {}
    for m in re.finditer(r"export\s+const\s+(\w+)\s*=\s*\[", text):
        var_name = m.group(1)
        start = m.end()
        depth, i = 1, start
        while i < len(text) and depth:
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
            i += 1
        block = text[start : i - 1]
        # Extract second element (label) from each tuple
        labels = re.findall(r"\[\s*'[^']+'\s*,\s*'([^']+)'", block)
        if labels:
            var_labels[var_name] = labels

    # ── Step 2: provider key → (display_name, var_name) ────────────────────
    sources_m = re.search(r"export\s+const\s+sources\s*=\s*\{", text)
    if not sources_m:
        return {}

    providers: dict[str, tuple[str, str]] = {}
    # Match entries like: key: { name: 'Display', ..., models: varName, }
    for m in re.finditer(
        r"""['\"]?([\w-]+)['\"]?\s*:\s*\{[^{}]*?"""
        r"""name\s*:\s*['"]([^'"]+)['"][^{}]*?"""
        r"""models\s*:\s*(\w+)""",
        text[sources_m.end() :],
        re.DOTALL,
    ):
        key, name, var = m.group(1), m.group(2), m.group(3)
        providers[key] = (name, var)

    # ── Step 3: build label → [provider_names] ─────────────────────────────
    result: dict[str, list[str]] = {}
    for key, (display_name, var_name) in providers.items():
        if key in _SKIP:
            continue
        provider_short = _SHORT_NAMES.get(key, display_name)
        for label in var_labels.get(var_name, []):
            if label not in result:
                result[label] = []
            if provider_short not in result[label]:
                result[label].append(provider_short)

    return result
