"""API dependencies."""

from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.edition import is_box_edition
from src.core.security import parse_access_token
from src.core.user_messages import EMPTY_DB_NO_CLINIC
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.infrastructure.database.base import get_db, get_db_reporting
from src.core.context import RequestContext
from src.application.services.rbac_service import RbacServiceImpl
from src.infrastructure.database.rbac_repo_impl import RbacRepositoryImpl


class AdminContext(RequestContext):
    """Typed alias for admin request context."""

    pass


async def get_session() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_db():
        yield session


async def get_reporting_session() -> AsyncSession:
    """Reporting GETs: optional replica + statement_timeout (ADR-005)."""
    async for session in get_db_reporting():
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
    except jwt.exceptions.InvalidTokenError:
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


async def get_request_context(
    # Keep FastAPI's special injection for Request by keeping annotation as `Request`,
    # but allow direct test calls without passing `request`.
    request: Request = None,
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
) -> RequestContext:
    """
    Build RequestContext from current request.

    For now supports:
    - admin JWT (via get_current_admin)
    - patient JWT (via get_current_patient)
    - unauthenticated/system calls (no token).
    """
    # Try admin first
    from src.domain.entities.admin_user import AdminUser

    admin: AdminUser | None = None
    patient: Patient | None = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        try:
            # Reuse existing token parser to inspect type
            from src.core.security import parse_access_token

            payload = parse_access_token(token)
        except jwt.exceptions.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный или истёкший токен",
            )

        token_type = payload.get("type") or payload.get("role")

        if token_type == "admin":
            # Use existing dependency logic to resolve AdminUser (lazy import to avoid circular deps)
            from src.api.v1.routers.admin_auth import get_current_admin

            admin = await get_current_admin(authorization=authorization, session=session)  # type: ignore[arg-type]
        elif token_type == "patient":
            patient = await get_current_patient(authorization=authorization, session=session)  # type: ignore[arg-type]
        else:
            # Unknown type – treat as unauthorized
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недопустимый тип токена",
            )

    if admin:
        rbac_repo = RbacRepositoryImpl(session)
        rbac_service = RbacServiceImpl(rbac_repo)
        rbac_info = await rbac_service.get_rbac_info_for_user(
            user_id=admin.id,
            clinic_id=admin.clinic_id,
        )
        return RequestContext(
            clinic_id=admin.clinic_id,
            user_id=admin.id,
            user_type="admin",
            trace_id=getattr(getattr(request, "state", None), "trace_id", None),
            roles=set(rbac_info.roles),
            permissions=set(rbac_info.permissions),
        )

    if patient:
        return RequestContext(
            clinic_id=None,
            user_id=patient.id,
            user_type="patient",
            trace_id=getattr(getattr(request, "state", None), "trace_id", None),
            roles=set(),
            permissions=set(),
        )

    # Fallback: system/unauthenticated
    return RequestContext(
        clinic_id=None,
        user_id=None,
        user_type="system",
        trace_id=getattr(getattr(request, "state", None), "trace_id", None),
        roles=set(),
        permissions=set(),
    )


def require_permissions(*permission_codes: str):
    """
    FastAPI dependency factory for RBAC permission checks.

    Usage:
        @router.get("/... ", dependencies=[Depends(require_permissions("view_reports"))])
    """

    async def dependency(context: RequestContext = Depends(get_request_context)) -> AdminContext:
        if context.user_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        if permission_codes:
            if not any(code in context.permissions for code in permission_codes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden",
                )
        # Cast to AdminContext for downstream type hints
        admin_context = AdminContext(
            clinic_id=context.clinic_id,
            user_id=context.user_id,
            user_type=context.user_type,
            trace_id=context.trace_id,
            roles=context.roles,
            permissions=context.permissions,
        )
        return admin_context

    return dependency


async def require_crm_enterprise_edition() -> None:
    """CRM / sales pipeline недоступны в редакции коробки (`EDITION=box|basic`)."""
    if is_box_edition():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "box_forbidden",
                "message": "CRM / Sales pipeline is available only in Enterprise edition.",
            },
        )

