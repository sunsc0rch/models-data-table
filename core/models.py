from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelRecord:
    name: str
    provider: Optional[str] = None
    params_b: Optional[float] = None
    context_k: Optional[int] = None
    output_tokens: Optional[int] = None
    swe_bench_pct: Optional[float] = None
    coding_index: Optional[float] = None
    free_providers: list[str] = field(default_factory=list)
    openrouter_id: Optional[str] = None
    openrouter_name: Optional[str] = None
