"""Admin staff profile card API (clinic-scoped AdminUser profile)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.dto.staff_directory_dto import StaffDirectoryAdminRead
from src.core.config import settings
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.staff_profession_category import StaffProfessionCategory
from src.domain.entities.staff_profile import StaffProfile
from src.infrastructure.storage.s3_storage import StaffAvatarsStorage

router = APIRouter(prefix="/admin/staff", tags=["admin-staff-profile"])

ALLOWED_AVATAR_CT = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _sniff_magic(buf: bytes) -> str | None:
    if not buf:
        return None
    if buf.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if buf.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if buf.startswith(b"GIF87a") or buf.startswith(b"GIF89a"):
        return "image/gif"
    if buf.startswith(b"RIFF") and buf[8:12] == b"WEBP":
        return "image/webp"
    return None


async def _get_or_create_profile(session: AsyncSession, *, clinic_id: UUID, admin_id: UUID) -> StaffProfile:
    res = await session.execute(select(StaffProfile).where(StaffProfile.admin_id == admin_id).limit(1))
    row = res.scalar_one_or_none()
    if row is not None:
        return row
    row = StaffProfile(admin_id=admin_id, clinic_id=clinic_id, bio="", avatar_s3_key=None, avatar_updated_at=None)
    session.add(row)
    await session.flush()
    return row


def _avatar_url(admin_id: UUID) -> str:
    # Relative to API v1 prefix; frontend uses `/v1/...`.
    return f"/v1/admin/staff/avatars/{admin_id}"


@router.get("/profiles/{admin_id}", response_model=StaffDirectoryAdminRead)
async def get_staff_profile(
    admin_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> StaffDirectoryAdminRead:
    """Read staff profile card for any admin inside the same clinic."""
    clinic_id = current_admin.clinic_id

    q = (
        select(AdminUser, StaffProfessionCategory.name)
        .outerjoin(
            StaffProfessionCategory,
            StaffProfessionCategory.id == AdminUser.profession_category_id,
        )
        .where(
            AdminUser.id == admin_id,
            AdminUser.deleted_at.is_(None),
        )
        .limit(1)
    )
    res = await session.execute(q)
    row = res.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")
    admin, profession_name = row

    if admin.clinic_id != clinic_id:
        # Hide existence across clinics.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")

    prof = await _get_or_create_profile(session, clinic_id=clinic_id, admin_id=admin.id)

    # If profession category is from another clinic (should not happen), do not leak it.
    if admin.profession_category_id and profession_name:
        pc = await session.execute(
            select(StaffProfessionCategory).where(
                StaffProfessionCategory.id == admin.profession_category_id,
                StaffProfessionCategory.clinic_id == clinic_id,
                StaffProfessionCategory.deleted_at.is_(None),
            )
        )
        if pc.scalar_one_or_none() is None:
            profession_name = None

    return StaffDirectoryAdminRead(
        id=str(admin.id),
        clinic_id=str(admin.clinic_id),
        email=admin.email,
        full_name=admin.full_name,
        birth_date=admin.birth_date.isoformat() if admin.birth_date else None,
        employment_status=admin.employment_status,
        profession_category_id=str(admin.profession_category_id) if admin.profession_category_id else None,
        profession_category_name=profession_name,
        bio=(prof.bio or "").strip() or None,
        avatar_url=_avatar_url(admin.id) if prof.avatar_s3_key else None,
    )


@router.get(
    "/me/profile",
    response_model=StaffDirectoryAdminRead,
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def get_my_staff_profile(
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> StaffDirectoryAdminRead:
    """Read current staff profile (for personal cabinet)."""
    # Reuse existing card logic.
    return await get_staff_profile(current_admin.id, session=session, current_admin=current_admin)


@router.patch(
    "/me/profile",
    response_model=StaffDirectoryAdminRead,
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def patch_my_staff_profile(
    body: dict,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> StaffDirectoryAdminRead:
    """Patch my staff profile fields (currently: bio)."""
    clinic_id = current_admin.clinic_id
    prof = await _get_or_create_profile(session, clinic_id=clinic_id, admin_id=current_admin.id)
    if "bio" in body:
        raw = body.get("bio")
        bio = str(raw or "").strip()
        # Keep it bounded for UI; hard limit to prevent abuse.
        if len(bio) > 2000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bio слишком длинный")
        prof.bio = bio
        await session.flush()
    return await get_staff_profile(current_admin.id, session=session, current_admin=current_admin)


@router.post(
    "/me/avatar",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def upload_my_avatar(
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    file: UploadFile = File(...),
) -> dict:
    clinic_id = current_admin.clinic_id
    max_bytes = int(settings.staff_avatar_max_bytes or 0)
    if max_bytes <= 0:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Avatar upload limit not configured")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_AVATAR_CT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый тип файла")

    raw = await file.read()
    try:
        await file.close()
    except Exception:
        pass

    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пустой файл")
    if len(raw) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Файл слишком большой")

    sniffed = _sniff_magic(raw[:16])
    if sniffed != content_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл не соответствует заявленному типу")

    prof = await _get_or_create_profile(session, clinic_id=clinic_id, admin_id=current_admin.id)
    if not (settings.s3_endpoint and settings.s3_bucket and settings.s3_access_key and settings.s3_secret_key):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 not configured")

    store = StaffAvatarsStorage()
    filename = os.path.basename(file.filename or "avatar")
    key = store.build_key(clinic_id=str(clinic_id), admin_id=str(current_admin.id), filename=filename)
    try:
        store.put_bytes(key=key, content=raw, content_type=content_type)
    except RuntimeError as e:
        if str(e) == "s3_sdk_missing":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 SDK missing") from e
        if str(e) == "s3_not_configured":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 not configured") from e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 upload failed") from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 upload failed") from e

    prof.avatar_s3_key = key
    prof.avatar_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await session.flush()
    return {"avatar_url": _avatar_url(current_admin.id)}


@router.get(
    "/avatars/{admin_id}",
    dependencies=[Depends(require_permissions("view_staff_collab"))],
)
async def get_staff_avatar_redirect(
    admin_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
) -> RedirectResponse:
    """Return a short-lived presigned URL for staff avatar (clinic-scoped)."""
    clinic_id = current_admin.clinic_id

    # Hide existence across clinics.
    res = await session.execute(
        select(AdminUser.id, AdminUser.clinic_id, AdminUser.deleted_at, AdminUser.employment_status).where(
            AdminUser.id == admin_id
        ).limit(1)
    )
    row = res.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")
    _id, target_clinic_id, deleted_at, _emp = row
    if deleted_at is not None or target_clinic_id != clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден")

    prof_res = await session.execute(select(StaffProfile).where(StaffProfile.admin_id == admin_id).limit(1))
    prof = prof_res.scalar_one_or_none()
    if prof is None or not prof.avatar_s3_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аватар не найден")

    store = StaffAvatarsStorage()
    try:
        url = store.presign_get(key=prof.avatar_s3_key, exp_seconds=settings.s3_staff_avatars_presign_exp_seconds)
    except RuntimeError as e:
        if str(e) == "s3_sdk_missing":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 SDK missing") from e
        if str(e) == "s3_not_configured":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 not configured") from e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 presign failed") from e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 presign failed") from e

    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

