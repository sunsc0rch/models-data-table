"""
Static enrichment: fills missing provider, context_k, params_b, coding scores,
and free_providers based on known public data and approximate estimates.

Applied after merge as a final pass. Never overwrites existing values.
"""

import re
from core.models import ModelRecord
from core.free_providers_data import EXTRA_PROVIDERS, FCM_PROVIDERS, PROVIDER_PRIORITY

# ---------------------------------------------------------------------------
# Provider inference from name
# ---------------------------------------------------------------------------

_PROVIDER_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^claude\b", re.I), "Anthropic"),
    (re.compile(r"^gemini\b|^gemma\b", re.I), "Google"),
    (re.compile(r"^gpt-|^o\d\b|^o\d-", re.I), "OpenAI"),
    (re.compile(r"^llama\b", re.I), "Meta"),
    (re.compile(r"^qwen\b", re.I), "Alibaba"),
    (re.compile(r"^deepseek\b", re.I), "DeepSeek"),
    (re.compile(r"^devstral\b|^mistral\b|^codestral\b", re.I), "Mistral AI"),
    (re.compile(r"^kimi\b", re.I), "Moonshot AI"),
    (re.compile(r"^minimax\b", re.I), "MiniMax"),
    (re.compile(r"^glm-", re.I), "Zhipu AI"),
    (re.compile(r"^phi-\d", re.I), "Microsoft"),
    (re.compile(r"^r1\b", re.I), "DeepSeek"),
]

# ---------------------------------------------------------------------------
# Per-model static specs
# Key: substring (lowercased) matched against lowercased model name.
# Values fill only empty fields (never overwrite scraped data).
# ---------------------------------------------------------------------------

