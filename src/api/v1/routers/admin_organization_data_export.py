"""Owner: data export / offboarding hooks (Phase 1e-F3) — manifest, request ticket, safe snapshot."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_request_context, get_session
from src.api.v1.effective_organization import resolve_effective_organization_id
from src.api.v1.routers.admin_auth import get_current_admin
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.booking import Booking
from src.domain.entities.clinic import Clinic
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.organization import Organization
from src.domain.entities.organization_data_export_request import OrganizationDataExportRequest
from src.domain.entities.patient import Patient

router = APIRouter(prefix="/admin/organization/data-export", tags=["admin-data-export"])


def _require_owner(ctx: AdminContext) -> None:
    if "owner" not in ctx.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "owner_role_required",
                "message": "Экспорт и offboarding доступны только владельцу организации.",
            },
        )


async def _clinic_ids_for_organization(session: AsyncSession, organization_id: uuid.UUID) -> list[uuid.UUID]:
    res = await session.execute(select(Clinic.id).where(Clinic.organization_id == organization_id))
    return [row[0] for row in res.all()]


class DataExportSummaryResponse(BaseModel):
    organization_id: str
    clinics: list[dict[str, str]]
    approximate_counts: dict[str, int]
    formats_note: str = Field(
        default="Machine-readable выгрузка PII по запросу OPS; этот endpoint даёт только агрегаты и безопасный манифест.",
    )


@router.get("/summary", response_model=DataExportSummaryResponse)
async def get_data_export_summary(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    ctx: AdminContext = Depends(get_request_context),
) -> DataExportSummaryResponse:
    _require_owner(ctx)
    org_id = await resolve_effective_organization_id(session, admin)
    clinic_ids = await _clinic_ids_for_organization(session, org_id)
    clinics_out: list[dict[str, str]] = []
    if clinic_ids:
        cres = await session.execute(select(Clinic).where(Clinic.id.in_(clinic_ids)))
        for c in cres.scalars():
            clinics_out.append({"id": str(c.id), "name": c.name})

    p_cnt = l_cnt = b_cnt = 0
    if clinic_ids:
        p_cnt = int(
            (
                await session.execute(
                    select(func.count()).select_from(Patient).where(Patient.clinic_id.in_(clinic_ids))
                )
            ).scalar()
            or 0
        )
        l_cnt = int(
            (
                await session.execute(
                    select(func.count()).select_from(LeadCard).where(LeadCard.clinic_id.in_(clinic_ids))
                )
            ).scalar()
            or 0
        )
        b_cnt = int(
            (
                await session.execute(
                    select(func.count()).select_from(Booking).where(Booking.clinic_id.in_(clinic_ids))
                )
            ).scalar()
            or 0
        )

    return DataExportSummaryResponse(
        organization_id=str(org_id),
        clinics=clinics_out,
        approximate_counts={
            "patients": p_cnt,
            "crm_leads": l_cnt,
            "bookings": b_cnt,
            "clinics": len(clinic_ids),
        },
    )


class DataExportRequestBody(BaseModel):
    export_kind: str = Field(default="full_machine_readable", max_length=64)
    note: str | None = Field(None, max_length=500)


class DataExportRequestResponse(BaseModel):
    request_id: str
    status: str
    message: str


@router.post("/request", response_model=DataExportRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_data_export_request(
    body: DataExportRequestBody,
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    ctx: AdminContext = Depends(get_request_context),
) -> DataExportRequestResponse:
    _require_owner(ctx)
    org_id = await resolve_effective_organization_id(session, admin)
    row = OrganizationDataExportRequest(
        id=uuid.uuid4(),
        organization_id=org_id,
        requested_by_admin_id=admin.id,
        status="pending",
        export_kind=body.export_kind.strip()[:64] or "full_machine_readable",
        meta={"note": body.note} if body.note else {},
    )
    session.add(row)
    await session.commit()
    return DataExportRequestResponse(
        request_id=str(row.id),
        status=row.status,
        message="Заявка зарегистрирована. OPS подготовит выгрузку по внутреннему регламенту.",
    )


@router.get("/manifest.jsonl")
async def download_safe_manifest_jsonl(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    ctx: AdminContext = Depends(get_request_context),
) -> Response:
    """Non-PII manifest: org + clinics metadata only (для автоматизации и тикетов)."""
    _require_owner(ctx)
    org_id = await resolve_effective_organization_id(session, admin)
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Организация не найдена")
    clinic_ids = await _clinic_ids_for_organization(session, org_id)
    lines: list[str] = []
    org_line: dict[str, Any] = {
        "type": "organization",
        "id": str(org.id),
        "name": org.name,
        "industry_profile": org.industry_profile,
    }
    lines.append(json.dumps(org_line, ensure_ascii=False))
    if clinic_ids:
        cres = await session.execute(select(Clinic).where(Clinic.id.in_(clinic_ids)))
        for c in cres.scalars():
            lines.append(
                json.dumps(
                    {
                        "type": "clinic",
                        "id": str(c.id),
                        "name": c.name,
                        "organization_id": str(org_id),
                    },
                    ensure_ascii=False,
                )
            )
    body = "\n".join(lines) + "\n"
    return Response(
        content=body,
        media_type="application/x-ndjson; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="export_manifest.jsonl"',
        },
    )
