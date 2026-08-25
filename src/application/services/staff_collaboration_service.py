"""P1 Staff Core: feed, staff chat, calendar, knowledge (separate from patient/omni chat)."""

from __future__ import annotations

import os
import re
import uuid
import hashlib
import shutil
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

from zlib import crc32

from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.staff_collab_dto import (
    CalendarDayCell,
    CalendarEventChip,
    CalendarMonthRange,
    StaffCalendarCreatorAckSummary,
    StaffCalendarEventDetailsResponse,
    KnowledgeDocumentCreate,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
    NamedAdminBrief,
    StaffAttachmentBrief,
    StaffCalendarEventCreate,
    StaffCalendarEventResponse,
    StaffCalendarEventUpdate,
    StaffCalendarInvitationAckResponse,
    StaffCalendarMonthGridResponse,
    StaffCalendarNotificationSignals,
    StaffCalendarReminderInfo,
    StaffChatMessageCreate,
    StaffChatMessageResponse,
    StaffChatRoomResponse,
    StaffFeedCommentCreate,
    StaffFeedCommentResponse,
    StaffFeedCommentUpdate,
    StaffFeedPostCreate,
    StaffFeedPostResponse,
    StaffAnnouncementPublishPolicyRow,
    StaffAnnouncementPublishPolicyResponse,
    StaffAnnouncementPublishPolicyAuditRow,
    StaffAnnouncementPublishPolicyAuditListResponse,
    StaffRoomCreateGroup,
    StaffRoomInviteCreate,
)
from src.core.datetime_utils import utc_now_naive
from src.core.config import settings
from src.domain.entities.admin_user import AdminUser, EMPLOYMENT_ACTIVE
from src.domain.entities.knowledge_document import KnowledgeDocument
from src.domain.entities.staff_calendar_event import StaffCalendarEvent
from src.domain.entities.staff_calendar_event_participant import StaffCalendarEventParticipant
from src.domain.entities.staff_calendar_event_invitation import StaffCalendarEventInvitation
from src.domain.entities.staff_calendar_reminder_delivery import StaffCalendarReminderDelivery
from src.domain.entities.staff_chat_message import StaffChatMessage
from src.domain.entities.staff_chat_message_attachment import StaffChatMessageAttachment
from src.domain.entities.staff_chat_room import StaffChatRoom
from src.domain.entities.staff_chat_room_member import StaffChatRoomMember
from src.domain.entities.staff_feed_comment import StaffFeedComment
from src.domain.entities.staff_feed_comment_attachment import StaffFeedCommentAttachment
from src.domain.entities.staff_feed_post import StaffFeedPost
from src.domain.entities.staff_feed_post_ack import StaffFeedPostAck
from src.domain.entities.staff_feed_post_attachment import StaffFeedPostAttachment
from src.domain.entities.staff_feed_post_like import StaffFeedPostLike
from src.domain.entities.staff_announcement_publish_policy import StaffAnnouncementPublishPolicy
from src.domain.entities.staff_announcement_publish_policy_audit import (
    StaffAnnouncementPublishPolicyAudit,
)
from src.domain.entities.task import Task
from src.domain.entities.task_assignee import TaskAssignee
from src.domain.entities.role import Role
from src.domain.entities.user_role import UserRole
from src.infrastructure.database.redis_client import get_redis
from src.core.metrics import chat_dedup_hits_total
from src.domain.entities.staff_profile import StaffProfile

GENERAL_ROOM_KIND = "GENERAL"
DM_KIND = "DM"
GROUP_KIND = "GROUP"
TASK_KIND = "TASK"

MEMBERSHIP_TASK_CORE = "task_core"
MEMBERSHIP_INVITE = "invite"
MEMBERSHIP_GENERAL = "general"
MEMBERSHIP_GROUP = "group"
MEMBERSHIP_DM = "dm"

STAFF_CHAT_DEDUP_TTL_SECONDS = 15

def _sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "file")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", base)[:200] or "file"


