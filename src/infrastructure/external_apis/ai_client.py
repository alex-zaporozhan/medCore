"""Generic AI HTTP client used by ChatAiService and other AI modules."""

from typing import Any, Iterable

import httpx

from src.application.services.ai_config_service import AiProviderConfig
from src.application.dto.chat_ai_agent_dto import ChatMessage, ToolCall
from src.core.config import settings


class AiClientError(Exception):
    """Errors when calling external AI provider."""

    pass


class AiClient:
    def __init__(
        self,
        config: AiProviderConfig | None = None,
        timeout: int | None = None,
    ) -> None:
        # Fallback to global Settings if explicit config not provided
        if config is None:
            config = AiProviderConfig(
                base_url=(settings.ai_provider_base_url or "").rstrip("/"),
                api_key=settings.ai_provider_api_key or "",
                model=settings.ai_provider_model,
                allow_personal_data=False,
                provider_type="external",
            )

        self._config = config
        self._timeout = timeout or settings.ai_timeout_seconds

    def is_configured(self) -> bool:
        return bool(self._config and self._config.base_url)

    async def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call external AI provider with generic chat-completions-like payload."""
        if not self.is_configured():
            raise AiClientError("AI provider base URL is not configured")

        assert self._config is not None  # for type checkers
        base_url = self._config.base_url.rstrip("/")
        api_key = self._config.api_key

        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def chat_with_tools(
        self,
        messages: Iterable[ChatMessage],
        tools_schema: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], list[ToolCall]]:
        """
        High-level helper for chat with function calling.

        Returns raw provider response and parsed ToolCall list (if any).
        """
        payload: dict[str, Any] = {
            "model": self._config.model if self._config else settings.ai_provider_model,
            "messages": [m.model_dump() for m in messages],
        }
        if tools_schema is not None:
            payload["tools"] = tools_schema
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        data = await self.complete(payload)
        tool_calls: list[ToolCall] = []

        try:
            choices = data.get("choices") or []
            if not choices:
                return data, tool_calls
            message = choices[0].get("message") or {}
            tool_calls_raw = message.get("tool_calls") or []
            for tc in tool_calls_raw:
                fn = tc.get("function") or {}
                tool_calls.append(
                    ToolCall(
                        id=str(tc.get("id") or ""),
                        name=str(fn.get("name") or ""),
                        arguments_json=str(fn.get("arguments") or "{}"),
                    )
                )
        except Exception:
            # If provider does not follow expected schema, we just return empty tool_calls.
            return data, []

        return data, tool_calls

