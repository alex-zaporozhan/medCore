"""Admin: per-organization RAG KB documents (§24.3), entitlement ai.rag.org_kb."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session, require_permissions
from src.api.v1.effective_organization import resolve_effective_organization_id
from src.api.v1.entitlement_dependencies import require_entitlement
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.organization_entitlement_access import (
    ensure_org_has_any_entitlement_for_organization,
)
from src.application.services.organization_rag_kb_service import (
    count_documents_for_org,
    create_document,
    delete_document,
    get_document,
    list_documents,
    update_document,
)
from src.application.services.rag_kb_audit_service import log_rag_kb_audit
from src.core.config import settings
from src.domain.entities.admin_user import AdminUser

router = APIRouter(
    prefix="/admin/organization/rag-kb",
    tags=["admin-rag-kb"],
    dependencies=[Depends(require_entitlement("ai.rag.org_kb"))],
)


class RagDocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=50_000)


class RagDocumentItem(BaseModel):
    id: str
    title: str
    body_preview: str
    updated_at: str


class RagDocumentDetail(BaseModel):
    id: str
    title: str
    body: str
    updated_at: str


class RagDocumentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    body: str | None = Field(None, min_length=1, max_length=50_000)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "RagDocumentUpdate":
        if self.title is None and self.body is None:
            raise ValueError("Укажите title и/или body")
        return self


class RagDocumentListResponse(BaseModel):
    items: list[RagDocumentItem]


@router.get("/documents", response_model=RagDocumentListResponse)
async def list_rag_documents(
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("view_crm")),
) -> RagDocumentListResponse:
    org_id = await resolve_effective_organization_id(session, admin)
    await ensure_org_has_any_entitlement_for_organization(session, org_id, "ai.rag.org_kb")
    rows = await list_documents(session, org_id, limit=100)
    items = [
        RagDocumentItem(
            id=str(r.id),
            title=r.title,
            body_preview=(r.body[:240] + "…") if len(r.body) > 240 else r.body,
            updated_at=r.updated_at.isoformat(),
        )
        for r in rows
    ]
    return RagDocumentListResponse(items=items)


@router.get("/documents/{document_id}", response_model=RagDocumentDetail)
async def get_rag_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("view_crm")),
) -> RagDocumentDetail:
    org_id = await resolve_effective_organization_id(session, admin)
    await ensure_org_has_any_entitlement_for_organization(session, org_id, "ai.rag.org_kb")
    row = await get_document(session, org_id, document_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "rag_document_not_found", "message": "Фрагмент базы знаний не найден"},
        )
    return RagDocumentDetail(
        id=str(row.id),
        title=row.title,
        body=row.body,
        updated_at=row.updated_at.isoformat(),
    )


@router.patch("/documents/{document_id}", response_model=RagDocumentDetail)
async def patch_rag_document(
    document_id: uuid.UUID,
    body: RagDocumentUpdate,
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("manage_crm")),
) -> RagDocumentDetail:
    org_id = await resolve_effective_organization_id(session, admin)
    await ensure_org_has_any_entitlement_for_organization(session, org_id, "ai.rag.org_kb")
    row = await update_document(
        session,
        org_id,
        document_id,
        title=body.title,
        body=body.body,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "rag_document_not_found", "message": "Фрагмент базы знаний не найден"},
        )
    await log_rag_kb_audit(
        session,
        organization_id=org_id,
        actor_admin_id=admin.id,
        action="rag_kb_document_updated",
        document_id=row.id,
        meta={"title": row.title[:200]},
    )
    await session.commit()
    return RagDocumentDetail(
        id=str(row.id),
        title=row.title,
        body=row.body,
        updated_at=row.updated_at.isoformat(),
    )


@router.post("/documents", response_model=RagDocumentItem, status_code=status.HTTP_201_CREATED)
async def create_rag_document(
    body: RagDocumentCreate,
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("manage_crm")),
) -> RagDocumentItem:
    org_id = await resolve_effective_organization_id(session, admin)
    await ensure_org_has_any_entitlement_for_organization(session, org_id, "ai.rag.org_kb")
    cap = settings.rag_kb_quota_max_documents_per_org
    if cap > 0:
        n = await count_documents_for_org(session, org_id)
        if n >= cap:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "rag_kb_quota_exceeded",
                    "message": "Достигнут лимит фрагментов базы знаний для организации",
                    "max_documents": cap,
                },
            )
    row = await create_document(session, org_id, title=body.title, body=body.body)
    await log_rag_kb_audit(
        session,
        organization_id=org_id,
        actor_admin_id=admin.id,
        action="rag_kb_document_created",
        document_id=row.id,
        meta={"title": row.title[:200]},
    )
    await session.commit()
    return RagDocumentItem(
        id=str(row.id),
        title=row.title,
        body_preview=(row.body[:240] + "…") if len(row.body) > 240 else row.body,
        updated_at=row.updated_at.isoformat(),
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_rag_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    admin: AdminUser = Depends(get_current_admin),
    _: None = Depends(require_permissions("manage_crm")),
) -> None:
    org_id = await resolve_effective_organization_id(session, admin)
    await ensure_org_has_any_entitlement_for_organization(session, org_id, "ai.rag.org_kb")
    snap = await delete_document(session, org_id, document_id)
    if snap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "rag_document_not_found", "message": "Фрагмент базы знаний не найден"},
        )
    await log_rag_kb_audit(
        session,
        organization_id=org_id,
        actor_admin_id=admin.id,
        action="rag_kb_document_deleted",
        document_id=snap.id,
        meta={"title": snap.title[:200]},
    )
    await session.commit()
