"""DTOs for function-calling AI agent in omnichannel chats."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RoleType = Literal["user", "assistant", "tool", "system"]


class ChatMessage(BaseModel):
    role: RoleType
    content: str
    name: str | None = None


class ToolCall(BaseModel):
    id: str
    name: str
    arguments_json: str = Field(
        description="Raw JSON string with tool arguments as returned by the LLM provider."
    )


class ToolMessage(BaseModel):
    tool_call_id: str
    name: str
    content: str


class AgentResult(BaseModel):
    reply_message: ChatMessage
    tool_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured events for logging/audit; schema will be refined in logging phase.",
    )
    error: str | None = None

