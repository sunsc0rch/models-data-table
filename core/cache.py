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