# fmt: off
_SPECS: list[tuple[str, dict]] = [
    # ── Anthropic ────────────────────────────────────────────────────────
    ("claude 4.5 opus",          {"provider": "Anthropic", "context_k": 200}),
    ("claude opus 4.6",          {"provider": "Anthropic", "context_k": 200}),
    ("claude 4.5 sonnet",        {"provider": "Anthropic", "context_k": 200}),
    ("claude 4 opus",            {"provider": "Anthropic", "context_k": 200}),
    ("claude 4 sonnet",          {"provider": "Anthropic", "context_k": 200}),
    ("claude 4.5 haiku",         {"provider": "Anthropic", "context_k": 200}),
    ("claude 3.7 sonnet",        {"provider": "Anthropic", "context_k": 200}),

    # ── Google ───────────────────────────────────────────────────────────
    ("gemini 3 pro",             {"provider": "Google", "context_k": 1048}),
    ("gemini 3 flash",           {"provider": "Google", "context_k": 1048}),
    ("gemini 2.5 pro",           {"provider": "Google", "context_k": 1048}),
    ("gemini 2.5 flash",         {"provider": "Google", "context_k": 1048}),
    ("gemini 2.0 flash",         {"provider": "Google", "context_k": 1048}),
    ("gemini 3 deep think",      {"provider": "Google", "context_k": 128, "coding_index": 48.0}),

    # ── OpenAI ───────────────────────────────────────────────────────────
    ("gpt-5.5 pro",              {"provider": "OpenAI", "context_k": 922, "coding_index": 59.1}),
    ("gpt-5-2",                  {"provider": "OpenAI", "context_k": 128}),
    ("gpt-5.2",                  {"provider": "OpenAI", "context_k": 128}),
    ("gpt-5.1",                  {"provider": "OpenAI", "context_k": 128}),
    ("gpt-5 mini",               {"provider": "OpenAI", "context_k": 128}),
    ("gpt-5 nano",               {"provider": "OpenAI", "context_k": 128}),
    ("gpt-5 ",                   {"provider": "OpenAI", "context_k": 128}),
    ("gpt-4.1-mini",             {"provider": "OpenAI", "context_k": 1048}),
    ("gpt-4.1",                  {"provider": "OpenAI", "context_k": 1048}),
    ("gpt-4o (2024-11",          {"provider": "OpenAI", "context_k": 128}),
    ("gpt-oss-120b",             {"provider": "OpenAI", "context_k": 128, "params_b": 120.0, "coding_index": 30.0}),
    ("o3 (2025",                 {"provider": "OpenAI", "context_k": 200}),
    ("o4-mini",                  {"provider": "OpenAI", "context_k": 128}),

    # ── DeepSeek ─────────────────────────────────────────────────────────
    ("deepseek v3.2",            {"provider": "DeepSeek", "context_k": 128, "params_b": 671.0}),
    ("deepseek v4 flash",        {"provider": "DeepSeek", "context_k": 128, "coding_index": 38.0}),

    # ── Kimi / Moonshot ──────────────────────────────────────────────────
    ("kimi k2.5",                {"provider": "Moonshot AI", "context_k": 128}),
    ("kimi k2 thinking",         {"provider": "Moonshot AI", "context_k": 128}),
    ("kimi k2 instruct",         {"provider": "Moonshot AI", "context_k": 128}),

    # ── MiniMax ──────────────────────────────────────────────────────────
    ("minimax m2.5",             {"provider": "MiniMax", "context_k": 1048, "coding_index": 46.0}),
    ("minimax m2",               {"provider": "MiniMax", "context_k": 1048, "coding_index": 38.0}),

    # ── Mistral AI ───────────────────────────────────────────────────────
    ("devstral (2512)",          {"provider": "Mistral AI", "context_k": 256, "params_b": 22.0}),
    ("devstral small",           {"provider": "Mistral AI", "context_k": 128, "params_b": 8.0}),

    # ── Qwen / Alibaba ───────────────────────────────────────────────────
    ("qwen3-coder 480b",         {"provider": "Alibaba", "context_k": 131, "params_b": 480.0, "coding_index": 48.0}),
    ("qwen3 coder 480b",         {"provider": "Alibaba", "context_k": 131, "params_b": 480.0, "coding_index": 48.0}),
    ("qwen3 next 80b",           {"provider": "Alibaba", "context_k": 131, "params_b": 80.0, "coding_index": 28.0}),
    ("qwen2.5-coder 32b",        {"provider": "Alibaba", "context_k": 128, "params_b": 32.0}),

    # ── Zhipu AI ─────────────────────────────────────────────────────────
    ("glm-5",                    {"provider": "Zhipu AI", "context_k": 128}),
    ("glm-4.6",                  {"provider": "Zhipu AI", "context_k": 128}),
    ("glm-4.5",                  {"provider": "Zhipu AI", "context_k": 128}),
    ("glm 4.5 air",              {"provider": "Zhipu AI", "context_k": 131, "coding_index": 20.0}),

    # ── Meta ─────────────────────────────────────────────────────────────
    ("llama 4 maverick",         {"provider": "Meta", "context_k": 1048, "params_b": 400.0}),
    ("llama 4 scout",            {"provider": "Meta", "context_k": 10240, "params_b": 109.0}),
    ("llama 3.3 70b",            {"provider": "Meta", "context_k": 131, "params_b": 70.0, "coding_index": 27.0}),
    ("llama 3.2 3b",             {"provider": "Meta", "context_k": 131, "params_b": 3.0,  "coding_index": 7.0}),

    # ── NVIDIA ───────────────────────────────────────────────────────────
    ("nemotron 3 super",         {"provider": "NVIDIA", "context_k": 1048, "coding_index": 34.0}),
    ("nemotron 3 nano 30b",      {"provider": "NVIDIA", "context_k": 256, "params_b": 30.0, "coding_index": 20.0}),
    ("nemotron nano 9b",         {"provider": "NVIDIA", "context_k": 128, "params_b": 9.0,  "coding_index": 13.0}),

    # ── LG AI ────────────────────────────────────────────────────────────
    ("exaone 4.5 33b",           {"provider": "LG AI Research", "context_k": 262, "params_b": 33.0, "coding_index": 24.0}),

    # ── Perplexity ───────────────────────────────────────────────────────
    ("r1 1776",                  {"provider": "Perplexity", "context_k": 128, "params_b": 671.0, "coding_index": 32.0}),

    # ── Liquid AI ────────────────────────────────────────────────────────
    ("lfm2.5-1.2b-thinking",     {"provider": "Liquid AI", "context_k": 32,  "params_b": 1.2, "coding_index": 6.0}),
    ("lfm2.5-1.2b-instruct",     {"provider": "Liquid AI", "context_k": 32,  "params_b": 1.2, "coding_index": 4.0}),

    # ── Arcee AI ─────────────────────────────────────────────────────────
    ("trinity large thinking",   {"provider": "Arcee AI", "context_k": 262, "coding_index": 30.0}),

    # ── Nous Research ────────────────────────────────────────────────────
    ("hermes 3 405b",            {"provider": "Nous Research", "context_k": 131, "params_b": 405.0, "coding_index": 22.0}),

    # ── Poolside ─────────────────────────────────────────────────────────
    ("laguna xs",                {"provider": "Poolside", "context_k": 131, "coding_index": 14.0}),
    ("laguna m",                 {"provider": "Poolside", "context_k": 131, "coding_index": 22.0}),

    # ── Venice ───────────────────────────────────────────────────────────
    ("venice: uncensored",       {"provider": "Venice", "context_k": 32,  "coding_index": 10.0}),

    # ── Baidu ────────────────────────────────────────────────────────────
    ("cobuddy",                  {"provider": "Baidu", "context_k": 131, "coding_index": 20.0}),

    # ── Microsoft ────────────────────────────────────────────────────────
    ("phi-4 multimodal",         {"provider": "Microsoft", "context_k": 128, "params_b": 5.6, "coding_index": 14.0}),
]
# fmt: on


