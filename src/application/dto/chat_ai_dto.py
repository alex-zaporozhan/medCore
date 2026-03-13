"""DTOs for AI assistant in admin chat and patient card."""

from pydantic import BaseModel


class PatientAiInsight(BaseModel):
    summary: str
    risk_flags: list[str]
    next_best_action: str | None
    ai_status: str | None = None


class ConversationSummaryResponse(BaseModel):
    summary: str
    sentiment: str | None = None
    main_issue: str | None = None
    is_conflict: bool | None = None
    is_resolved: bool | None = None
    suggested_actions: list[str] | None = None
    ai_status: str | None = None


class SuggestReplyResponse(BaseModel):
    variants: list[str]
    ai_status: str | None = None
