from dataclasses import fields
from rapidfuzz import process, fuzz
import re
from core.models import ModelRecord

THRESHOLD = 85


def _normalize(s: str) -> str:
    """Normalize model name for fuzzy matching by removing separators and lowercasing."""
    return re.sub(r'[\s\-_]', '', s.lower())


def merge(scraper_results: list[list[ModelRecord]]) -> list[ModelRecord]:
    merged: dict[str, ModelRecord] = {}

    for records in scraper_results:
        for record in records:
            match = process.extractOne(
                record.name,
                merged.keys(),
                processor=_normalize,
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
