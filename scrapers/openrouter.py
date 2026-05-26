from core.models import ModelRecord
from scrapers.base import BaseScraper

API_URL = "https://openrouter.ai/api/v1/models"


class OpenRouterScraper(BaseScraper):
    name = "openrouter"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get(API_URL)
        records = []
        for model in resp.json()["data"]:
            model_id: str = model["id"]
            if ":free" not in model_id:
                continue
            modality: str = model.get("architecture", {}).get("modality", "text->text")
            parts = modality.split("->") if "->" in modality else [modality, modality]
            input_mod = parts[0]
            output_mod = parts[1] if len(parts) > 1 else parts[0]
            if input_mod != "text" or output_mod != "text":
                continue
            context = model.get("context_length")
            output = (model.get("top_provider") or {}).get("max_completion_tokens")
            records.append(ModelRecord(
                name=model.get("name", model_id),
                openrouter_id=model_id,
                openrouter_name=model.get("name"),
                context_k=context // 1000 if context else None,
                output_tokens=output,
                free_providers=["OpenRouter"],
            ))
        return records
