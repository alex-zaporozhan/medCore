"""DTOs for P1 staff collaboration APIs."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NamedAdminBrief(BaseModel):
    id: UUID
    full_name: str | None = None


class StaffAttachmentBrief(BaseModel):
    id: UUID
    file_name: str
    content_type: str
    size_bytes: int


class StaffFeedPostResponse(BaseModel):
    id: UUID
    title: str | None = None
    body: str
    author: NamedAdminBrief
    created_at: datetime
    comments_count: int = 0
    likes_count: int = 0
    liked_by_me: bool = False
    attachments: list[StaffAttachmentBrief] = Field(default_factory=list)


class StaffFeedPostLikeResponse(BaseModel):
    liked: bool
    likes_count: int


class StaffFeedPostCreate(BaseModel):
    title: str | None = Field(None, max_length=500)
    body: str = Field(..., min_length=1, max_length=16000)


class StaffFeedCommentResponse(BaseModel):
    id: UUID
    body: str
    author: NamedAdminBrief
    created_at: datetime
    parent_comment_id: UUID | None = None
    in_reply_to: NamedAdminBrief | None = None
    attachments: list[StaffAttachmentBrief] = Field(default_factory=list)


class StaffFeedCommentCreate(BaseModel):
    body: str = Field(default="", max_length=8000)
    parent_comment_id: UUID | None = Field(
        None,
        description="Ответ на комментарий в том же посте; в UI показывается как «Имя, — …»",
    )


class StaffChatRoomResponse(BaseModel):
    id: UUID
    kind: str
    title: str
    task_id: UUID | None = None


class StaffChatMessageResponse(BaseModel):
    id: UUID
    body: str
    author: NamedAdminBrief
    created_at: datetime
    attachments: list[StaffAttachmentBrief] = Field(default_factory=list)


class StaffChatMessageCreate(BaseModel):
    body: str = Field(default="", max_length=8000)


class StaffCalendarEventResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    all_day: bool
    task_id: UUID | None
    reminder_minutes_before: int | None = None
    created_by: NamedAdminBrief
    participants: list[NamedAdminBrief] = Field(default_factory=list)


class StaffCalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=8000)
    starts_at: datetime
    ends_at: datetime
    all_day: bool = False
    task_id: UUID | None = None
    participant_admin_ids: list[UUID] = Field(
        default_factory=list,
        description="Участники совещания; требует права invite_staff_calendar_participants",
    )
    reminder_minutes_before: int | None = Field(
        15,
        ge=0,
        le=24 * 60,
        description="Напоминание за N минут до начала; 0 или null — без напоминания",
    )


class StaffCalendarEventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=8000)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    all_day: bool | None = None
    reminder_minutes_before: int | None = Field(None, ge=0, le=24 * 60)
    task_id: UUID | None = Field(
        None,
        description="Связь с задачей Kanban; передайте null чтобы снять привязку",
    )
    participant_admin_ids: list[UUID] | None = Field(
        None,
        description="Полная замена списка участников (при наличии права invite_staff_calendar_participants)",
    )


class CalendarEventChip(BaseModel):
    """Минимальная карточка события для day-cell рендера."""

    id: UUID
    title: str
    starts_at: datetime
    ends_at: datetime
    all_day: bool
    task_id: UUID | None
    created_by_admin_id: UUID


class CalendarDayCell(BaseModel):
    """Данные одной ячейки месяца (календарная дата + события/сигналы)."""

    date: date
    is_in_current_month: bool

    events: list[CalendarEventChip] = Field(default_factory=list)
    reminder_event_ids: list[UUID] = Field(default_factory=list)

    unseen_invite_event_ids: list[UUID] = Field(default_factory=list)
    unseen_invite_count: int = 0


class StaffCalendarNotificationSignals(BaseModel):
    unseen_invites_count: int
    reminders_due_now_count: int


class CalendarMonthRange(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: datetime = Field(alias="from")
    to: datetime


class StaffCalendarMonthGridResponse(BaseModel):
    month: CalendarMonthRange
    days: list[CalendarDayCell]
    notification_signals: StaffCalendarNotificationSignals


class StaffCalendarReminderInfo(BaseModel):
    reminder_minutes_before: int | None
    fire_at: datetime | None
    sent_at: datetime | None


class StaffCalendarCreatorAckSummary(BaseModel):
    total_participants: int
    acknowledged_participants: int


class StaffCalendarEventDetailsResponse(BaseModel):
    event: StaffCalendarEventResponse
    reminder: StaffCalendarReminderInfo
    invitation_acknowledged_at: datetime | None
    creator_ack_summary: StaffCalendarCreatorAckSummary | None = None


class StaffCalendarInvitationAckResponse(BaseModel):
    event_id: UUID
    acknowledged_at: datetime
    unseen_invite_count: int | None = None


class StaffRoomCreateDm(BaseModel):
    peer_admin_id: UUID


class StaffRoomCreateGroup(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    member_admin_ids: list[UUID] = Field(..., min_length=1)


class StaffRoomInviteCreate(BaseModel):
    """Приглашение в GROUP/TASK-комнату; вызывать может только текущий участник комнаты."""

    invitee_admin_id: UUID


class KnowledgeDocumentResponse(BaseModel):
    id: UUID
    folder_key: str
    title: str
    body_md: str
    visible_roles: list[str]
    sort_order: int
    created_by: NamedAdminBrief
    updated_at: datetime


class KnowledgeDocumentCreate(BaseModel):
    folder_key: str = Field("general", max_length=64)
    title: str = Field(..., min_length=1, max_length=255)
    body_md: str = Field(..., min_length=1, max_length=64000)
    visible_roles: list[str] = Field(default_factory=lambda: ["owner", "manager", "admin", "doctor"])
    sort_order: int = 0


class KnowledgeDocumentUpdate(BaseModel):
    folder_key: str | None = Field(None, max_length=64)
    title: str | None = Field(None, min_length=1, max_length=255)
    body_md: str | None = Field(None, min_length=1, max_length=64000)
    visible_roles: list[str] | None = None
    sort_order: int | None = None
