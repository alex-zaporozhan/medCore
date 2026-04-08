"""Admin API: Kanban board layouts (columns map to task.status — variant A)."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.v1.entitlement_dependencies import require_entitlement
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.v1.dependencies import AdminContext, get_request_context, get_session, require_permissions
from src.application.dto.task_dto import TASK_STATUSES
from src.domain.entities.task_board import TaskBoard
from src.domain.entities.task_board_column import TaskBoardColumn

router = APIRouter(
    prefix="/admin/task-boards",
    tags=["admin-task-boards"],
    dependencies=[Depends(require_entitlement("tasks.kanban"))],
)

_STATUS_SET = frozenset(TASK_STATUSES)


def err_payload(detail: str, code: str, field: str | None = None) -> dict:
    return {"detail": detail, "code": code, "field": field}


class TaskBoardColumnOut(BaseModel):
    id: UUID
    sort_order: int
    mapped_status: str
    label: str | None = None


class TaskBoardOut(BaseModel):
    id: UUID
    clinic_id: UUID
    name: str
    kind: str
    owner_admin_id: UUID | None = None
    columns: list[TaskBoardColumnOut] = Field(default_factory=list)


class TaskBoardColumnUpdateItem(BaseModel):
    mapped_status: str
    label: str | None = None


class CreatePersonalBoardBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)


class ReplaceTaskBoardColumnsBody(BaseModel):
    columns: list[TaskBoardColumnUpdateItem]


async def _ensure_default_clinic_board(session: AsyncSession, clinic_id: UUID) -> TaskBoard:
    res = await session.execute(
        select(TaskBoard)
        .where(
            TaskBoard.clinic_id == clinic_id,
            TaskBoard.kind == "clinic_wide",
            TaskBoard.owner_admin_id.is_(None),
        )
        .options(selectinload(TaskBoard.columns))
    )
    existing = res.scalar_one_or_none()
    if existing is not None:
        return existing
    board = TaskBoard(
        id=uuid4(),
        clinic_id=clinic_id,
        name="Основная",
        kind="clinic_wide",
        owner_admin_id=None,
    )
    try:
        async with session.begin_nested():
            session.add(board)
            await session.flush()
            for i, st in enumerate(TASK_STATUSES, start=1):
                session.add(
                    TaskBoardColumn(
                        id=uuid4(),
                        board_id=board.id,
                        sort_order=i,
                        mapped_status=st,
                        label=None,
                    )
                )
            await session.flush()
    except IntegrityError:
        res2 = await session.execute(
            select(TaskBoard)
            .where(
                TaskBoard.clinic_id == clinic_id,
                TaskBoard.kind == "clinic_wide",
                TaskBoard.owner_admin_id.is_(None),
            )
            .options(selectinload(TaskBoard.columns))
        )
        return res2.scalar_one()
    await session.refresh(board, ["columns"])
    return board


def _board_to_out(board: TaskBoard) -> TaskBoardOut:
    cols = sorted(board.columns, key=lambda c: c.sort_order)
    return TaskBoardOut(
        id=board.id,
        clinic_id=board.clinic_id,
        name=board.name,
        kind=board.kind,
        owner_admin_id=board.owner_admin_id,
        columns=[
            TaskBoardColumnOut(
                id=c.id,
                sort_order=c.sort_order,
                mapped_status=c.mapped_status,
                label=c.label,
            )
            for c in cols
        ],
    )


@router.get(
    "",
    response_model=list[TaskBoardOut],
    dependencies=[Depends(require_permissions("view_tasks"))],
)
async def list_task_boards(
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> list[TaskBoardOut]:
    """Boards for current clinic: clinic-wide + current user's personal boards."""
    clinic_id = context.clinic_id
    if clinic_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic context is required")
    if context.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User context is required")

    await _ensure_default_clinic_board(session, clinic_id)

    stmt = (
        select(TaskBoard)
        .where(TaskBoard.clinic_id == clinic_id)
        .where(
            or_(
                TaskBoard.kind == "clinic_wide",
                TaskBoard.owner_admin_id == context.user_id,
            )
        )
        .options(selectinload(TaskBoard.columns))
        .order_by(TaskBoard.kind.asc(), TaskBoard.name.asc())
    )
    res = await session.execute(stmt)
    boards = list(res.scalars().unique().all())
    return [_board_to_out(b) for b in boards]


@router.post(
    "",
    response_model=TaskBoardOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def create_personal_task_board(
    body: CreatePersonalBoardBody,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskBoardOut:
    """Create a personal board (same workflow statuses; columns default to full pipeline)."""
    clinic_id = context.clinic_id
    uid = context.user_id
    if clinic_id is None or uid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic and user context required")
    name = body.name.strip()
    board = TaskBoard(
        id=uuid4(),
        clinic_id=clinic_id,
        name=name,
        kind="personal",
        owner_admin_id=uid,
    )
    session.add(board)
    await session.flush()
    for i, st in enumerate(TASK_STATUSES, start=1):
        session.add(
            TaskBoardColumn(
                id=uuid4(),
                board_id=board.id,
                sort_order=i,
                mapped_status=st,
                label=None,
            )
        )
    await session.flush()
    res = await session.execute(
        select(TaskBoard).where(TaskBoard.id == board.id).options(selectinload(TaskBoard.columns))
    )
    b = res.scalar_one()
    return _board_to_out(b)


@router.put(
    "/{board_id}/columns",
    response_model=TaskBoardOut,
    dependencies=[Depends(require_permissions("manage_tasks"))],
)
async def replace_task_board_columns(
    board_id: UUID,
    body: ReplaceTaskBoardColumnsBody,
    session: AsyncSession = Depends(get_session),
    context: AdminContext = Depends(get_request_context),
) -> TaskBoardOut:
    """Replace column order and labels; must include each status at most once (full pipeline subset allowed)."""
    clinic_id = context.clinic_id
    uid = context.user_id
    if clinic_id is None or uid is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clinic and user context required")

    res = await session.execute(
        select(TaskBoard).where(TaskBoard.id == board_id, TaskBoard.clinic_id == clinic_id)
    )
    board = res.scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")

    if board.kind == "personal":
        if board.owner_admin_id != uid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your board")
    elif board.kind == "clinic_wide":
        if "tasks.manage_clinic_board" not in context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=err_payload(
                    "Недостаточно прав для изменения общей доски клиники",
                    "CLINIC_BOARD_FORBIDDEN",
                ),
            )

    mapped = [c.mapped_status for c in body.columns]
    if len(mapped) != len(set(mapped)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_payload("Duplicate mapped_status", "VALIDATION_ERROR", field="columns"),
        )
    for c in body.columns:
        if c.mapped_status not in _STATUS_SET:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=err_payload("Invalid status", "VALIDATION_ERROR", field="columns"),
            )
    if set(mapped) != _STATUS_SET:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_payload(
                "columns must list each task status exactly once",
                "INVALID_COLUMN_SET",
                field="columns",
            ),
        )

    await session.execute(delete(TaskBoardColumn).where(TaskBoardColumn.board_id == board_id))
    for i, item in enumerate(body.columns, start=1):
        label_val: str | None = None
        if item.label is not None:
            s = str(item.label).strip()
            if s:
                label_val = s[:128]
        session.add(
            TaskBoardColumn(
                id=uuid4(),
                board_id=board_id,
                sort_order=i,
                mapped_status=item.mapped_status,
                label=label_val,
            )
        )
    await session.flush()
    out = await session.execute(
        select(TaskBoard).where(TaskBoard.id == board_id).options(selectinload(TaskBoard.columns))
    )
    b = out.scalar_one()
    return _board_to_out(b)