def enrich(records: list[ModelRecord]) -> list[ModelRecord]:
    for r in records:
        _fill_provider_from_name(r)
        _fill_from_specs(r)
        _fill_free_providers(r)
    return records


def _fill_provider_from_name(r: ModelRecord) -> None:
    if r.provider:
        return
    # OpenRouter format: "Provider: Model Name (free)"
    if ": " in r.name:
        r.provider = r.name.split(": ")[0]
        return
    name_lower = r.name.lower()
    for pattern, provider in _PROVIDER_PATTERNS:
        if pattern.search(name_lower):
            r.provider = provider
            return


def _fill_from_specs(r: ModelRecord) -> None:
    name_lower = r.name.lower()
    for key, data in _SPECS:
        if key in name_lower:
            for field, value in data.items():
                if getattr(r, field) is None:
                    setattr(r, field, value)
            # don't break — a model can match multiple keys (e.g. "devstral" then "devstral (2512)")
            # but we only want the first (most specific) match for each field
            # since fields are only filled when None, later matches are harmless


# ---------------------------------------------------------------------------
# Free-provider enrichment
# ---------------------------------------------------------------------------

def _norm_for_free(s: str) -> str:
    """Normalize name for substring matching: lowercase, collapse punctuation to spaces."""
    s = re.sub(r"[:\-_()/,]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


# Normalized FCM cache — rebuilt at import time and after fcm_updater.refresh().
_FCM_NORMALIZED: list[tuple[str, list[str]]] = []


def _rebuild_fcm_cache() -> None:
    """Rebuild the normalized lookup table from FCM_PROVIDERS + EXTRA_PROVIDERS."""
    global _FCM_NORMALIZED
    combined: dict[str, list[str]] = {}
    for src in (FCM_PROVIDERS, EXTRA_PROVIDERS):
        for label, providers in src.items():
            seen = combined.setdefault(label, [])
            seen.extend(p for p in providers if p not in seen)
    _FCM_NORMALIZED = [(_norm_for_free(label), providers) for label, providers in combined.items()]


_rebuild_fcm_cache()


def _fill_free_providers(r: ModelRecord) -> None:
    """Add free providers discovered via FCM static mapping."""
    r_norm = _norm_for_free(r.name)
    new: set[str] = set()
    for label_norm, providers in _FCM_NORMALIZED:
        if label_norm in r_norm:
            new.update(providers)
    if new:
        existing = set(r.free_providers)
        merged = list(existing | new)
        # Sort by canonical priority so display is consistent.
        priority = {p: i for i, p in enumerate(PROVIDER_PRIORITY)}
        r.free_providers = sorted(merged, key=lambda p: priority.get(p, len(PROVIDER_PRIORITY)))
