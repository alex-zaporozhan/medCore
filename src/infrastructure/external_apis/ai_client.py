"""Generic AI HTTP client used by ChatAiService."""

from typing import Any

import httpx

from src.core.config import settings


class AiClientError(Exception):
    """Errors when calling external AI provider."""

    pass


class AiClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self._base_url = (base_url or settings.ai_provider_base_url or "").rstrip("/")
        self._api_key = api_key or settings.ai_provider_api_key
        self._timeout = timeout or settings.ai_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self._base_url)

    async def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call external AI provider with generic chat-completions-like payload."""
        if not self.is_configured():
            raise AiClientError("AI provider base URL is not configured")

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