def _as_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dt_naive_utc(dt: datetime) -> datetime:
    """Persist calendar timestamps as naive UTC (columns are TIMESTAMP WITHOUT TIME ZONE)."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _staff_chat_dedup_key(*, clinic_id: UUID, room_id: UUID, sender_admin_id: UUID, body: str) -> str:
    base = f"{clinic_id}|{room_id}|{sender_admin_id}|{(body or '').strip()[:512]}"
    h = hashlib.sha256(base.encode('utf-8', errors='ignore')).hexdigest()
    return f"dedup:staff_chat:{room_id}:{h}"


def _sniff_magic(buf: bytes) -> str | None:
    if not buf:
        return None
    if buf.startswith(b"%PDF-"):
        return "application/pdf"
    if buf.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if buf.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if buf.startswith(b"GIF87a") or buf.startswith(b"GIF89a"):
        return "image/gif"
    if buf.startswith(b"RIFF") and buf[8:12] == b"WEBP":
        return "image/webp"
    return None


def _knowledge_visible(user_roles: set[str], visible_roles: list[str] | None) -> bool:
    if not visible_roles:
        return True
    return bool(user_roles.intersection(set(visible_roles)))


class StaffCollaborationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _ensure_calendar_event_invitations(
        self,
        *,
        clinic_id: UUID,
        event_id: UUID,
        invitee_admin_ids: list[UUID],
    ) -> None:
        """Create invitation rows for invitees that don't have an invitation yet."""
        if not invitee_admin_ids:
            return
        existing_res = await self._session.execute(
            select(StaffCalendarEventInvitation.invitee_admin_id).where(
                StaffCalendarEventInvitation.event_id == event_id,
                StaffCalendarEventInvitation.invitee_admin_id.in_(list(invitee_admin_ids)),
            )
        )
        existing = set(existing_res.scalars().all())
        for aid in invitee_admin_ids:
            if aid in existing:
                continue
            self._session.add(
                StaffCalendarEventInvitation(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    event_id=event_id,
                    invitee_admin_id=aid,
                    acknowledged_at=None,
                )
            )
        await self._session.flush()

    async def _delete_calendar_event_invitations(
        self,
        *,
        event_id: UUID,
        invitee_admin_ids: list[UUID],
    ) -> None:
        if not invitee_admin_ids:
            return
        await self._session.execute(
            delete(StaffCalendarEventInvitation).where(
                StaffCalendarEventInvitation.event_id == event_id,
                StaffCalendarEventInvitation.invitee_admin_id.in_(list(invitee_admin_ids)),
            )
        )
        await self._session.flush()

    async def revoke_staff_chat_memberships_for_admin(self, admin_id: UUID) -> None:
        """Удалить участие во всех комнатах (при увольнении)."""
        await self._session.execute(delete(StaffChatRoomMember).where(StaffChatRoomMember.admin_id == admin_id))

    async def _is_room_member(self, room_id: UUID, admin_id: UUID) -> bool:
        res = await self._session.execute(
            select(StaffChatRoomMember.admin_id).where(
                StaffChatRoomMember.room_id == room_id,
                StaffChatRoomMember.admin_id == admin_id,
            )
        )
        return res.scalar_one_or_none() is not None

    async def _sync_general_room_members(self, clinic_id: UUID, room_id: UUID) -> None:
        res = await self._session.execute(
            select(AdminUser.id).where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.deleted_at.is_(None),
                AdminUser.employment_status == EMPLOYMENT_ACTIVE,
            )
        )
        for aid in res.scalars().all():
            if await self._is_room_member(room_id, aid):
                continue
            self._session.add(
                StaffChatRoomMember(
                    room_id=room_id,
                    admin_id=aid,
                    membership_kind=MEMBERSHIP_GENERAL,
                )
            )

    async def sync_task_room_members_for_task(self, clinic_id: UUID, task_id: UUID) -> None:
        """Вызывать после смены исполнителя/постановщика задачи: синхронизировать TASK-комнату."""
        task = await self._session.get(Task, task_id)
        if task is None or task.clinic_id != clinic_id:
            return
        res = await self._session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.task_id == task_id,
                StaffChatRoom.clinic_id == clinic_id,
            )
        )
        room = res.scalar_one_or_none()
        if room is None:
            return
        await self._sync_task_room_members(room.id, task)

    async def _task_core_admin_ids(self, task: Task) -> set[UUID]:
        desired: set[UUID] = {x for x in (task.creator_id, task.assignee_id) if x is not None}
        res = await self._session.execute(
            select(TaskAssignee.admin_id).where(TaskAssignee.task_id == task.id)
        )
        for aid in res.scalars().all():
            desired.add(aid)
        return desired

    async def _sync_task_room_members(self, room_id: UUID, task: Task) -> None:
        """Постановщик/исполнитель как task_core; при смене — удаление старого task_core. Приглашённые (invite) не трогаем."""
        res = await self._session.execute(select(StaffChatRoom).where(StaffChatRoom.id == room_id))
        room = res.scalar_one_or_none()
        if room is None or room.kind != TASK_KIND:
            return
        desired = await self._task_core_admin_ids(task)
        stmt = delete(StaffChatRoomMember).where(
            StaffChatRoomMember.room_id == room_id,
            StaffChatRoomMember.membership_kind == MEMBERSHIP_TASK_CORE,
        )
        if desired:
            stmt = stmt.where(~StaffChatRoomMember.admin_id.in_(list(desired)))
        await self._session.execute(stmt)
        for aid in desired:
            ex = await self._session.execute(
                select(StaffChatRoomMember).where(
                    StaffChatRoomMember.room_id == room_id,
                    StaffChatRoomMember.admin_id == aid,
                )
            )
            row = ex.scalar_one_or_none()
            if row is None:
                self._session.add(
                    StaffChatRoomMember(
                        room_id=room_id,
                        admin_id=aid,
                        membership_kind=MEMBERSHIP_TASK_CORE,
                    )
                )
            else:
                row.membership_kind = MEMBERSHIP_TASK_CORE

    async def _admin_brief(self, admin_id: UUID) -> NamedAdminBrief:
        res = await self._session.execute(
            select(AdminUser.id, AdminUser.full_name, StaffProfile.avatar_s3_key)
            .select_from(AdminUser)
            .outerjoin(StaffProfile, StaffProfile.admin_id == AdminUser.id)
            .where(AdminUser.id == admin_id)
            .limit(1)
        )
        row = res.first()
        if row is None:
            return NamedAdminBrief(id=admin_id, full_name=None, avatar_url=None)
        aid, full_name, avatar_key = row
        avatar_url = f"/v1/admin/staff/avatars/{aid}" if avatar_key else None
        return NamedAdminBrief(id=aid, full_name=full_name, avatar_url=avatar_url)

    async def ensure_general_room(self, clinic_id: UUID) -> StaffChatRoom:
        res = await self._session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.clinic_id == clinic_id,
                StaffChatRoom.kind == GENERAL_ROOM_KIND,
            )
        )
        room = res.scalar_one_or_none()
        if room:
            return room
        room = StaffChatRoom(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            kind=GENERAL_ROOM_KIND,
            title="Общий чат",
        )
        self._session.add(room)
        await self._session.flush()
        return room

    async def list_chat_rooms(self, clinic_id: UUID, admin_id: UUID) -> list[StaffChatRoomResponse]:
        general = await self.ensure_general_room(clinic_id)
        await self._sync_general_room_members(clinic_id, general.id)
        await self._session.flush()
        member_res = await self._session.execute(
            select(StaffChatRoom, StaffChatRoomMember.last_read_at)
            .select_from(StaffChatRoom)
            .join(StaffChatRoomMember, StaffChatRoomMember.room_id == StaffChatRoom.id)
            .where(
                StaffChatRoom.clinic_id == clinic_id,
                StaffChatRoomMember.admin_id == admin_id,
            )
        )
        member_rows = list(member_res.all())
        rooms = [r for r, _lr in member_rows]
        room_ids = [r.id for r in rooms]
        if not room_ids:
            return []

        # Last message per room (single shot).
        last_at_sub = (
            select(
                StaffChatMessage.room_id.label("room_id"),
                func.max(StaffChatMessage.created_at).label("last_at"),
            )
            .where(
                StaffChatMessage.clinic_id == clinic_id,
                StaffChatMessage.room_id.in_(room_ids),
            )
            .group_by(StaffChatMessage.room_id)
            .subquery()
        )

        # NOTE: Postgres doesn't support MAX(uuid). We join on MAX(created_at) and pick the first row per room.
        last_msg_res = await self._session.execute(
            select(
                StaffChatMessage.id,
                StaffChatMessage.room_id,
                StaffChatMessage.body,
                StaffChatMessage.created_at,
                StaffChatMessage.author_admin_id,
            )
            .select_from(StaffChatMessage)
            .join(
                last_at_sub,
                (last_at_sub.c.room_id == StaffChatMessage.room_id)
                & (last_at_sub.c.last_at == StaffChatMessage.created_at),
            )
            .order_by(StaffChatMessage.room_id.asc(), StaffChatMessage.created_at.desc(), StaffChatMessage.id.desc())
        )
        last_msg_by_room: dict[UUID, tuple[UUID, str, datetime, UUID]] = {}
        for mid, rid, body, created_at, author_id in last_msg_res.all():
            if rid in last_msg_by_room:
                continue
            last_msg_by_room[rid] = (mid, body, created_at, author_id)

        # Unread counts per room (messages after last_read_at, excluding own messages).
        epoch = datetime(1970, 1, 1)
        unread_res = await self._session.execute(
            select(
                StaffChatMessage.room_id,
                func.count().label("unread"),
            )
            .select_from(StaffChatMessage)
            .join(
                StaffChatRoomMember,
                (StaffChatRoomMember.room_id == StaffChatMessage.room_id)
                & (StaffChatRoomMember.admin_id == admin_id),
            )
            .where(
                StaffChatMessage.clinic_id == clinic_id,
                StaffChatMessage.room_id.in_(room_ids),
                StaffChatMessage.author_admin_id != admin_id,
                StaffChatMessage.created_at > func.coalesce(StaffChatRoomMember.last_read_at, epoch),
            )
            .group_by(StaffChatMessage.room_id)
        )
        unread_by_room = {rid: int(cnt or 0) for rid, cnt in unread_res.all()}

        # DM peers: derive peer ids from dm_pair_key (stored as "uuidA:uuidB").
        dm_peer_id_by_room: dict[UUID, UUID] = {}
        dm_peer_ids: set[UUID] = set()
        for r in rooms:
            if r.kind != DM_KIND or not r.dm_pair_key:
                continue
            try:
                a, b = (r.dm_pair_key or "").split(":", 1)
                peer = UUID(a) if str(UUID(b)) == str(admin_id) else UUID(b)
                if peer == admin_id:
                    peer = UUID(a)
                dm_peer_id_by_room[r.id] = peer
                dm_peer_ids.add(peer)
            except Exception:
                continue

        dm_peer_brief: dict[UUID, NamedAdminBrief] = {}
        if dm_peer_ids:
            peer_res = await self._session.execute(
                select(AdminUser.id, AdminUser.full_name, StaffProfile.avatar_s3_key)
                .select_from(AdminUser)
                .outerjoin(StaffProfile, StaffProfile.admin_id == AdminUser.id)
                .where(
                    AdminUser.id.in_(list(dm_peer_ids)),
                    AdminUser.clinic_id == clinic_id,
                    AdminUser.deleted_at.is_(None),
                    AdminUser.employment_status == EMPLOYMENT_ACTIVE,
                )
            )
            for pid, full_name, avatar_key in peer_res.all():
                dm_peer_brief[pid] = NamedAdminBrief(
                    id=pid,
                    full_name=full_name,
                    avatar_url=f"/v1/admin/staff/avatars/{pid}" if avatar_key else None,
                )

        def _preview(text: str) -> str:
            t = (text or "").strip().replace("\n", " ")
            if len(t) <= 160:
                return t
            return t[:160].rstrip() + "…"

        # Build responses and sort by last activity.
        out: list[StaffChatRoomResponse] = []
        for r in rooms:
            last = last_msg_by_room.get(r.id)
            last_at = last[2] if last else None
            preview = _preview(last[1]) if last else None
            unread = unread_by_room.get(r.id, 0)
            peer = dm_peer_brief.get(dm_peer_id_by_room.get(r.id)) if r.kind == DM_KIND else None
            title = peer.full_name.strip() if (peer and peer.full_name and peer.full_name.strip()) else r.title
            out.append(
                StaffChatRoomResponse(
                    id=r.id,
                    kind=r.kind,
                    title=title,
                    task_id=r.task_id,
                    last_message_at=last_at,
                    last_message_preview=preview,
                    unread_count=unread,
                    dm_peer=peer,
                )
            )

        out.sort(
            key=lambda x: (
                0 if x.last_message_at else 1,
                -(int(x.last_message_at.timestamp()) if x.last_message_at else 0),
                str(x.id),
            )
        )
        return out


    async def mark_chat_room_read(self, clinic_id: UUID, room_id: UUID, admin_id: UUID) -> bool:
        res = await self._session.execute(
            select(StaffChatRoomMember).join(
                StaffChatRoom, StaffChatRoom.id == StaffChatRoomMember.room_id
            ).where(
                StaffChatRoomMember.room_id == room_id,
                StaffChatRoomMember.admin_id == admin_id,
                StaffChatRoom.clinic_id == clinic_id,
            ).limit(1)
        )
        row = res.scalar_one_or_none()
        if row is None:
            return False
        row.last_read_at = utc_now_naive()
        await self._session.flush()
        return True

    async def list_chat_messages(
        self,
        clinic_id: UUID,
        room_id: UUID,
        admin_id: UUID,
        *,
        limit: int = 50,
    ) -> list[StaffChatMessageResponse] | None:
        chk = await self._session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.id == room_id,
                StaffChatRoom.clinic_id == clinic_id,
            )
        )
        if chk.scalar_one_or_none() is None:
            return None
        if not await self._is_room_member(room_id, admin_id):
            return None
        res = await self._session.execute(
            select(StaffChatMessage).where(
                StaffChatMessage.clinic_id == clinic_id,
                StaffChatMessage.room_id == room_id,
            ).order_by(StaffChatMessage.created_at.desc()).limit(limit)
        )
        rows = list(reversed(res.scalars().all()))
        out: list[StaffChatMessageResponse] = []
        for m in rows:
            author = await self._admin_brief(m.author_admin_id)
            att_res = await self._session.execute(
                select(StaffChatMessageAttachment).where(
                    StaffChatMessageAttachment.message_id == m.id
                )
            )
            atts = [
                StaffAttachmentBrief(
                    id=a.id,
                    file_name=a.file_name,
                    content_type=a.content_type,
                    size_bytes=a.size_bytes,
                )
                for a in att_res.scalars().all()
            ]
            out.append(
                StaffChatMessageResponse(
                    id=m.id,
                    body=m.body,
                    author=author,
                    created_at=m.created_at,
                    attachments=atts,
                )
            )
        return out

    async def post_chat_message(
        self,
        clinic_id: UUID,
        room_id: UUID,
        author_admin_id: UUID,
        data: StaffChatMessageCreate,
    ) -> StaffChatMessageResponse | None:
        chk = await self._session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.id == room_id,
                StaffChatRoom.clinic_id == clinic_id,
            )
        )
        if chk.scalar_one_or_none() is None:
            return None
        if not await self._is_room_member(room_id, author_admin_id):
            return None
        body_val = (data.body or "").strip()
        if not body_val:
            return None

        dk: str | None = None
        try:
            redis = await get_redis()
            dk = _staff_chat_dedup_key(
                clinic_id=clinic_id,
                room_id=room_id,
                sender_admin_id=author_admin_id,
                body=body_val,
            )
            existing_id = await redis.get(dk)
            if existing_id:
                chat_dedup_hits_total.labels(kind="staff_chat").inc()
                row = await self._session.get(StaffChatMessage, UUID(existing_id))
                if row is not None:
                    author = await self._admin_brief(author_admin_id)
                    return StaffChatMessageResponse(
                        id=row.id,
                        body=row.body,
                        author=author,
                        created_at=row.created_at,
                        attachments=[],
                    )
        except Exception:
            dk = None

        msg = StaffChatMessage(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            room_id=room_id,
            author_admin_id=author_admin_id,
            body=body_val,
        )
        self._session.add(msg)
        await self._session.flush()
        try:
            if dk:
                redis = await get_redis()
                await redis.setex(dk, STAFF_CHAT_DEDUP_TTL_SECONDS, str(msg.id))
        except Exception:
            pass
        author = await self._admin_brief(author_admin_id)
        return StaffChatMessageResponse(
            id=msg.id,
            body=msg.body,
            author=author,
            created_at=msg.created_at,
            attachments=[],
        )

    async def invite_to_room(
        self,
        clinic_id: UUID,
        room_id: UUID,
        inviter_admin_id: UUID,
        data: StaffRoomInviteCreate,
    ) -> StaffChatRoom | None:
        invitee = data.invitee_admin_id
        if inviter_admin_id == invitee:
            raise ValueError("cannot_invite_self")
        res = await self._session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.id == room_id,
                StaffChatRoom.clinic_id == clinic_id,
            )
        )
        room = res.scalar_one_or_none()
        if room is None:
            return None
        if room.kind in (GENERAL_ROOM_KIND, DM_KIND):
            raise ValueError("room_kind_not_invitable")
        if not await self._is_room_member(room_id, inviter_admin_id):
            return None
        peer = await self._session.execute(
            select(AdminUser.id).where(
                AdminUser.id == invitee,
                AdminUser.clinic_id == clinic_id,
                AdminUser.employment_status == EMPLOYMENT_ACTIVE,
            )
        )
        if peer.scalar_one_or_none() is None:
            raise ValueError("invitee_not_in_clinic")
        if await self._is_room_member(room_id, invitee):
            return room
        self._session.add(
            StaffChatRoomMember(
                room_id=room_id,
                admin_id=invitee,
                membership_kind=MEMBERSHIP_INVITE,
            )
        )
        await self._session.flush()
        return room

    async def _feed_posts_liked_by_admin(
        self, post_ids: list[UUID], admin_id: UUID | None
    ) -> set[UUID]:
        if not post_ids or admin_id is None:
            return set()
        res = await self._session.execute(
            select(StaffFeedPostLike.post_id).where(
                StaffFeedPostLike.post_id.in_(post_ids),
                StaffFeedPostLike.author_admin_id == admin_id,
            )
        )
        return {row[0] for row in res.all()}

    async def _feed_posts_acked_by_admin(
        self, post_ids: list[UUID], admin_id: UUID | None
    ) -> set[UUID]:
        if not post_ids or admin_id is None:
            return set()
        res = await self._session.execute(
            select(StaffFeedPostAck.post_id).where(
                StaffFeedPostAck.post_id.in_(post_ids),
                StaffFeedPostAck.admin_id == admin_id,
            )
        )
        return {row[0] for row in res.all()}

    async def _admin_role_codes(self, clinic_id: UUID, admin_id: UUID | None) -> set[str]:
        if admin_id is None:
            return set()
        res = await self._session.execute(
            select(Role.code)
            .select_from(UserRole)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.clinic_id == clinic_id,
                UserRole.user_id == admin_id,
            )
        )
        return {str(row[0]) for row in res.all() if row[0]}

    @staticmethod
    def _is_post_visible_to_admin(post: StaffFeedPost, admin_id: UUID | None, role_codes: set[str]) -> bool:
        # Override: owner + managers can always see announcements (even if targeted).
        if post.is_announcement and {"owner", "manager"}.intersection(role_codes):
            return True
        role_scope = {str(x) for x in (post.audience_roles or []) if x}
        admin_scope = {str(x) for x in (post.audience_admin_ids or []) if x}
        if not role_scope and not admin_scope:
            return True
        if admin_id is not None and str(admin_id) in admin_scope:
            return True
        return bool(role_scope.intersection(role_codes))

    async def _can_publish_announcement(
        self,
        clinic_id: UUID,
        *,
        actor_admin_id: UUID,
        actor_role_codes: set[str],
    ) -> bool:
        # Owner can always publish announcements.
        if "owner" in actor_role_codes:
            return True

        # Default allow unless explicitly denied by policy (user overrides role).
        res = await self._session.execute(
            select(StaffAnnouncementPublishPolicy).where(
                StaffAnnouncementPublishPolicy.clinic_id == clinic_id
            )
        )
        rows = list(res.scalars().all())
        if not rows:
            return True

        actor_id_str = str(actor_admin_id)
        user_rows = [r for r in rows if r.scope_type == "user" and r.scope_value == actor_id_str]
        if user_rows:
            # If multiple rows exist (shouldn't due to unique constraint), last one wins.
            return bool(user_rows[-1].can_publish)

        role_rows = [r for r in rows if r.scope_type == "role" and r.scope_value in actor_role_codes]
        # Any explicit deny for any of actor roles disables publishing.
        if any(not r.can_publish for r in role_rows):
            return False
        # Otherwise allow.
        return True

    async def list_announcement_publish_policies(self, clinic_id: UUID) -> StaffAnnouncementPublishPolicyResponse:
        res = await self._session.execute(
            select(StaffAnnouncementPublishPolicy).where(
                StaffAnnouncementPublishPolicy.clinic_id == clinic_id
            )
        )
        rows = list(res.scalars().all())
        return StaffAnnouncementPublishPolicyResponse(
            policies=[
                StaffAnnouncementPublishPolicyRow(
                    scope_type=r.scope_type,
                    scope_value=r.scope_value,
                    can_publish=bool(r.can_publish),
                )
                for r in rows
            ]
        )

    async def upsert_announcement_publish_policies(
        self,
        clinic_id: UUID,
        *,
        actor_admin_id: UUID | None = None,
        rows: list[StaffAnnouncementPublishPolicyRow],
    ) -> StaffAnnouncementPublishPolicyResponse:
        # Audit snapshot (who/when) for compliance / complaints wall.
        self._session.add(
            StaffAnnouncementPublishPolicyAudit(
                id=uuid.uuid4(),
                clinic_id=clinic_id,
                actor_admin_id=actor_admin_id,
                snapshot={"policies": [r.model_dump() for r in rows]},
            )
        )
        # Full replace semantics: caller sends the whole desired policy set.
        await self._session.execute(
            delete(StaffAnnouncementPublishPolicy).where(
                StaffAnnouncementPublishPolicy.clinic_id == clinic_id
            )
        )
        for row in rows:
            scope_type = (row.scope_type or "").strip()
            scope_value = (row.scope_value or "").strip()
            if scope_type not in ("role", "user"):
                continue
            if not scope_value:
                continue
            self._session.add(
                StaffAnnouncementPublishPolicy(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    scope_type=scope_type,
                    scope_value=scope_value,
                    can_publish=bool(row.can_publish),
                )
            )
        await self._session.flush()
        return await self.list_announcement_publish_policies(clinic_id)

    async def list_announcement_publish_policy_audits(
        self,
        clinic_id: UUID,
        *,
        limit: int = 200,
    ) -> StaffAnnouncementPublishPolicyAuditListResponse:
        limit = max(1, min(int(limit or 200), 500))
        res = await self._session.execute(
            select(
                StaffAnnouncementPublishPolicyAudit,
                AdminUser.full_name,
            )
            .select_from(StaffAnnouncementPublishPolicyAudit)
            .join(
                AdminUser,
                AdminUser.id == StaffAnnouncementPublishPolicyAudit.actor_admin_id,
                isouter=True,
            )
            .where(StaffAnnouncementPublishPolicyAudit.clinic_id == clinic_id)
            .order_by(StaffAnnouncementPublishPolicyAudit.created_at.desc())
            .limit(limit)
        )
        items: list[StaffAnnouncementPublishPolicyAuditRow] = []
        for row, actor_name in res.all():
            items.append(
                StaffAnnouncementPublishPolicyAuditRow(
                    id=row.id,
                    created_at=row.created_at,
                    actor_admin_id=row.actor_admin_id,
                    actor_name=actor_name,
                    snapshot=row.snapshot,
                )
            )
        return StaffAnnouncementPublishPolicyAuditListResponse(items=items)

    async def _resolve_target_admin_ids(self, clinic_id: UUID, post: StaffFeedPost) -> set[UUID]:
        role_scope = {str(x) for x in (post.audience_roles or []) if x}
        admin_scope = {str(x) for x in (post.audience_admin_ids or []) if x}
        all_active_stmt = select(AdminUser.id).where(
            AdminUser.clinic_id == clinic_id,
            AdminUser.deleted_at.is_(None),
            AdminUser.employment_status == EMPLOYMENT_ACTIVE,
        )
        if not role_scope and not admin_scope:
            res = await self._session.execute(all_active_stmt)
            return set(res.scalars().all())
        target_ids: set[UUID] = set()
        if admin_scope:
            exp = await self._session.execute(
                all_active_stmt.where(AdminUser.id.in_([UUID(x) for x in admin_scope]))
            )
            target_ids.update(exp.scalars().all())
        if role_scope:
            rr = await self._session.execute(
                select(UserRole.user_id)
                .select_from(UserRole)
                .join(Role, Role.id == UserRole.role_id)
                .join(AdminUser, AdminUser.id == UserRole.user_id)
                .where(
                    UserRole.clinic_id == clinic_id,
                    Role.code.in_(list(role_scope)),
                    AdminUser.deleted_at.is_(None),
                    AdminUser.employment_status == EMPLOYMENT_ACTIVE,
                )
            )
            target_ids.update(rr.scalars().all())
        return target_ids

    async def list_feed_posts(
        self,
        clinic_id: UUID,
        *,
        viewer_admin_id: UUID | None = None,
        viewer_role_codes: set[str] | None = None,
        limit: int = 30,
        only_announcements: bool = False,
        exclude_announcements: bool = False,
    ) -> list[StaffFeedPostResponse]:
        if only_announcements and exclude_announcements:
            raise ValueError("invalid_feed_posts_filter")
        res = await self._session.execute(
            select(StaffFeedPost)
            .where(
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
            .order_by(StaffFeedPost.created_at.desc())
            .limit(limit)
        )
        posts = list(res.scalars().all())
        if only_announcements:
            posts = [p for p in posts if bool(p.is_announcement)]
        elif exclude_announcements:
            posts = [p for p in posts if not bool(p.is_announcement)]
        role_codes = viewer_role_codes if viewer_role_codes is not None else await self._admin_role_codes(
            clinic_id,
            viewer_admin_id,
        )
        posts = [p for p in posts if self._is_post_visible_to_admin(p, viewer_admin_id, role_codes)]
        liked_ids = await self._feed_posts_liked_by_admin(
            [p.id for p in posts], viewer_admin_id
        )
        acked_ids = await self._feed_posts_acked_by_admin([p.id for p in posts], viewer_admin_id)
        out: list[StaffFeedPostResponse] = []
        for post in posts:
            cnt_res = await self._session.execute(
                select(func.count())
                .select_from(StaffFeedComment)
                .where(StaffFeedComment.post_id == post.id)
            )
            cc = int(cnt_res.scalar_one() or 0)

            like_cnt_res = await self._session.execute(
                select(func.count())
                .select_from(StaffFeedPostLike)
                .where(StaffFeedPostLike.post_id == post.id)
            )
            lc = int(like_cnt_res.scalar_one() or 0)
            ack_cnt_res = await self._session.execute(
                select(func.count())
                .select_from(StaffFeedPostAck)
                .where(StaffFeedPostAck.post_id == post.id)
            )
            ac = int(ack_cnt_res.scalar_one() or 0)
            audience_total = len(await self._resolve_target_admin_ids(clinic_id, post))

            author = await self._admin_brief(post.author_admin_id)
            att_res = await self._session.execute(
                select(StaffFeedPostAttachment).where(StaffFeedPostAttachment.post_id == post.id)
            )
            raw_atts = list(att_res.scalars().all())
            atts = [
                StaffAttachmentBrief(
                    id=a.id,
                    file_name=a.file_name,
                    content_type=a.content_type,
                    size_bytes=a.size_bytes,
                )
                for a in raw_atts
                if (Path(settings.staff_chat_upload_root) / a.storage_path.replace("/", os.sep)).is_file()
            ]
            out.append(
                StaffFeedPostResponse(
                    id=post.id,
                    title=post.title,
                    body=post.body,
                    author=author,
                    created_at=post.created_at,
                    comments_count=cc,
                    likes_count=lc,
                    liked_by_me=post.id in liked_ids,
                    acknowledged_by_me=post.id in acked_ids,
                    acknowledged_count=ac,
                    audience_total=audience_total,
                    is_announcement=post.is_announcement,
                    requires_ack=post.requires_ack,
                    priority_level=post.priority_level,
                    audience_roles=[str(x) for x in (post.audience_roles or []) if x],
                    audience_admin_ids=[UUID(x) for x in (post.audience_admin_ids or []) if x],
                    attachments=atts,
                )
            )
        return out

    async def create_feed_post(
        self,
        clinic_id: UUID,
        author_admin_id: UUID,
        data: StaffFeedPostCreate,
        *,
        actor_role_codes: set[str] | None = None,
    ) -> StaffFeedPostResponse:
        title = data.title.strip() if data.title else None
        if title == "":
            title = None
        role_codes = actor_role_codes if actor_role_codes is not None else await self._admin_role_codes(
            clinic_id, author_admin_id
        )
        if data.is_announcement:
            allowed = await self._can_publish_announcement(
                clinic_id,
                actor_admin_id=author_admin_id,
                actor_role_codes=role_codes,
            )
            if not allowed:
                raise ValueError("announcement_publish_denied")
        post = StaffFeedPost(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            author_admin_id=author_admin_id,
            title=title,
            body=data.body.strip(),
            is_announcement=bool(data.is_announcement),
            requires_ack=bool(data.requires_ack),
            priority_level=data.priority_level.strip() if data.priority_level else "normal",
            audience_roles=[str(x) for x in (data.audience_roles or []) if x],
            audience_admin_ids=[str(x) for x in (data.audience_admin_ids or []) if x],
        )
        self._session.add(post)
        await self._session.flush()
        author = await self._admin_brief(author_admin_id)
        return StaffFeedPostResponse(
            id=post.id,
            title=post.title,
            body=post.body,
            author=author,
            created_at=post.created_at,
            comments_count=0,
            likes_count=0,
            liked_by_me=False,
            acknowledged_by_me=False,
            acknowledged_count=0,
            audience_total=0,
            is_announcement=post.is_announcement,
            requires_ack=post.requires_ack,
            priority_level=post.priority_level,
            audience_roles=[str(x) for x in (post.audience_roles or []) if x],
            audience_admin_ids=[UUID(x) for x in (post.audience_admin_ids or []) if x],
            attachments=[],
        )

    async def list_feed_comments(
        self,
        clinic_id: UUID,
        post_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> list[StaffFeedCommentResponse] | None:
        chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        if chk.scalar_one_or_none() is None:
            return None
        base = select(StaffFeedComment).where(StaffFeedComment.post_id == post_id)
        if not include_deleted:
            base = base.where(StaffFeedComment.deleted_at.is_(None))
        res = await self._session.execute(
            base.order_by(StaffFeedComment.created_at)
        )
        rows = list(res.scalars().all())
        parent_ids = {c.parent_comment_id for c in rows if c.parent_comment_id}
        parent_by_id: dict[UUID, StaffFeedComment] = {}
        if parent_ids:
            pres = await self._session.execute(
                select(StaffFeedComment).where(StaffFeedComment.id.in_(parent_ids))
            )
            for pc in pres.scalars().all():
                parent_by_id[pc.id] = pc
        att_map: dict[UUID, list[StaffAttachmentBrief]] = defaultdict(list)
        if rows:
            cids = [c.id for c in rows]
            ares = await self._session.execute(
                select(StaffFeedCommentAttachment).where(StaffFeedCommentAttachment.comment_id.in_(cids))
            )
            for ar in ares.scalars().all():
                att_map[ar.comment_id].append(
                    StaffAttachmentBrief(
                        id=ar.id,
                        file_name=ar.file_name,
                        content_type=ar.content_type,
                        size_bytes=ar.size_bytes,
                    )
                )
        out: list[StaffFeedCommentResponse] = []
        for c in rows:
            author = await self._admin_brief(c.author_admin_id)
            in_reply_to = None
            if c.parent_comment_id:
                parent = parent_by_id.get(c.parent_comment_id)
                if parent is not None:
                    in_reply_to = await self._admin_brief(parent.author_admin_id)
            out.append(
                StaffFeedCommentResponse(
                    id=c.id,
                    body=c.body,
                    author=author,
                    created_at=c.created_at,
                    updated_at=getattr(c, "updated_at", None),
                    parent_comment_id=c.parent_comment_id,
                    in_reply_to=in_reply_to,
                    attachments=att_map.get(c.id, []),
                    deleted_at=getattr(c, "deleted_at", None),
                    deleted_by_admin_id=getattr(c, "deleted_by_admin_id", None),
                )
            )
        return out

    async def update_feed_comment(
        self,
        clinic_id: UUID,
        *,
        comment_id: UUID,
        editor_admin_id: UUID,
        data: StaffFeedCommentUpdate,
    ) -> StaffFeedCommentResponse | None:
        res = await self._session.execute(
            select(StaffFeedComment).where(
                StaffFeedComment.id == comment_id,
                StaffFeedComment.author_admin_id == editor_admin_id,
            )
        )
        c = res.scalar_one_or_none()
        if c is None:
            return None
        if c.deleted_at is not None:
            raise ValueError("comment_deleted")
        post_chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == c.post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        if post_chk.scalar_one_or_none() is None:
            return None
        c.body = data.body.strip()
        await self._session.flush()
        # Reuse list for full shape (incl. reply-to + attachments).
        rows = await self.list_feed_comments(clinic_id, c.post_id, include_deleted=True)
        if rows is None:
            return None
        for r in rows:
            if r.id == c.id:
                return r
        return None

    async def delete_feed_comment(
        self,
        clinic_id: UUID,
        *,
        comment_id: UUID,
        actor_admin_id: UUID,
        allow_moderate: bool,
    ) -> bool:
        res = await self._session.execute(select(StaffFeedComment).where(StaffFeedComment.id == comment_id))
        c = res.scalar_one_or_none()
        if c is None:
            return False
        post_chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == c.post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        if post_chk.scalar_one_or_none() is None:
            return False
        if c.deleted_at is not None:
            return True
        if c.author_admin_id != actor_admin_id and not allow_moderate:
            return False
        c.deleted_at = utc_now_naive()
        c.deleted_by_admin_id = actor_admin_id
        await self._session.flush()
        return True

    async def add_feed_comment(
        self,
        clinic_id: UUID,
        post_id: UUID,
        author_admin_id: UUID,
        data: StaffFeedCommentCreate,
    ) -> StaffFeedCommentResponse | None:
        chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        if chk.scalar_one_or_none() is None:
            return None
        parent_comment_id = data.parent_comment_id
        parent_row: StaffFeedComment | None = None
        if parent_comment_id is not None:
            pres = await self._session.execute(
                select(StaffFeedComment).where(
                    StaffFeedComment.id == parent_comment_id,
                    StaffFeedComment.post_id == post_id,
                )
            )
            parent_row = pres.scalar_one_or_none()
            if parent_row is None:
                raise ValueError("invalid_parent_comment")
        c = StaffFeedComment(
            id=uuid.uuid4(),
            post_id=post_id,
            parent_comment_id=parent_comment_id,
            author_admin_id=author_admin_id,
            body=data.body.strip(),
        )
        self._session.add(c)
        await self._session.flush()
        author = await self._admin_brief(author_admin_id)
        in_reply_to = (
            await self._admin_brief(parent_row.author_admin_id) if parent_row is not None else None
        )
        return StaffFeedCommentResponse(
            id=c.id,
            body=c.body,
            author=author,
            created_at=c.created_at,
            parent_comment_id=c.parent_comment_id,
            in_reply_to=in_reply_to,
            attachments=[],
        )

    async def add_feed_comment_attachment(
        self,
        clinic_id: UUID,
        comment_id: UUID,
        admin_id: UUID,
        *,
        file_name: str,
        content_type: str,
        raw: bytes,
    ) -> StaffAttachmentBrief | None:
        if len(raw) > settings.staff_chat_max_attachment_bytes:
            raise ValueError("file_too_large")
        crow = await self._session.execute(
            select(StaffFeedComment).where(
                StaffFeedComment.id == comment_id,
                StaffFeedComment.author_admin_id == admin_id,
            )
        )
        c = crow.scalar_one_or_none()
        if c is None:
            return None
        post_chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == c.post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        if post_chk.scalar_one_or_none() is None:
            return None
        att_id = uuid.uuid4()
        safe = _sanitize_filename(file_name)
        rel = f"feed_comments/{clinic_id}/{att_id}_{safe}"
        path = Path(settings.staff_chat_upload_root) / rel.replace("/", os.sep)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        row = StaffFeedCommentAttachment(
            id=att_id,
            clinic_id=clinic_id,
            comment_id=comment_id,
            file_name=file_name[:500],
            content_type=content_type[:128],
            size_bytes=len(raw),
            storage_path=rel.replace("\\", "/"),
        )
        self._session.add(row)
        await self._session.flush()
        return StaffAttachmentBrief(
            id=row.id,
            file_name=row.file_name,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
        )

    async def toggle_feed_post_like(
        self,
        clinic_id: UUID,
        post_id: UUID,
        admin_id: UUID,
    ) -> tuple[bool, int] | None:
        """Toggle post like for current admin."""
        chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        post = chk.scalar_one_or_none()
        if post is None:
            return None

        like_chk = await self._session.execute(
            select(StaffFeedPostLike).where(
                StaffFeedPostLike.post_id == post_id,
                StaffFeedPostLike.author_admin_id == admin_id,
            )
        )
        like_row = like_chk.scalar_one_or_none()
        liked: bool
        if like_row is not None:
            await self._session.execute(
                delete(StaffFeedPostLike).where(StaffFeedPostLike.id == like_row.id)
            )
            liked = False
        else:
            self._session.add(
                StaffFeedPostLike(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    post_id=post_id,
                    author_admin_id=admin_id,
                )
            )
            liked = True

        await self._session.flush()

        like_cnt_res = await self._session.execute(
            select(func.count())
            .select_from(StaffFeedPostLike)
            .where(StaffFeedPostLike.post_id == post_id)
        )
        lc = int(like_cnt_res.scalar_one() or 0)
        return liked, lc

    async def acknowledge_feed_post(
        self,
        clinic_id: UUID,
        post_id: UUID,
        admin_id: UUID,
        *,
        viewer_role_codes: set[str] | None = None,
    ) -> tuple[bool, int] | None:
        chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        post = chk.scalar_one_or_none()
        if post is None:
            return None
        role_codes = viewer_role_codes if viewer_role_codes is not None else await self._admin_role_codes(
            clinic_id,
            admin_id,
        )
        if not self._is_post_visible_to_admin(post, admin_id, role_codes):
            return None
        like_chk = await self._session.execute(
            select(StaffFeedPostAck).where(
                StaffFeedPostAck.post_id == post_id,
                StaffFeedPostAck.admin_id == admin_id,
            )
        )
        ack_row = like_chk.scalar_one_or_none()
        if ack_row is None:
            self._session.add(
                StaffFeedPostAck(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    post_id=post_id,
                    admin_id=admin_id,
                )
            )
            acknowledged = True
        else:
            acknowledged = True
        await self._session.flush()
        ack_cnt_res = await self._session.execute(
            select(func.count())
            .select_from(StaffFeedPostAck)
            .where(StaffFeedPostAck.post_id == post_id)
        )
        return acknowledged, int(ack_cnt_res.scalar_one() or 0)

    async def feed_post_ack_status(self, clinic_id: UUID, post_id: UUID) -> tuple[list[tuple[UUID, str | None, datetime | None]], list[tuple[UUID, str | None, datetime | None]]] | None:
        res = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        post = res.scalar_one_or_none()
        if post is None:
            return None
        target_ids = await self._resolve_target_admin_ids(clinic_id, post)
        if not target_ids:
            return [], []
        admins_res = await self._session.execute(
            select(AdminUser.id, AdminUser.full_name).where(AdminUser.id.in_(list(target_ids)))
        )
        names = {row[0]: row[1] for row in admins_res.all()}
        ack_res = await self._session.execute(
            select(StaffFeedPostAck.admin_id, StaffFeedPostAck.created_at).where(
                StaffFeedPostAck.post_id == post_id,
                StaffFeedPostAck.admin_id.in_(list(target_ids)),
            )
        )
        ack_map = {row[0]: row[1] for row in ack_res.all()}
        acknowledged = [(aid, names.get(aid), ack_map.get(aid)) for aid in target_ids if aid in ack_map]
        pending = [(aid, names.get(aid), None) for aid in target_ids if aid not in ack_map]
        acknowledged.sort(key=lambda x: (x[1] or "", str(x[0])))
        pending.sort(key=lambda x: (x[1] or "", str(x[0])))
        return acknowledged, pending

    async def update_feed_post(
        self,
        clinic_id: UUID,
        editor_admin_id: UUID,
        post_id: UUID,
        *,
        title: str | None,
        body: str,
        raw: bytes | None,
        file_name: str | None,
        content_type: str | None,
    ) -> StaffFeedPostResponse | None:
        """Update feed post: title/body and optionally replace its attachments with a new file."""
        chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        post = chk.scalar_one_or_none()
        if post is None:
            return None

        # Title can be null (no title).
        if title is not None:
            t = title.strip()
            post.title = t if t else None
        post.body = body.strip()

        if raw is not None:
            if file_name is None or content_type is None:
                raise ValueError("file_name/content_type required with raw")
            if len(raw) > settings.staff_chat_max_attachment_bytes:
                raise ValueError("file_too_large")

            # Delete old attachments (DB + best-effort file system cleanup).
            old_atts = (
                await self._session.execute(
                    select(StaffFeedPostAttachment).where(StaffFeedPostAttachment.post_id == post_id)
                )
            ).scalars().all()
            for a in old_atts:
                try:
                    path = Path(settings.staff_chat_upload_root) / a.storage_path.replace("/", os.sep)
                    if path.is_file():
                        path.unlink()
                except OSError:
                    # Best-effort: attachment DB row will be removed; file cleanup shouldn't break UX.
                    pass
            await self._session.execute(
                delete(StaffFeedPostAttachment).where(StaffFeedPostAttachment.post_id == post_id)
            )

            att_id = uuid.uuid4()
            safe = _sanitize_filename(file_name)
            rel = f"feed_posts/{clinic_id}/{att_id}_{safe}"
            path = Path(settings.staff_chat_upload_root) / rel.replace("/", os.sep)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            self._session.add(
                StaffFeedPostAttachment(
                    id=att_id,
                    clinic_id=clinic_id,
                    post_id=post_id,
                    file_name=file_name[:500],
                    content_type=content_type[:128],
                    size_bytes=len(raw),
                    storage_path=rel.replace("\\", "/"),
                )
            )

        await self._session.flush()

        # Build response (keep logic consistent with list_feed_posts).
        cnt_res = await self._session.execute(
            select(func.count()).select_from(StaffFeedComment).where(StaffFeedComment.post_id == post_id)
        )
        cc = int(cnt_res.scalar_one() or 0)
        like_cnt_res = await self._session.execute(
            select(func.count())
            .select_from(StaffFeedPostLike)
            .where(StaffFeedPostLike.post_id == post_id)
        )
        lc = int(like_cnt_res.scalar_one() or 0)

        author = await self._admin_brief(post.author_admin_id)
        att_res = await self._session.execute(
            select(StaffFeedPostAttachment).where(StaffFeedPostAttachment.post_id == post_id)
        )
        atts = [
            StaffAttachmentBrief(
                id=a.id,
                file_name=a.file_name,
                content_type=a.content_type,
                size_bytes=a.size_bytes,
            )
            for a in att_res.scalars().all()
        ]
        liked_ids = await self._feed_posts_liked_by_admin([post_id], editor_admin_id)

        return StaffFeedPostResponse(
            id=post.id,
            title=post.title,
            body=post.body,
            author=author,
            created_at=post.created_at,
            comments_count=cc,
            likes_count=lc,
            liked_by_me=post_id in liked_ids,
            acknowledged_by_me=False,
            acknowledged_count=0,
            audience_total=0,
            is_announcement=post.is_announcement,
            requires_ack=post.requires_ack,
            priority_level=post.priority_level,
            audience_roles=[str(x) for x in (post.audience_roles or []) if x],
            audience_admin_ids=[UUID(x) for x in (post.audience_admin_ids or []) if x],
            attachments=atts,
        )

    async def delete_feed_post(self, clinic_id: UUID, post_id: UUID) -> bool:
        """Hard-delete side tables and attachments, and soft-delete the post."""
        chk = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        post = chk.scalar_one_or_none()
        if post is None:
            return False

        # Clean attachments + best-effort files.
        old_atts = (
            await self._session.execute(
                select(StaffFeedPostAttachment).where(StaffFeedPostAttachment.post_id == post_id)
            )
        ).scalars().all()
        for a in old_atts:
            try:
                path = Path(settings.staff_chat_upload_root) / a.storage_path.replace("/", os.sep)
                if path.is_file():
                    path.unlink()
            except OSError:
                pass
        await self._session.execute(
            delete(StaffFeedPostAttachment).where(StaffFeedPostAttachment.post_id == post_id)
        )
        await self._session.execute(delete(StaffFeedPostLike).where(StaffFeedPostLike.post_id == post_id))
        com_ids_res = await self._session.execute(
            select(StaffFeedComment.id).where(StaffFeedComment.post_id == post_id)
        )
        comment_ids = [r[0] for r in com_ids_res.all()]
        if comment_ids:
            c_atts = (
                await self._session.execute(
                    select(StaffFeedCommentAttachment).where(
                        StaffFeedCommentAttachment.comment_id.in_(comment_ids)
                    )
                )
            ).scalars().all()
            for a in c_atts:
                try:
                    p = Path(settings.staff_chat_upload_root) / a.storage_path.replace("/", os.sep)
                    if p.is_file():
                        p.unlink()
                except OSError:
                    pass
            await self._session.execute(
                delete(StaffFeedCommentAttachment).where(
                    StaffFeedCommentAttachment.comment_id.in_(comment_ids)
                )
            )
        await self._session.execute(delete(StaffFeedComment).where(StaffFeedComment.post_id == post_id))

        post.deleted_at = utc_now_naive()
        await self._session.flush()
        return True

    async def list_calendar_events(
        self,
        clinic_id: UUID,
        *,
        from_ts: datetime,
        to_ts: datetime,
        filter_doctor_user_id: UUID | None = None,
    ) -> list[StaffCalendarEventResponse]:
        stmt = (
            select(StaffCalendarEvent)
            .where(
                StaffCalendarEvent.clinic_id == clinic_id,
                StaffCalendarEvent.starts_at < to_ts,
                StaffCalendarEvent.ends_at > from_ts,
            )
            .order_by(StaffCalendarEvent.starts_at)
        )
        if filter_doctor_user_id is not None:
            stmt = stmt.where(
                or_(
                    StaffCalendarEvent.created_by_admin_id == filter_doctor_user_id,
                    StaffCalendarEvent.id.in_(
                        select(StaffCalendarEventParticipant.event_id).where(
                            StaffCalendarEventParticipant.admin_id == filter_doctor_user_id
                        )
                    ),
                )
            )
        res = await self._session.execute(stmt)
        out: list[StaffCalendarEventResponse] = []
        for ev in res.scalars().all():
            out.append(await self._calendar_event_to_response(ev))
        return out

    async def list_calendar_month_grid(
        self,
        clinic_id: UUID,
        *,
        from_ts: datetime,
        to_ts: datetime,
        current_admin_id: UUID,
    ) -> StaffCalendarMonthGridResponse:
        """
        Month-grid summary for staff calendar.

        Enterprise range: include events overlapping [from_ts, to_ts)
        (starts_at < to_ts && ends_at > from_ts).
        """

        month_first_date = from_ts.date()
        month_last_date = to_ts.date()

        # Monday-based calendar grid (7 columns).
        grid_start = month_first_date - timedelta(days=month_first_date.weekday())
        grid_end = month_last_date + timedelta(days=(6 - month_last_date.weekday()))

        grid_start_dt = datetime(grid_start.year, grid_start.month, grid_start.day)
        grid_end_exclusive_dt = datetime(grid_end.year, grid_end.month, grid_end.day) + timedelta(days=1)

        event_stmt = (
            select(StaffCalendarEvent)
            .where(
                StaffCalendarEvent.clinic_id == clinic_id,
                # Load events for the full visible calendar grid, not only [from_ts, to_ts].
                # Otherwise leading/trailing days (e.g. Feb days in March grid) appear empty.
                StaffCalendarEvent.starts_at < grid_end_exclusive_dt,
                StaffCalendarEvent.ends_at > grid_start_dt,
            )
            .order_by(StaffCalendarEvent.starts_at)
        )
        ev_res = await self._session.execute(event_stmt)
        events = list(ev_res.scalars().all())

        if not events:
            empty_days: list[CalendarDayCell] = []
            d = grid_start
            while d <= grid_end:
                empty_days.append(
                    CalendarDayCell(
                        date=d,
                        is_in_current_month=(d.month == month_first_date.month),
                        events=[],
                        reminder_event_ids=[],
                        unseen_invite_event_ids=[],
                        unseen_invite_count=0,
                    )
                )
                d += timedelta(days=1)
            return StaffCalendarMonthGridResponse(
                month=CalendarMonthRange(from_=from_ts, to=to_ts),
                days=empty_days,
                notification_signals=StaffCalendarNotificationSignals(
                    unseen_invites_count=0,
                    reminders_due_now_count=0,
                ),
            )

        event_ids = [e.id for e in events]

        # Participants for fetched events (one query, then map in-memory).
        parts_res = await self._session.execute(
            select(StaffCalendarEventParticipant.event_id, StaffCalendarEventParticipant.admin_id).where(
                StaffCalendarEventParticipant.event_id.in_(event_ids)
            )
        )
        participants_by_event: dict[UUID, set[UUID]] = {}
        for eid, aid in parts_res.all():
            participants_by_event.setdefault(eid, set()).add(aid)

        # Invitation ack for the current admin (one query).
        inv_res = await self._session.execute(
            select(StaffCalendarEventInvitation.event_id, StaffCalendarEventInvitation.acknowledged_at).where(
                StaffCalendarEventInvitation.event_id.in_(event_ids),
                StaffCalendarEventInvitation.invitee_admin_id == current_admin_id,
            )
        )
        ack_by_event: dict[UUID, datetime | None] = {}
        for eid, ack_at in inv_res.all():
            ack_by_event[eid] = ack_at

        unseen_invite_event_ids = {eid for eid, ack_at in ack_by_event.items() if ack_at is None}
        participant_event_ids = {eid for eid, aids in participants_by_event.items() if current_admin_id in aids}

        # Reminder deliveries for events where current admin participates.
        now = datetime.now(timezone.utc)
        remind_window_start = now - timedelta(minutes=15)
        remind_window_end = now + timedelta(minutes=15)

        rem_res = await self._session.execute(
            select(
                StaffCalendarReminderDelivery.event_id,
                StaffCalendarReminderDelivery.fire_at,
                StaffCalendarReminderDelivery.sent_at,
            ).where(
                StaffCalendarReminderDelivery.event_id.in_(list(participant_event_ids) or [uuid.uuid4()]),
                StaffCalendarReminderDelivery.sent_at.is_(None),
            )
        )

        reminders_by_date: dict[date, list[UUID]] = {}
        reminders_due_now_count = 0
        for eid, fire_at, _sent_at in rem_res.all():
            # Defensive: treat naive datetimes as UTC for window checks.
            fire_aware = fire_at if fire_at.tzinfo is not None else fire_at.replace(tzinfo=timezone.utc)
            reminders_due_now_count += 1 if remind_window_start <= fire_aware <= remind_window_end else 0
            reminders_by_date.setdefault(fire_at.date(), []).append(eid)

        event_chip_by_id: dict[UUID, CalendarEventChip] = {
            e.id: CalendarEventChip(
                id=e.id,
                title=e.title,
                starts_at=e.starts_at,
                ends_at=e.ends_at,
                all_day=e.all_day,
                task_id=e.task_id,
                created_by_admin_id=e.created_by_admin_id,
            )
            for e in events
        }

        # Build day cells with event overlap + markers.
        days: list[CalendarDayCell] = []
        d = grid_start
        while d <= grid_end:
            day_start = datetime(d.year, d.month, d.day)
            day_end = day_start + timedelta(days=1)

            overlapping_event_ids: list[UUID] = []
            for e in events:
                ev_start = e.starts_at.replace(tzinfo=None) if getattr(e.starts_at, "tzinfo", None) is not None else e.starts_at
                ev_end = e.ends_at.replace(tzinfo=None) if getattr(e.ends_at, "tzinfo", None) is not None else e.ends_at
                if ev_start < day_end and ev_end > day_start:
                    overlapping_event_ids.append(e.id)
            overlapping_ids_set = set(overlapping_event_ids)

            unseen_ids = sorted(list(overlapping_ids_set.intersection(unseen_invite_event_ids)))
            reminder_ids = sorted(set(reminders_by_date.get(d, [])))

            events_for_day = [event_chip_by_id[eid] for eid in overlapping_event_ids]

            days.append(
                CalendarDayCell(
                    date=d,
                    is_in_current_month=(d.month == month_first_date.month),
                    events=events_for_day,
                    reminder_event_ids=reminder_ids,
                    unseen_invite_event_ids=unseen_ids,
                    unseen_invite_count=len(unseen_ids),
                )
            )
            d += timedelta(days=1)

        return StaffCalendarMonthGridResponse(
            month=CalendarMonthRange(from_=from_ts, to=to_ts),
            days=days,
            notification_signals=StaffCalendarNotificationSignals(
                unseen_invites_count=len(unseen_invite_event_ids),
                reminders_due_now_count=reminders_due_now_count,
            ),
        )

    async def get_calendar_event_details(
        self,
        clinic_id: UUID,
        *,
        event_id: UUID,
        current_admin_id: UUID,
    ) -> StaffCalendarEventDetailsResponse | None:
        ev = await self._session.get(StaffCalendarEvent, event_id)
        if ev is None or ev.clinic_id != clinic_id:
            return None

        event_resp = await self._calendar_event_to_response(ev)

        # Reminder delivery details (optional).
        rem = await self._session.execute(
            select(StaffCalendarReminderDelivery).where(
                StaffCalendarReminderDelivery.event_id == event_id,
                StaffCalendarReminderDelivery.clinic_id == clinic_id,
            )
        )
        rem_row = rem.scalar_one_or_none()
        reminder = StaffCalendarReminderInfo(
            reminder_minutes_before=ev.reminder_minutes_before,
            fire_at=rem_row.fire_at if rem_row else None,
            sent_at=rem_row.sent_at if rem_row else None,
        )

        # Current admin invitation ack status (optional).
        inv = await self._session.execute(
            select(StaffCalendarEventInvitation.acknowledged_at).where(
                StaffCalendarEventInvitation.event_id == event_id,
                StaffCalendarEventInvitation.invitee_admin_id == current_admin_id,
            )
        )
        invitation_ack_at = inv.scalar_one_or_none()

        creator_summary: StaffCalendarCreatorAckSummary | None = None
        if ev.created_by_admin_id == current_admin_id:
            # Count ack'ed among OTHER participants (creator sees "who confirmed").
            other_participants = [p.id for p in event_resp.participants if p.id != current_admin_id]
            if other_participants:
                inv2 = await self._session.execute(
                    select(StaffCalendarEventInvitation.acknowledged_at).where(
                        StaffCalendarEventInvitation.event_id == event_id,
                        StaffCalendarEventInvitation.invitee_admin_id.in_(list(other_participants)),
                    )
                )
                ack_rows = inv2.scalars().all()
                acknowledged_cnt = sum(1 for a in ack_rows if a is not None)
                creator_summary = StaffCalendarCreatorAckSummary(
                    total_participants=len(other_participants),
                    acknowledged_participants=acknowledged_cnt,
                )
            else:
                creator_summary = StaffCalendarCreatorAckSummary(
                    total_participants=0,
                    acknowledged_participants=0,
                )

        return StaffCalendarEventDetailsResponse(
            event=event_resp,
            reminder=reminder,
            invitation_acknowledged_at=invitation_ack_at,
            creator_ack_summary=creator_summary,
        )

    async def ack_calendar_invitation(
        self,
        clinic_id: UUID,
        *,
        event_id: UUID,
        current_admin_id: UUID,
    ) -> StaffCalendarInvitationAckResponse | None:
        inv = await self._session.execute(
            select(StaffCalendarEventInvitation).where(
                StaffCalendarEventInvitation.clinic_id == clinic_id,
                StaffCalendarEventInvitation.event_id == event_id,
                StaffCalendarEventInvitation.invitee_admin_id == current_admin_id,
            )
        )
        inv_row = inv.scalar_one_or_none()
        if inv_row is None:
            return None

        if inv_row.acknowledged_at is None:
            inv_row.acknowledged_at = utc_now_naive()
            await self._session.flush()

        # For a single event ack, unseen count after ack is always 0.
        return StaffCalendarInvitationAckResponse(
            event_id=event_id,
            acknowledged_at=inv_row.acknowledged_at,
            unseen_invite_count=0,
        )

    async def _calendar_event_to_response(self, ev: StaffCalendarEvent) -> StaffCalendarEventResponse:
        author = await self._admin_brief(ev.created_by_admin_id)
        pres = await self._session.execute(
            select(StaffCalendarEventParticipant.admin_id).where(
                StaffCalendarEventParticipant.event_id == ev.id
            )
        )
        participants: list[NamedAdminBrief] = []
        for pid in pres.scalars().all():
            participants.append(await self._admin_brief(pid))
        return StaffCalendarEventResponse(
            id=ev.id,
            title=ev.title,
            description=ev.description,
            starts_at=ev.starts_at,
            ends_at=ev.ends_at,
            all_day=ev.all_day,
            task_id=ev.task_id,
            reminder_minutes_before=ev.reminder_minutes_before,
            created_by=author,
            participants=participants,
        )

    async def _validate_participant_admins(self, clinic_id: UUID, admin_ids: list[UUID]) -> None:
        if not admin_ids:
            return
        res = await self._session.execute(
            select(AdminUser.id).where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.id.in_(admin_ids),
                AdminUser.deleted_at.is_(None),
                AdminUser.employment_status == EMPLOYMENT_ACTIVE,
            )
        )
        found = {r for r in res.scalars().all()}
        if found != set(admin_ids):
            raise ValueError("invalid_participants")

    async def _replace_calendar_participants(self, event_id: UUID, admin_ids: list[UUID]) -> None:
        await self._session.execute(
            delete(StaffCalendarEventParticipant).where(
                StaffCalendarEventParticipant.event_id == event_id
            )
        )
        for aid in admin_ids:
            self._session.add(StaffCalendarEventParticipant(event_id=event_id, admin_id=aid))
        await self._session.flush()

    async def _assert_calendar_event_no_overlap(
        self,
        *,
        clinic_id: UUID,
        starts_at: datetime,
        ends_at: datetime,
        exclude_event_id: UUID | None = None,
    ) -> None:
        """
        Calendars in the same clinic must not overlap.

        Overlap condition (half-open interval):
        new_starts < existing_ends AND new_ends > existing_starts
        """
        # Ensure DB/SQLAlchemy parameter types match:
        # we bind naive UTC datetimes to avoid asyncpg "offset-naive vs offset-aware" errors.
        starts_at = _dt_naive_utc(starts_at)
        ends_at = _dt_naive_utc(ends_at)

        if ends_at <= starts_at:
            raise ValueError("invalid_event_range")

        # Count-then-insert is racy without a lock (two concurrent creates both see cnt=0).
        # Same pg_advisory_xact_lock pattern as doctor-slot booking and ERP refresh.
        # Namespace 8842017 is distinct from ERP refresh (8842001).
        lock_k = crc32(str(clinic_id).encode("utf-8")) & 0x7FFFFFFF
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:a, :b)"),
            {"a": 8_842_017, "b": lock_k},
        )

        q = (
            select(func.count())
            .select_from(StaffCalendarEvent)
            .where(
                StaffCalendarEvent.clinic_id == clinic_id,
                StaffCalendarEvent.starts_at < ends_at,
                StaffCalendarEvent.ends_at > starts_at,
            )
        )
        if exclude_event_id is not None:
            q = q.where(StaffCalendarEvent.id != exclude_event_id)

        res = await self._session.execute(q)
        cnt = res.scalar_one()
        if cnt > 0:
            raise ValueError("calendar_event_overlap")

    async def create_calendar_event(
        self,
        clinic_id: UUID,
        created_by: UUID,
        data: StaffCalendarEventCreate,
    ) -> StaffCalendarEventResponse:
        rem = data.reminder_minutes_before
        if rem is not None and rem <= 0:
            rem = None
        ev = StaffCalendarEvent(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            title=data.title.strip(),
            description=data.description.strip() if data.description else None,
            starts_at=_dt_naive_utc(data.starts_at),
            ends_at=_dt_naive_utc(data.ends_at),
            all_day=data.all_day,
            created_by_admin_id=created_by,
            task_id=data.task_id,
            reminder_minutes_before=rem,
        )

        # Ensure we never create conflicting calendar intervals.
        await self._assert_calendar_event_no_overlap(
            clinic_id=clinic_id,
            starts_at=ev.starts_at,
            ends_at=ev.ends_at,
        )

        self._session.add(ev)
        await self._session.flush()
        raw_ids = list(dict.fromkeys(data.participant_admin_ids))
        if created_by not in raw_ids:
            raw_ids.insert(0, created_by)
        await self._validate_participant_admins(clinic_id, raw_ids)
        await self._replace_calendar_participants(ev.id, raw_ids)
        await self._ensure_calendar_event_invitations(
            clinic_id=clinic_id,
            event_id=ev.id,
            invitee_admin_ids=raw_ids,
        )
        await self._sync_calendar_reminder(ev)
        await self._session.flush()
        return await self._calendar_event_to_response(ev)

    async def update_calendar_event(
        self,
        clinic_id: UUID,
        event_id: UUID,
        data: StaffCalendarEventUpdate,
    ) -> StaffCalendarEventResponse | None:
        res = await self._session.execute(
            select(StaffCalendarEvent).where(
                StaffCalendarEvent.id == event_id,
                StaffCalendarEvent.clinic_id == clinic_id,
            )
        )
        ev = res.scalar_one_or_none()
        if ev is None:
            return None
        if data.title is not None:
            ev.title = data.title.strip()
        if data.description is not None:
            ev.description = data.description.strip() if data.description else None
        if data.starts_at is not None:
            ev.starts_at = _dt_naive_utc(data.starts_at)
        if data.ends_at is not None:
            ev.ends_at = _dt_naive_utc(data.ends_at)
        if data.all_day is not None:
            ev.all_day = data.all_day
        if data.reminder_minutes_before is not None:
            r = data.reminder_minutes_before
            ev.reminder_minutes_before = None if r <= 0 else r
        upd = data.model_dump(exclude_unset=True)
        if "task_id" in upd:
            ev.task_id = upd["task_id"]
        await self._session.flush()
        if ev.ends_at <= ev.starts_at:
            raise ValueError("invalid_event_range")

        # Ensure we never create conflicting calendar intervals.
        await self._assert_calendar_event_no_overlap(
            clinic_id=clinic_id,
            starts_at=ev.starts_at,
            ends_at=ev.ends_at,
            exclude_event_id=ev.id,
        )

        if data.participant_admin_ids is not None:
            merged = list(dict.fromkeys(data.participant_admin_ids))
            if ev.created_by_admin_id not in merged:
                merged.insert(0, ev.created_by_admin_id)
            old_res = await self._session.execute(
                select(StaffCalendarEventParticipant.admin_id).where(
                    StaffCalendarEventParticipant.event_id == ev.id
                )
            )
            old_ids = set(old_res.scalars().all())
            # Be robust: creator should always be invitee, even if a bad row state exists.
            old_ids.add(ev.created_by_admin_id)

            new_ids = set(merged)
            removed = sorted(old_ids - new_ids)
            added = sorted(new_ids - old_ids)

            await self._validate_participant_admins(clinic_id, merged)
            await self._replace_calendar_participants(ev.id, merged)
            await self._delete_calendar_event_invitations(event_id=ev.id, invitee_admin_ids=removed)
            await self._ensure_calendar_event_invitations(
                clinic_id=clinic_id,
                event_id=ev.id,
                invitee_admin_ids=added,
            )
        await self._sync_calendar_reminder(ev)
        await self._session.flush()
        return await self._calendar_event_to_response(ev)

    async def _sync_calendar_reminder(self, ev: StaffCalendarEvent) -> None:
        await self._session.execute(
            delete(StaffCalendarReminderDelivery).where(
                StaffCalendarReminderDelivery.event_id == ev.id
            )
        )
        mins = ev.reminder_minutes_before
        if mins is None or mins <= 0:
            return
        # DB stores calendar timestamps as naive UTC (TIMESTAMP WITHOUT TIME ZONE).
        # Keep `fire_at` naive to avoid asyncpg "offset-naive and offset-aware" errors.
        start_naive = ev.starts_at.replace(tzinfo=None) if getattr(ev.starts_at, "tzinfo", None) is not None else ev.starts_at
        fire_at = start_naive - timedelta(minutes=int(mins))
        now = utc_now_naive()
        if fire_at <= now:
            return
        row = StaffCalendarReminderDelivery(
            id=uuid.uuid4(),
            event_id=ev.id,
            clinic_id=ev.clinic_id,
            fire_at=fire_at,
            sent_at=None,
        )
        self._session.add(row)

    async def get_or_create_dm_room(
        self,
        clinic_id: UUID,
        admin_a: UUID,
        admin_b: UUID,
    ) -> StaffChatRoom:
        if admin_a == admin_b:
            raise ValueError("DM peer must differ from self")
        sa, sb = sorted([str(admin_a), str(admin_b)])
        key = f"{sa}:{sb}"
        res = await self._session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.clinic_id == clinic_id,
                StaffChatRoom.dm_pair_key == key,
            )
        )
        existing = res.scalar_one_or_none()
        if existing:
            return existing
        room = StaffChatRoom(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            kind=DM_KIND,
            title="Личные сообщения",
            dm_pair_key=key,
            created_by_admin_id=admin_a,
        )
        self._session.add(room)
        await self._session.flush()
        for aid in (UUID(sa), UUID(sb)):
            self._session.add(
                StaffChatRoomMember(
                    room_id=room.id,
                    admin_id=aid,
                    membership_kind=MEMBERSHIP_DM,
                )
            )
        return room

    async def create_group_room(
        self,
        clinic_id: UUID,
        creator_admin_id: UUID,
        data: StaffRoomCreateGroup,
    ) -> StaffChatRoom:
        member_ids = list({creator_admin_id, *data.member_admin_ids})
        room = StaffChatRoom(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            kind=GROUP_KIND,
            title=data.title.strip(),
            created_by_admin_id=creator_admin_id,
        )
        self._session.add(room)
        await self._session.flush()
        for aid in member_ids:
            self._session.add(
                StaffChatRoomMember(
                    room_id=room.id,
                    admin_id=aid,
                    membership_kind=MEMBERSHIP_GROUP,
                )
            )
        return room

    async def ensure_task_room(
        self,
        clinic_id: UUID,
        task_id: UUID,
        actor_admin_id: UUID,
    ) -> StaffChatRoom | None:
        task = await self._session.get(Task, task_id)
        if task is None or task.clinic_id != clinic_id:
            return None
        res = await self._session.execute(
            select(StaffChatRoom).where(
                StaffChatRoom.task_id == task_id,
                StaffChatRoom.clinic_id == clinic_id,
            )
        )
        existing = res.scalar_one_or_none()
        if existing:
            await self._ensure_task_room_members(existing.id, task)
            await self._session.flush()
            if not await self._is_room_member(existing.id, actor_admin_id):
                return None
            return existing
        if actor_admin_id not in (task.creator_id, task.assignee_id):
            return None
        room = StaffChatRoom(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            kind=TASK_KIND,
            title=f"Задача: {task.title[:200]}",
            task_id=task_id,
            created_by_admin_id=actor_admin_id,
        )
        self._session.add(room)
        await self._session.flush()
        await self._ensure_task_room_members(room.id, task)
        await self._session.flush()
        return room

    async def add_message_attachment(
        self,
        clinic_id: UUID,
        message_id: UUID,
        admin_id: UUID,
        *,
        file_name: str,
        content_type: str,
        raw: bytes | None = None,
        tmp_path: str | None = None,
        size_bytes: int | None = None,
    ) -> StaffAttachmentBrief | None:
        if raw is None and tmp_path is None:
            return None
        file_size = len(raw) if raw is not None else int(size_bytes or 0)
        if file_size <= 0:
            return None
        if file_size > settings.staff_chat_max_attachment_bytes:
            raise ValueError("file_too_large")
        try:
            first = raw[:16] if raw is not None else (open(tmp_path, "rb").read(16) if tmp_path else b"")
        except Exception:
            first = b""
        ct = (content_type or "").split(";")[0].strip().lower()
        if ct in {"application/pdf", "image/png", "image/jpeg", "image/gif", "image/webp"}:
            if _sniff_magic(first) != ct:
                raise ValueError("file_magic_mismatch")
        msg_row = await self._session.execute(
            select(StaffChatMessage).where(
                StaffChatMessage.id == message_id,
                StaffChatMessage.clinic_id == clinic_id,
            )
        )
        msg = msg_row.scalar_one_or_none()
        if msg is None or msg.author_admin_id != admin_id:
            return None
        if not await self._is_room_member(msg.room_id, admin_id):
            return None
        att_id = uuid.uuid4()
        safe = _sanitize_filename(file_name)
        subdir = Path(settings.staff_chat_upload_root) / str(clinic_id)
        subdir.mkdir(parents=True, exist_ok=True)
        rel = f"{clinic_id}/{att_id}_{safe}"
        path = Path(settings.staff_chat_upload_root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if raw is not None:
            path.write_bytes(raw)
        else:
            with open(tmp_path, "rb") as src, open(path, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
        row = StaffChatMessageAttachment(
            id=att_id,
            clinic_id=clinic_id,
            message_id=message_id,
            file_name=file_name[:500],
            content_type=content_type[:128],
            size_bytes=file_size,
            storage_path=rel.replace("\\", "/"),
        )
        self._session.add(row)
        await self._session.flush()
        return StaffAttachmentBrief(
            id=row.id,
            file_name=row.file_name,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
        )

    async def get_attachment_payload(
        self,
        clinic_id: UUID,
        attachment_id: UUID,
        viewer_admin_id: UUID,
    ) -> tuple[StaffChatMessageAttachment, bytes] | None:
        res = await self._session.execute(
            select(StaffChatMessageAttachment).where(
                StaffChatMessageAttachment.id == attachment_id,
                StaffChatMessageAttachment.clinic_id == clinic_id,
            )
        )
        row = res.scalar_one_or_none()
        if row is None:
            return None
        msg_row = await self._session.execute(
            select(StaffChatMessage).where(
                StaffChatMessage.id == row.message_id,
                StaffChatMessage.clinic_id == clinic_id,
            )
        )
        msg = msg_row.scalar_one_or_none()
        if msg is None:
            return None
        if not await self._is_room_member(msg.room_id, viewer_admin_id):
            return None
        path = Path(settings.staff_chat_upload_root) / row.storage_path.replace("/", os.sep)
        if not path.is_file():
            return None
        return row, path.read_bytes()

    async def add_feed_post_attachment(
        self,
        clinic_id: UUID,
        post_id: UUID,
        admin_id: UUID,
        *,
        file_name: str,
        content_type: str,
        raw: bytes,
    ) -> StaffAttachmentBrief | None:
        if len(raw) > settings.staff_chat_max_attachment_bytes:
            raise ValueError("file_too_large")
        post_row = await self._session.execute(
            select(StaffFeedPost).where(
                StaffFeedPost.id == post_id,
                StaffFeedPost.clinic_id == clinic_id,
                StaffFeedPost.deleted_at.is_(None),
            )
        )
        post = post_row.scalar_one_or_none()
        if post is None or post.author_admin_id != admin_id:
            return None
        att_id = uuid.uuid4()
        safe = _sanitize_filename(file_name)
        rel = f"feed_posts/{clinic_id}/{att_id}_{safe}"
        path = Path(settings.staff_chat_upload_root) / rel.replace("/", os.sep)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        row = StaffFeedPostAttachment(
            id=att_id,
            clinic_id=clinic_id,
            post_id=post_id,
            file_name=file_name[:500],
            content_type=content_type[:128],
            size_bytes=len(raw),
            storage_path=rel.replace("\\", "/"),
        )
        self._session.add(row)
        await self._session.flush()
        return StaffAttachmentBrief(
            id=row.id,
            file_name=row.file_name,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
        )

    async def get_feed_attachment_payload(
        self,
        clinic_id: UUID,
        attachment_id: UUID,
        viewer_admin_id: UUID,
    ) -> tuple[StaffFeedPostAttachment | StaffFeedCommentAttachment, bytes] | None:
        ures = await self._session.execute(
            select(AdminUser.id).where(
                AdminUser.id == viewer_admin_id,
                AdminUser.clinic_id == clinic_id,
                AdminUser.deleted_at.is_(None),
            )
        )
        if ures.scalar_one_or_none() is None:
            return None
        res = await self._session.execute(
            select(StaffFeedPostAttachment).where(
                StaffFeedPostAttachment.id == attachment_id,
                StaffFeedPostAttachment.clinic_id == clinic_id,
            )
        )
        row = res.scalar_one_or_none()
        if row is not None:
            path = Path(settings.staff_chat_upload_root) / row.storage_path.replace("/", os.sep)
            if not path.is_file():
                return None
            return row, path.read_bytes()
        res_c = await self._session.execute(
            select(StaffFeedCommentAttachment).where(
                StaffFeedCommentAttachment.id == attachment_id,
                StaffFeedCommentAttachment.clinic_id == clinic_id,
            )
        )
        crow = res_c.scalar_one_or_none()
        if crow is None:
            return None
        path_c = Path(settings.staff_chat_upload_root) / crow.storage_path.replace("/", os.sep)
        if not path_c.is_file():
            return None
        return crow, path_c.read_bytes()

    async def list_knowledge(
        self,
        clinic_id: UUID,
        user_roles: set[str],
    ) -> list[KnowledgeDocumentResponse]:
        res = await self._session.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.clinic_id == clinic_id)
            .order_by(KnowledgeDocument.folder_key, KnowledgeDocument.sort_order, KnowledgeDocument.title)
        )
        out: list[KnowledgeDocumentResponse] = []
        for doc in res.scalars().all():
            vr = doc.visible_roles if isinstance(doc.visible_roles, list) else []
            if not _knowledge_visible(user_roles, [str(x) for x in vr]):
                continue
            author = await self._admin_brief(doc.created_by_admin_id)
            out.append(
                KnowledgeDocumentResponse(
                    id=doc.id,
                    folder_key=doc.folder_key,
                    title=doc.title,
                    body_md=doc.body_md,
                    visible_roles=[str(x) for x in vr],
                    sort_order=doc.sort_order,
                    created_by=author,
                    updated_at=doc.updated_at,
                )
            )
        return out

    async def create_knowledge(
        self,
        clinic_id: UUID,
        created_by: UUID,
        data: KnowledgeDocumentCreate,
    ) -> KnowledgeDocumentResponse:
        doc = KnowledgeDocument(
            id=uuid.uuid4(),
            clinic_id=clinic_id,
            folder_key=data.folder_key.strip() or "general",
            title=data.title.strip(),
            body_md=data.body_md.strip(),
            visible_roles=list(data.visible_roles),
            sort_order=data.sort_order,
            created_by_admin_id=created_by,
        )
        self._session.add(doc)
        await self._session.flush()
        author = await self._admin_brief(created_by)
        return KnowledgeDocumentResponse(
            id=doc.id,
            folder_key=doc.folder_key,
            title=doc.title,
            body_md=doc.body_md,
            visible_roles=[str(x) for x in doc.visible_roles],
            sort_order=doc.sort_order,
            created_by=author,
            updated_at=doc.updated_at,
        )

    async def update_knowledge(
        self,
        clinic_id: UUID,
        doc_id: UUID,
        data: KnowledgeDocumentUpdate,
    ) -> KnowledgeDocumentResponse | None:
        res = await self._session.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == doc_id,
                KnowledgeDocument.clinic_id == clinic_id,
            )
        )
        doc = res.scalar_one_or_none()
        if doc is None:
            return None
        if data.folder_key is not None:
            doc.folder_key = data.folder_key.strip() or "general"
        if data.title is not None:
            doc.title = data.title.strip()
        if data.body_md is not None:
            doc.body_md = data.body_md.strip()
        if data.visible_roles is not None:
            doc.visible_roles = list(data.visible_roles)
        if data.sort_order is not None:
            doc.sort_order = data.sort_order
        await self._session.flush()
        author = await self._admin_brief(doc.created_by_admin_id)
        return KnowledgeDocumentResponse(
            id=doc.id,
            folder_key=doc.folder_key,
            title=doc.title,
            body_md=doc.body_md,
            visible_roles=[str(x) for x in (doc.visible_roles or [])],
            sort_order=doc.sort_order,
            created_by=author,
            updated_at=doc.updated_at,
        )
