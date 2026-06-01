"""Tests for the _fill_from_litellm enrichment function in core.static_data."""
from core import litellm_data
from core.litellm_data import LITELLM_DATA
from core.models import ModelRecord
from core.static_data import (
    _fill_from_litellm,
    _litellm_normalize,
    invalidate_litellm_cache,
)


def _record(name: str, **kwargs) -> ModelRecord:
    """Build a ModelRecord with all enrichment-relevant fields None by default."""
    defaults = dict(
        name=name,
        provider=None,
        context_k=None,
        output_tokens=None,
        supports_function_calling=False,
        supports_vision=False,
    )
    defaults.update(kwargs)
    return ModelRecord(**defaults)


def load_entries(entries: dict) -> None:
    """Reset LiteLLM state and load the supplied entries."""
    LITELLM_DATA.clear()
    LITELLM_DATA.update(entries)
    invalidate_litellm_cache()


def test_direct_match_fills_output_tokens():
    load_entries({
        "claude-3-5-sonnet": {
            "context_k": 200, "output_tokens": 8192,
            "supports_function_calling": True, "supports_vision": True,
        },
    })
    r = _record("Claude 3.5 Sonnet")
    _fill_from_litellm(r)
    assert r.context_k == 200
    assert r.output_tokens == 8192
    assert r.supports_function_calling is True
    assert r.supports_vision is True


def test_direct_match_ignores_provider_prefix_and_parentheticals():
    load_entries({
        "qwen3-coder-480b-a35b": {
            "context_k": 262, "output_tokens": 262144,
            "supports_function_calling": True, "supports_vision": False,
        },
    })
    r = _record("Qwen: Qwen3 Coder 480B A35B (free)")
    _fill_from_litellm(r)
    assert r.context_k == 262
    assert r.output_tokens == 262144


def test_substring_match_catches_date_tagged_variant():
    """A near-equivalent string (date tag) should match via substring."""
    load_entries({
        "ministral-3-3b-2512": {
            "context_k": 128, "output_tokens": 32000,
            "supports_function_calling": True, "supports_vision": False,
        },
    })
    # 14/20 = 70% → passes the length-ratio threshold
    r = _record("Ministral 3 3B")
    _fill_from_litellm(r)
    assert r.context_k == 128
    assert r.output_tokens == 32000


def test_substring_match_rejects_too_short_match():
    """A 4-char LiteLLM name can't match a 30-char query (avoid false matches)."""
    load_entries({
        "kimi": {
            "context_k": 999, "output_tokens": 999,
            "supports_function_calling": False, "supports_vision": False,
        },
    })
    r = _record("Kimi Linear 48B A3B Instruct")  # normalizes to "kimi linear 48b a3b"
    _fill_from_litellm(r)
    # Should NOT match: "kimi" is only 4 chars and 4/24 = 17% < 70% threshold
    assert r.context_k is None
    assert r.output_tokens is None


def test_never_overwrites_existing_values():
    """Scraped context_k/output_tokens are preserved; True booleans stay True."""
    load_entries({
        "gpt-4o": {
            "context_k": 999, "output_tokens": 999,
            "supports_function_calling": True, "supports_vision": True,
        },
    })
    # Record has scraped values; LiteLLM must not clobber them.
    r = _record("GPT-4o", context_k=128, output_tokens=16384,
                supports_function_calling=True, supports_vision=True)
    _fill_from_litellm(r)
    assert r.context_k == 128
    assert r.output_tokens == 16384
    # True stays True; LiteLLM cannot downgrade.
    assert r.supports_function_calling is True
    assert r.supports_vision is True


def test_upgrades_unspecified_boolean_to_true():
    """False (unspecified) is upgraded to True when LiteLLM confirms it."""
    load_entries({
        "gpt-4o": {
            "context_k": 128, "output_tokens": 16384,
            "supports_function_calling": True, "supports_vision": True,
        },
    })
    r = _record("GPT-4o", context_k=128, output_tokens=16384,
                supports_function_calling=False, supports_vision=True)
    _fill_from_litellm(r)
    # FC upgraded to True; vision already True, stays True
    assert r.supports_function_calling is True
    assert r.supports_vision is True


def test_no_match_leaves_fields_alone():
    load_entries({
        "gpt-4o": {
            "context_k": 128, "output_tokens": 16384,
            "supports_function_calling": True, "supports_vision": True,
        },
    })
    r = _record("Poolside: Laguna XS.2 (free)")
    _fill_from_litellm(r)
    assert r.context_k is None
    assert r.output_tokens is None
    assert r.supports_function_calling is False
    assert r.supports_vision is False


def test_empty_litellm_data_is_noop():
    load_entries({})
    r = _record("Claude 3.5 Sonnet")
    _fill_from_litellm(r)
    assert r.context_k is None
    assert r.output_tokens is None


def test_normalize_strips_parens_and_prefix():
    assert _litellm_normalize("Qwen: Qwen3 Coder (free)") == "qwen3 coder"
    assert _litellm_normalize("DeepSeek V3.2 Reasoner (high)") == "deepseek 2 reasoner"
    assert _litellm_normalize("Claude 4.5 Sonnet (20250929)") == "claude 4 5 sonnet"
    assert _litellm_normalize("GPT-5-2 (high reasoning)") == "gpt 5 2"
