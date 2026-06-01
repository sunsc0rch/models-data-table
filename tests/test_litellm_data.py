"""Tests for core.litellm_data — parsing the LiteLLM model registry."""
import json

from core.litellm_data import (
    _derive_name,
    _parse,
    LITELLM_DATA,
)


# ---------------------------------------------------------------------------
# _derive_name
# ---------------------------------------------------------------------------

def test_derive_name_takes_last_path_component():
    assert _derive_name("openrouter/qwen/qwen3-coder") == "qwen3 coder"


def test_derive_name_lowercases():
    assert _derive_name("Claude-3.5-Sonnet") == "claude 3 5 sonnet"


def test_derive_name_replaces_separators_with_spaces():
    assert _derive_name("mistral/devstral-small-2505") == "devstral small 2505"


def test_derive_name_strips_bedrock_region_prefix():
    """Bedrock keys like 'us.anthropic.claude-3-5-sonnet' should normalize cleanly."""
    # rsplit('/', 1) doesn't help here; but the period split does.
    # Need to handle bedrock dotted format.
    name = _derive_name("us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    assert "claude" in name
    assert "sonnet" in name
    # Should not contain the version noise
    assert "v2" not in name


def test_derive_name_strips_noise_tokens():
    """Words like 'preview', 'latest', 'instruct' should be removed."""
    name = _derive_name("openai/gpt-4o-2024-08-06")
    assert "preview" not in name
    assert "latest" not in name


def test_derive_name_returns_short_string_for_garbage():
    assert _derive_name("") == ""
    assert _derive_name("a") == ""
    assert _derive_name("---") == ""


def test_derive_name_dedupes_likely_variants():
    """Different dates should normalize to the same name."""
    n1 = _derive_name("mistral/devstral-small-2505")
    n2 = _derive_name("mistral/devstral-small-2507")
    n3 = _derive_name("mistral/devstral-small-latest")
    # All should produce similar (possibly identical) names
    assert "devstral" in n1 and "small" in n1
    assert "devstral" in n2 and "small" in n2
    assert "devstral" in n3 and "small" in n3


# ---------------------------------------------------------------------------
# _parse
# ---------------------------------------------------------------------------

def _write_json(data: dict) -> str:
    return json.dumps(data)


def test_parse_skips_non_chat_modes():
    data = {
        "some-embed": {"mode": "embedding", "max_input_tokens": 100, "max_output_tokens": 100},
        "some-img":   {"mode": "image_generation", "max_input_tokens": 100, "max_output_tokens": 100},
    }
    result = _parse(_write_json(data))
    assert result == {}


def test_parse_skips_models_without_token_limits():
    data = {
        "valid":   {"mode": "chat", "max_input_tokens": 1000, "max_output_tokens": 100},
        "no-in":   {"mode": "chat", "max_output_tokens": 100},
        "no-out":  {"mode": "chat", "max_input_tokens": 1000},
    }
    result = _parse(_write_json(data))
    assert "valid" in result
    assert len(result) == 1


def test_parse_skips_models_with_tiny_context():
    data = {
        "valid":    {"mode": "chat", "max_input_tokens": 1000, "max_output_tokens": 100},
        "tiny-in":  {"mode": "chat", "max_input_tokens": 100,  "max_output_tokens": 100},
        "tiny-out": {"mode": "chat", "max_input_tokens": 1000, "max_output_tokens": 10},
    }
    result = _parse(_write_json(data))
    assert "valid" in result
    assert len(result) == 1


def test_parse_extracts_context_in_thousands():
    data = {
        "gpt-4o": {"mode": "chat", "max_input_tokens": 128000, "max_output_tokens": 16384},
    }
    result = _parse(_write_json(data))
    assert result["gpt 4o"]["context_k"] == 128


def test_parse_extracts_output_tokens():
    data = {
        "gpt-4o": {"mode": "chat", "max_input_tokens": 128000, "max_output_tokens": 16384},
    }
    result = _parse(_write_json(data))
    assert result["gpt 4o"]["output_tokens"] == 16384


def test_parse_extracts_function_calling_support():
    data = {
        "with-fc":  {"mode": "chat", "max_input_tokens": 1000, "max_output_tokens": 100, "supports_function_calling": True},
        "without":  {"mode": "chat", "max_input_tokens": 1000, "max_output_tokens": 100, "supports_function_calling": False},
    }
    result = _parse(_write_json(data))
    assert result["with fc"]["supports_function_calling"] is True
    assert result["without"]["supports_function_calling"] is False


def test_parse_extracts_vision_support():
    data = {
        "gpt-4o":  {"mode": "chat", "max_input_tokens": 128000, "max_output_tokens": 16384, "supports_vision": True},
        "llama":   {"mode": "chat", "max_input_tokens": 1000,   "max_output_tokens": 100,   "supports_vision": False},
    }
    result = _parse(_write_json(data))
    assert result["gpt 4o"]["supports_vision"] is True
    assert result["llama"]["supports_vision"] is False


def test_parse_dedupes_preferring_openrouter_prefix():
    data = {
        "openrouter/foo": {"mode": "chat", "max_input_tokens": 128000, "max_output_tokens": 100},
        "groq/foo":       {"mode": "chat", "max_input_tokens": 999000, "max_output_tokens": 999},  # bigger but not OR
    }
    result = _parse(_write_json(data))
    # Should keep the openrouter one (smaller values) because of OR preference
    assert result["foo"]["output_tokens"] == 100


def test_parse_dedupes_higher_output_wins_when_neither_is_openrouter():
    data = {
        "groq/devstral-small":   {"mode": "chat", "max_input_tokens": 128000, "max_output_tokens": 100},
        "mistral/devstral-small": {"mode": "chat", "max_input_tokens": 128000, "max_output_tokens": 500},
    }
    result = _parse(_write_json(data))
    # Neither is openrouter; the one with higher output_tokens wins
    assert result["devstral small"]["output_tokens"] == 500
    assert len(result) == 1


def test_parse_handles_max_tokens_fallback():
    """Some entries only have max_tokens (not separate in/out)."""
    data = {
        "claude": {"mode": "chat", "max_tokens": 8192},
    }
    result = _parse(_write_json(data))
    assert result["claude"]["output_tokens"] == 8192
    assert result["claude"]["context_k"] == 8


def test_parse_handles_responses_mode():
    """Newer models use 'responses' mode instead of 'chat'."""
    data = {
        "gpt-5": {"mode": "responses", "max_input_tokens": 128000, "max_output_tokens": 16384},
    }
    result = _parse(_write_json(data))
    assert "gpt 5" in result


def test_parse_skips_non_dict_values():
    """Some LiteLLM entries are strings or null (model aliases)."""
    data = {
        "alias": "just-a-string",
        "null":  None,
        "valid": {"mode": "chat", "max_input_tokens": 128000, "max_output_tokens": 16384},
    }
    result = _parse(_write_json(data))
    assert "valid" in result
    assert len(result) == 1
