"""Admin auth: login with email + password (min 8 chars), JWT."""

import logging
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from passlib.hash import pbkdf2_sha256
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.core.config import settings
from src.core.security import create_access_token, parse_access_token
from src.domain.entities.admin_user import AdminUser
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])

MIN_PASSWORD_LENGTH = 8


class AdminLoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=200)


class AdminLoginResponse(BaseModel):
    access_token: str
    admin_id: str
    clinic_id: str
    full_name: str | None


def hash_password(password: str) -> str:
    return pbkdf2_sha256.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pbkdf2_sha256.verify(plain, hashed)


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    data: AdminLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter=Depends(get_rate_limiter),
) -> AdminLoginResponse:
    client_ip = request.client.host if request.client else "unknown"
    email_norm = data.email.strip().lower()
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:admin_login:ip:{client_ip}",
            limit=settings.rate_admin_login_ip_limit,
            window=settings.rate_admin_login_ip_window_seconds,
        )
        await rate_limiter.check_or_raise(
            key=f"rate:admin_login:email:{email_norm}",
            limit=settings.rate_admin_login_email_limit,
            window=settings.rate_admin_login_email_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много попыток. Попробуйте позже.",
        )

    result = await session.execute(
        select(AdminUser).where(
            AdminUser.email == email_norm,
            AdminUser.deleted_at.is_(None),
        ).limit(1)
    )
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    # Admin access token: short-lived; explicit token revocation will be implemented
    # separately according to ARCH_AUTH_SESSIONS.md (token version/blacklist pattern).
    token = create_access_token(
        data={
            "sub": str(admin.id),
            "clinic_id": str(admin.clinic_id),
            "type": "admin",
        },
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes_admin),
    )
    return AdminLoginResponse(
        access_token=token,
        admin_id=str(admin.id),
        clinic_id=str(admin.clinic_id),
        full_name=admin.full_name,
    )


def get_current_admin_dependency():
    """Dependency that extracts Bearer token and returns AdminUser."""
    from fastapi import Depends, Header

    async def _get_current_admin(
        authorization: str | None = Header(None),
        session: AsyncSession = Depends(get_session),
    ) -> AdminUser:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется авторизация",
            )
        token = authorization[7:].strip()
        try:
            payload = parse_access_token(token)
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный или истёкший токен",
            )
        if payload.get("type") != "admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        admin_id = payload.get("sub")
        if not admin_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        result = await session.execute(
            select(AdminUser).where(
                AdminUser.id == UUID(admin_id),
                AdminUser.deleted_at.is_(None),
            ).limit(1)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
        return admin

    return _get_current_admin


get_current_admin = get_current_admin_dependency()


def get_current_admin_optional_dependency():
    """Returns AdminUser if valid token present, else None (no 401)."""
    from fastapi import Depends, Header

    async def _get(
        authorization: str | None = Header(None),
        session: AsyncSession = Depends(get_session),
    ) -> AdminUser | None:
        if not authorization or not authorization.startswith("Bearer "):
            return None
        token = authorization[7:].strip()
        try:
            payload = parse_access_token(token)
        except JWTError:
            return None
        if payload.get("type") != "admin":
            return None
        admin_id = payload.get("sub")
        if not admin_id:
            return None
        result = await session.execute(
            select(AdminUser).where(
                AdminUser.id == UUID(admin_id),
                AdminUser.deleted_at.is_(None),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    return _get


get_current_admin_optional = get_current_admin_optional_dependency()
