"""API dependencies."""

from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import parse_access_token
from src.core.user_messages import EMPTY_DB_NO_CLINIC
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.infrastructure.database.base import get_db


async def get_session() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_db():
        yield session


async def get_default_clinic(session: AsyncSession) -> Clinic:
    """Get the default (first) clinic for single-clinic instance. Raises 404 if none."""
    result = await session.execute(select(Clinic).limit(1))
    clinic = result.scalar_one_or_none()
    if clinic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EMPTY_DB_NO_CLINIC)
    return clinic


async def get_default_clinic_id(session: AsyncSession = Depends(get_session)) -> UUID:
    """Get default clinic UUID for create operations. Depends on get_session so FastAPI injects it."""
    clinic = await get_default_clinic(session)
    return clinic.id


async def get_current_patient(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> Patient:
    """Extract current patient from Bearer token and load entity."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    token = authorization[7:].strip()
    try:
        payload = parse_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истёкший токен",
        )
    if payload.get("role") != "patient":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token role")
    patient_sub = payload.get("sub")
    if not patient_sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await session.execute(
        select(Patient).where(
            Patient.id == UUID(patient_sub),
            Patient.deleted_at.is_(None),
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Patient not found")
    return patient

