"""
Mapping from free-provider display names (as stored in ModelRecord.free_providers)
to the provider keys used in ~/.config/opencode/opencode.json under
``provider.<key>.models``.

Used by the Enter / Shift+Enter copy action to:
  * resolve which ``provider.<key>`` block the snippet should be pasted into,
  * pick the provider-specific API model ID (e.g. ``llama-3.3-70b-versatile``
    for Groq, not the display name).
"""
from core.models import ModelRecord


PROVIDER_TO_OPENCODE_KEY: dict[str, str] = {
    "OpenRouter":   "openrouter",
    "Google AI":    "google",
    "GitHub":       "github-models",
    "NIM":          "nvidia",
    "Groq":         "groq",
    "Cerebras":     "cerebras",
    "SambaNova":    "sambanova",
    "Cloudflare":   "cloudflare",
    "Mistral":      "mistral",
    "Codestral":    "codestral",
    "Pollinations": "pollinations",
    "LLM7":         "llm7",
    "Scaleway":     "scaleway",
    "OVHcloud":     "ovhcloud",
    "DashScope":    "dashscope",
    "ZAI":          "zai",
}


def resolve_api_provider(record: ModelRecord) -> str | None:
    """
    Resolve the opencode.json provider key for a record.

    Priority:
      1. First entry of free_providers (already sorted by PROVIDER_PRIORITY).
      2. Fallback to ``openrouter`` if openrouter_id is set.
      3. ``None`` when neither yields a known mapping.
    """
    if record.free_providers:
        first = record.free_providers[0]
        if first in PROVIDER_TO_OPENCODE_KEY:
            return PROVIDER_TO_OPENCODE_KEY[first]
    if record.openrouter_id:
        return "openrouter"
    return None


def resolve_model_id(
    record: ModelRecord,
    api_provider: str | None,
) -> tuple[str, str]:
    """
    Pick the best model ID for the opencode.json snippet.

    Returns ``(model_id, source)`` where ``source`` is one of:
      * ``"model_ids"``     — found in record.model_ids for the given provider
                              (most accurate, from FCM live data)
      * ``"openrouter_id"`` — fell back to record.openrouter_id (only valid for
                              the ``openrouter`` provider; otherwise returns the
                              value but marks source as fallback)
      * ``"fallback"``      — none of the above; built from display name

    The caller can use ``source`` to decide whether to surface a warning
    to the user.
    """
    if api_provider and api_provider in record.model_ids:
        return record.model_ids[api_provider], "model_ids"
    if api_provider == "openrouter" and record.openrouter_id:
        return record.openrouter_id, "openrouter_id"
    if record.openrouter_id and api_provider is None:
        return record.openrouter_id, "openrouter_id"
    return f"{record.name}:free", "fallback"
