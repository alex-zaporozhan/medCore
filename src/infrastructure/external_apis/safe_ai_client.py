"""Safe AI client that always sanitizes text payloads before external calls."""

from typing import Any, Iterable

from src.core.ai_sanitizer import AiSanitizer
from src.infrastructure.external_apis.ai_client import AiClient
from src.application.dto.chat_ai_agent_dto import ChatMessage as AgentChatMessage, ToolCall


class SafeAiClient:
    """Wrapper around AiClient that sanitizes text fields."""

    def __init__(self, ai_client: AiClient | None = None, sanitizer: AiSanitizer | None = None) -> None:
        self._client = ai_client or AiClient()
        self._sanitizer = sanitizer or AiSanitizer()

    def is_configured(self) -> bool:
        return self._client.is_configured()

    async def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sanitize known text fields in payload and call underlying AiClient."""
        safe_payload = self._sanitize_messages(payload)
        return await self._client.complete(safe_payload)

    async def chat_with_tools(
        self,
        messages: Iterable[AgentChatMessage],
        tools_schema: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], list[ToolCall]]:
        """
        Wrapper around AiClient.chat_with_tools that applies sanitizer to message content.
        """
        sanitized_messages: list[AgentChatMessage] = []
        for m in messages:
            content = m.content
            if isinstance(content, str):
                safe_content = self._sanitizer.sanitize(content).sanitized
            else:
                safe_content = content
            sanitized_messages.append(
                AgentChatMessage(
                    role=m.role,
                    content=safe_content,
                    name=m.name,
                )
            )
        return await self._client.chat_with_tools(
            messages=sanitized_messages,
            tools_schema=tools_schema,
            tool_choice=tool_choice,
        )

    def _sanitize_messages(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Sanitize `messages[n].content` in-place copy of payload."""
        safe = dict(payload)
        messages = safe.get("messages")
        if isinstance(messages, list):
            new_messages: list[dict[str, Any]] = []
            for msg in messages:
                if not isinstance(msg, dict):
                    new_messages.append(msg)
                    continue
                msg_copy = dict(msg)
                content = msg_copy.get("content")
                if isinstance(content, str):
                    msg_copy["content"] = self._sanitizer.sanitize(content).sanitized
                new_messages.append(msg_copy)
            safe["messages"] = new_messages
        return safe

