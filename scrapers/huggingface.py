"""
HuggingFace Hub API — parameter counts for open-weight models.
Queries safetensors metadata for a curated list of public HF model IDs.
Only covers non-gated (publicly accessible) models.
"""

import asyncio
from core.models import ModelRecord
from scrapers.base import BaseScraper

HF_API = "https://huggingface.co/api/models"

# Mapping: display name (as it appears in ModelRecord.name) → HF model ID.
# Only include non-gated public repos — gated models return 401.
HF_MODEL_IDS: dict[str, str] = {
    "Qwen2.5-Coder 32B Instruct":         "Qwen/Qwen2.5-Coder-32B-Instruct",
    "Devstral small (2512)":               "mistralai/Devstral-Small-2505",
    "EXAONE 4.5 33B (Non-reasoning)":     "LGAI-EXAONE/EXAONE-4.5-33B",
    "Llama 3.3 70B Instruct":             "meta-llama/Llama-3.3-70B-Instruct",
    "Llama 3.2 3B Instruct":              "meta-llama/Llama-3.2-3B-Instruct",
    "Meta: Llama 3.3 70B Instruct (free)": "meta-llama/Llama-3.3-70B-Instruct",
    "Meta: Llama 3.2 3B Instruct (free)": "meta-llama/Llama-3.2-3B-Instruct",
    "Qwen: Qwen3 Next 80B A3B Instruct (free)": "Qwen/Qwen3-80B",
    "Nous: Hermes 3 405B Instruct (free)": "NousResearch/Hermes-3-Llama-3.1-405B",
    "Qwen3-Coder 480B/A35B Instruct":     "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    "Qwen: Qwen3 Coder 480B A35B (free)": "Qwen/Qwen3-Coder-480B-A35B-Instruct",
    "Phi-4 Multimodal Instruct":          "microsoft/Phi-4-multimodal-instruct",
    "R1 1776":                            "perplexity-ai/r1-1776",
    "DeepSeek: DeepSeek V4 Flash (free)": "deepseek-ai/DeepSeek-V4-Flash",
    "Devstral (2512)":                    "mistralai/Devstral-Medium-2505",
}


class HuggingFaceScraper(BaseScraper):
    name = "huggingface"

    async def _fetch(self) -> list[ModelRecord]:
        tasks = {
            display: self._fetch_params(hf_id)
            for display, hf_id in HF_MODEL_IDS.items()
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        records = []
        for display, result in zip(tasks.keys(), results):
            if isinstance(result, Exception) or result is None:
                continue
            records.append(ModelRecord(name=display, params_b=result))
        return records

    async def _fetch_params(self, hf_id: str) -> float | None:
        try:
            resp = await self._get(f"{HF_API}/{hf_id}")
            data = resp.json()
            st = data.get("safetensors") or {}
            total = st.get("total")
            if total:
                return round(total / 1e9, 1)
        except Exception:
            pass
        return None
