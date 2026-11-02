"""Conservative deduplication for provider and benchmark model aliases."""

import re
from dataclasses import fields, replace

from core.models import ModelRecord

_EFFORT_RE = re.compile(
    r"\([^)]*(?:high|low|medium|max|xhigh|non[- ]?reasoning|reasoning|"
    r"default fallback|no think|thinking)[^)]*\)",
    re.I,
)
_DATE_RE = re.compile(r"(?<!\d)20\d{2}[-_. ]?\d{2}[-_. ]?\d{2}(?!\d)")
_SHORT_DATE_RE = re.compile(r"\((?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\)")


def model_key(name: str) -> str:
    """Normalize display/config aliases without dropping model size/version."""
    value = name.casefold().strip()
    value = re.sub(r"\s*:\s*free\b", " ", value)
    value = re.sub(r"\s+\(free\)", " ", value)
    # Provider-qualified display names, e.g. "Meta: Llama 3.3 70B".
    value = re.sub(r"^[a-z0-9_-]{2,20}:\s*", "", value)
    value = _EFFORT_RE.sub(" ", value)
    value = _DATE_RE.sub(" ", value)
    value = _SHORT_DATE_RE.sub(" ", value)
    value = re.sub(r"\b(?:preview|experimental|exp)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def deduplicate(records: list[ModelRecord]) -> list[ModelRecord]:
    """Combine exact normalized aliases, retaining distinct model sizes/versions."""
    groups: dict[str, ModelRecord] = {}
    for record in records:
        key = model_key(record.name)
        clean_name = _clean_display_name(record.name)
        current = groups.get(key)
        if current is None:
            groups[key] = replace(record, name=clean_name)
            continue
        _combine_alias(current, record)
    return list(groups.values())


def _combine_alias(base: ModelRecord, other: ModelRecord) -> None:
    list_fields = {"free_providers"}
    dict_fields = {"model_ids"}
    score_fields = {"swe_bench_pct", "aider_pct", "coding_index"}
    for model_field in fields(base):
        name = model_field.name
        if name == "name":
            continue
        left, right = getattr(base, name), getattr(other, name)
        if name in list_fields:
            setattr(base, name, list(dict.fromkeys(left + right)))
        elif name in dict_fields:
            setattr(base, name, {**right, **left})
        elif name in score_fields:
            if right is not None and (left is None or right > left):
                setattr(base, name, right)
        elif isinstance(left, bool):
            setattr(base, name, left or right)
        elif left is None and right is not None:
            setattr(base, name, right)


def _clean_display_name(name: str) -> str:
    value = re.sub(r"^[a-z0-9_-]{2,20}:\s*", "", name, flags=re.I)
    value = re.sub(r"\s*:\s*free\b", "", value, flags=re.I)
    value = re.sub(r"\s+\(free\)", "", value, flags=re.I)
    value = _EFFORT_RE.sub("", value)
    value = _DATE_RE.sub("", value)
    value = _SHORT_DATE_RE.sub("", value)
    value = re.sub(r"\b(?:preview|experimental|exp)\b", "", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip(" -_:")
    return value or name
