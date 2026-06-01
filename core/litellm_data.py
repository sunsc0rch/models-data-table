"""
LiteLLM model registry — module-level data source for per-model
``context_k``, ``output_tokens``, ``supports_function_calling``, and
``supports_vision``.

Fetched from BerriAI/litellm ``model_prices_and_context_window.json``.
Unlike other scrapers this does **not** return ``ModelRecord`` entries;
instead it populates ``LITELLM_DATA`` in place so that
``core.static_data._fill_from_litellm`` can enrich records by fuzzy name
match during ``enrich()``.

The pattern mirrors ``core.fcm_updater``: a refresh function called
separately from the scraper registry during ``action_refresh``.
"""
import json
import re
import httpx


LITELLM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

# Module-level dict: normalized_name -> spec
#   spec = {"context_k": int, "output_tokens": int,
#           "supports_function_calling": bool, "supports_vision": bool}
LITELLM_DATA: dict[str, dict] = {}

CHAT_MODES = {"chat", "responses"}
# Tokens that vary across providers/versions and add noise to fuzzy matching.
_NOISE_TOKENS = re.compile(
    r"\b(v\d+(?:\.\d+)*|preview|latest|exp|alpha|beta|instruct|chat|base|"
    r"hf|gguf|fp8|bf16|q\d+|ft|fs|maas|public|cloud)\b",
    re.IGNORECASE,
)
# Bedrock model-version qualifiers: "v1:0", "v2:0", "v3:5" — keep the major
# version (Claude 3 vs 4) but drop these provider-specific tags.
_VERSION_QUALIFIER_RE = re.compile(r"\bv\d+:\d+\b", re.IGNORECASE)
# Date codes: "20240620" (YYYYMMDD), "2024-08-06", "2505" (YYMM) — noise.
_DATE_RE = re.compile(r"\b\d{4}[-/]?\d{2}(?:[-/]?\d{2})?\b")


def _derive_name(key: str) -> str:
    """Derive a normalized name from a LiteLLM key for fuzzy matching.

    Examples::

        "openrouter/qwen/qwen3-coder"            -> "qwen3 coder"
        "mistral/devstral-small-2505"            -> "devstral small"
        "us.anthropic.claude-3-5-sonnet-v2:0"    -> "anthropic claude 3 5 sonnet"
        "claude-3-5-sonnet-20241022"             -> "claude 3 5 sonnet"

    Returns ``""`` for inputs that can't yield a usable name.
    """
    # Take the part after the last '/'.
    name = key.rsplit("/", 1)[-1]
    # For Bedrock-style "us.anthropic.claude-3-5-sonnet" — drop the leading
    # region token if present.
    parts = name.split(".")
    if (
        len(parts) >= 3
        and parts[0] in {"us", "eu", "au", "jp", "apac", "ap", "sa", "ca", "af", "me", "global"}
    ):
        parts = parts[1:]
    name = " ".join(parts)
    # Run _VERSION_QUALIFIER_RE on the raw form so it can see the ":".
    name = _VERSION_QUALIFIER_RE.sub(" ", name)
    # Now replace separators with spaces.
    name = re.sub(r"[:\-_./]+", " ", name)
    name = name.lower()
    # Strip noise: dates, then named noise tokens.
    name = _DATE_RE.sub(" ", name)
    name = _NOISE_TOKENS.sub(" ", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) < 3:
        return ""
    return name


def _parse(json_text: str) -> dict[str, dict]:
    """Parse the LiteLLM JSON and return ``{normalized_name: spec}``.

    Dedup policy when multiple LiteLLM keys normalize to the same name:
      1. Prefer entries with an ``openrouter/`` prefix (most useful for
         our opencode-focused use case).
      2. Among entries with the same prefix status, prefer the one with
         higher ``output_tokens`` (usually the canonical / non-tiny variant).
    """
    raw = json.loads(json_text)
    specs: dict[str, tuple[str, dict]] = {}
    for key, val in raw.items():
        if not isinstance(val, dict):
            continue
        if val.get("mode") not in CHAT_MODES:
            continue
        in_tok = val.get("max_input_tokens") or val.get("max_tokens")
        out_tok = val.get("max_output_tokens") or val.get("max_tokens")
        if not in_tok or not out_tok:
            continue
        if in_tok < 1000 or out_tok < 100:
            continue
        name = _derive_name(key)
        if len(name) < 3:
            continue
        spec = {
            "context_k": in_tok // 1000,
            "output_tokens": out_tok,
            "supports_function_calling": bool(val.get("supports_function_calling")),
            "supports_vision": bool(val.get("supports_vision")),
        }
        is_openrouter = key.startswith("openrouter/")
        existing = specs.get(name)
        if existing is None:
            specs[name] = (key, spec)
            continue
        existing_key, existing_spec = existing
        existing_is_or = existing_key.startswith("openrouter/")
        if is_openrouter and not existing_is_or:
            specs[name] = (key, spec)
        elif is_openrouter == existing_is_or and spec["output_tokens"] > existing_spec["output_tokens"]:
            specs[name] = (key, spec)
    return {name: spec for name, (_, spec) in specs.items()}


async def refresh() -> tuple[int, Exception | None]:
    """Fetch and populate ``LITELLM_DATA``. Returns ``(count, error_or_None)``."""
    try:
        async with httpx.AsyncClient(timeout=20, trust_env=False) as client:
            resp = await client.get(LITELLM_URL)
            resp.raise_for_status()
        fresh = _parse(resp.text)
        LITELLM_DATA.clear()
        LITELLM_DATA.update(fresh)
        return len(fresh), None
    except Exception as exc:
        return 0, exc
