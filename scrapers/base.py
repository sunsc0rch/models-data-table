from abc import ABC, abstractmethod
import httpx
from core.models import ModelRecord


class BaseScraper(ABC):
    name: str = "base"
    timeout: int = 30

    async def fetch(self) -> tuple[list[ModelRecord], Exception | None]:
        """Returns (records, error). On error returns ([], exception)."""
        try:
            return await self._fetch(), None
        except Exception as exc:
            return [], exc

    @abstractmethod
    async def _fetch(self) -> list[ModelRecord]:
        ...

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
            resp = await client.get(url, **kwargs)
            resp.raise_for_status()
            return resp
