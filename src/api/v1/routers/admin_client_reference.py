"""Admin: client reference (problems and scenarios) for handover to client. Editable, stored in DB."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.core.patient_messages import REFERENCE_FOR_CLIENT
from src.domain.entities.client_reference import ClientReference

router = APIRouter(prefix="/admin/client-reference", tags=["admin-client-reference"])


class ClientReferenceBody(BaseModel):
    content: str = ""


async def _get_row(session: AsyncSession) -> ClientReference | None:
    result = await session.execute(select(ClientReference).limit(1))
    return result.scalar_one_or_none()


@router.get("", response_model=dict)
async def get_client_reference(session: AsyncSession = Depends(get_session)) -> dict:
    """Return the client reference content. From DB if set, else default from code."""
    row = await _get_row(session)
    if row and row.content and row.content.strip():
        return {"content": row.content}
    return {"content": REFERENCE_FOR_CLIENT}


@router.put("", response_model=dict)
async def put_client_reference(
    body: ClientReferenceBody,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Update the client reference content (stored in DB)."""
    row = await _get_row(session)
    if not row:
        row = ClientReference(content=body.content)
        session.add(row)
        await session.flush()
    else:
        row.content = body.content
    await session.flush()
    await session.refresh(row)
    return {"content": row.content}
