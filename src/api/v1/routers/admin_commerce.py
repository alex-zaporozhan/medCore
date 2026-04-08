"""Admin Commerce API (Phase 4, ADR-013): entitlement `commerce.store_network`, separate from ERP inventory."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import AdminContext, get_session, require_permissions
from src.api.v1.entitlement_dependencies import require_entitlement
from src.api.v1.routers.admin_auth import get_current_admin
from src.application.services.commerce_import_job_service import (
    COMMERCE_IMPORT_STATUS_COMMITTED,
    CommerceImportJobError,
    build_commerce_import_payload_summary,
    list_import_jobs_for_clinic,
    try_replay_committed_import,
    upsert_import_job_record,
)
from src.application.services.commerce_store_service import (
    COMMERCE_CSV_IMPORT_MAX_ROWS,
    COMMERCE_NOMENCLATURE_CSV_PROFILE,
    COMMERCE_STOCK_BALANCES_CSV_PROFILE,
    CommerceBalanceLine,
    CommerceCsvImportResult,
    CommerceDocumentLineDetail,
    CommerceStoreError,
    apply_nomenclature_patch,
    apply_stock_location_patch,
    count_locations,
    count_nomenclature,
    create_nomenclature_item,
    create_stock_location,
    delete_nomenclature_item,
    delete_stock_location,
    get_movement_document,
    get_nomenclature_item,
    get_stock_location,
    import_nomenclature_csv,
    import_stock_balances_csv,
    list_balance_lines_for_location,
    list_document_line_details,
    list_movement_documents,
    list_nomenclature_items,
    list_stock_locations,
    post_movement_document,
    resolve_org_for_clinic,
    upsert_stock_balance,
)
from src.core.openapi_error_schemas import OPENAPI_403_ENTITLEMENT_GATE_RESPONSE
from src.domain.entities.admin_user import AdminUser

router = APIRouter(
    prefix="/admin/clinics",
    tags=["admin-commerce"],
    dependencies=[Depends(require_entitlement("commerce.store_network"))],
    responses={403: OPENAPI_403_ENTITLEMENT_GATE_RESPONSE},
)


def _idempotency_client_and_storage_key(request: Request) -> tuple[str | None, str]:
    raw = (request.headers.get("Idempotency-Key") or "").strip()[:255]
    if raw:
        return raw, raw
    return None, str(uuid.uuid4())


async def _commerce_replay_after_integrity_rollback(
    session: AsyncSession,
    *,
    organization_id: UUID,
    idem_client: str | None,
    source_profile: str,
    clinic_id: UUID,
    stock_location_id: UUID | None,
) -> CommerceCsvImportResult | None:
    """After rollback on IntegrityError: winner of concurrent idempotent import may have committed the job."""
    if not idem_client:
        return None
    try:
        return await try_replay_committed_import(
            session,
            organization_id,
            idem_client,
            source_profile=source_profile,
            clinic_id=clinic_id,
            stock_location_id=stock_location_id,
        )
    except CommerceImportJobError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "commerce_import_idempotency_scope_mismatch",
                "message": "Idempotency-Key уже использован для другого профиля или точки",
            },
        ) from None


async def _guard_clinic_org(
    clinic_id: UUID,
    admin: AdminUser,
    session: AsyncSession,
) -> UUID:
    if admin.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "organization_required", "message": "У администратора нет organization_id"},
        )
    if clinic_id != admin.clinic_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    try:
        org_id = await resolve_org_for_clinic(session, clinic_id)
    except CommerceStoreError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found") from None
    if org_id != admin.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "commerce_clinic_org_mismatch",
                "message": "Клиника не принадлежит организации администратора",
            },
        )
    return org_id


class CommerceOverviewResponse(BaseModel):
    clinic_id: str
    organization_id: str
    stock_locations_count: int
    nomenclature_items_count: int


class CommerceStockLocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str | None
    is_default: bool
    created_at: datetime


class CommerceStockLocationCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str | None = Field(None, max_length=64)
    is_default: bool = False


class CommerceStockLocationPatchBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = None
    is_default: bool | None = None


@router.get(
    "/{clinic_id}/commerce/stock-locations",
    response_model=list[CommerceStockLocationRead],
)
async def list_commerce_stock_locations(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> list[CommerceStockLocationRead]:
    await _guard_clinic_org(clinic_id, current_admin, session)
    rows = await list_stock_locations(session, clinic_id)
    return [CommerceStockLocationRead.model_validate(r) for r in rows]


@router.post(
    "/{clinic_id}/commerce/stock-locations",
    response_model=CommerceStockLocationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_commerce_stock_location(
    clinic_id: UUID,
    body: CommerceStockLocationCreateBody,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> CommerceStockLocationRead:
    org_id = await _guard_clinic_org(clinic_id, current_admin, session)
    row = await create_stock_location(
        session,
        organization_id=org_id,
        clinic_id=clinic_id,
        name=body.name,
        code=body.code,
        is_default=body.is_default,
    )
    await session.commit()
    return CommerceStockLocationRead.model_validate(row)


@router.patch(
    "/{clinic_id}/commerce/stock-locations/{location_id}",
    response_model=CommerceStockLocationRead,
)
async def patch_commerce_stock_location(
    clinic_id: UUID,
    location_id: UUID,
    body: CommerceStockLocationPatchBody,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> CommerceStockLocationRead:
    await _guard_clinic_org(clinic_id, current_admin, session)
    row = await get_stock_location(session, location_id, clinic_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "commerce_stock_location_not_found", "message": "Точка не найдена"},
        )
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return CommerceStockLocationRead.model_validate(row)
    await apply_stock_location_patch(session, row, patch)
    await session.commit()
    await session.refresh(row)
    return CommerceStockLocationRead.model_validate(row)


@router.delete(
    "/{clinic_id}/commerce/stock-locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_commerce_stock_location(
    clinic_id: UUID,
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> None:
    await _guard_clinic_org(clinic_id, current_admin, session)
    ok = await delete_stock_location(session, location_id, clinic_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "commerce_stock_location_not_found", "message": "Точка не найдена"},
        )
    await session.commit()


class CommerceStockBalanceLineRead(BaseModel):
    balance_id: UUID | None = None
    nomenclature_item_id: UUID
    sku: str | None
    name: str
    unit: str
    quantity: Decimal


def _balance_line_to_read(line: CommerceBalanceLine) -> CommerceStockBalanceLineRead:
    return CommerceStockBalanceLineRead(
        balance_id=line.balance_id,
        nomenclature_item_id=line.nomenclature_item_id,
        sku=line.sku,
        name=line.name,
        unit=line.unit,
        quantity=line.quantity,
    )


@router.get(
    "/{clinic_id}/commerce/stock-locations/{location_id}/balances",
    response_model=list[CommerceStockBalanceLineRead],
)
async def list_commerce_stock_balances(
    clinic_id: UUID,
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> list[CommerceStockBalanceLineRead]:
    await _guard_clinic_org(clinic_id, current_admin, session)
    loc = await get_stock_location(session, location_id, clinic_id)
    if loc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "commerce_stock_location_not_found", "message": "Точка не найдена"},
        )
    lines = await list_balance_lines_for_location(session, clinic_id, location_id)
    return [_balance_line_to_read(x) for x in lines]


class CommerceStockBalanceImportSpecResponse(BaseModel):
    profile: str
    encoding: str = "utf-8"
    description: str
    required_columns: list[str]
    optional_columns: list[str]
    max_rows: int
    scope: str
    notes: list[str]
    example_csv: str


@router.get(
    "/{clinic_id}/commerce/stock-locations/{location_id}/balances/import-spec",
    response_model=CommerceStockBalanceImportSpecResponse,
)
async def commerce_stock_balance_import_spec(
    clinic_id: UUID,
    location_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> CommerceStockBalanceImportSpecResponse:
    """Contract for per-location stock quantity CSV (4-F4b)."""
    await _guard_clinic_org(clinic_id, current_admin, session)
    loc = await get_stock_location(session, location_id, clinic_id)
    if loc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "commerce_stock_location_not_found", "message": "Точка не найдена"},
        )
    return CommerceStockBalanceImportSpecResponse(
        profile=COMMERCE_STOCK_BALANCES_CSV_PROFILE,
        description="Выставление остатков на одной точке; sku должен совпадать с номенклатурой клиники.",
        required_columns=["sku", "quantity"],
        optional_columns=[],
        max_rows=COMMERCE_CSV_IMPORT_MAX_ROWS,
        scope=f"stock_location_id={location_id} (остатки только на этой точке).",
        notes=[
            "quantity — неотрицательное число; допускается десятичная запятая в файле.",
            "Позиции без sku в номенклатуре пропускаются, строка попадает в errors в ответе.",
            "Заголовок HTTP Idempotency-Key: повтор с тем же ключом возвращает тот же результат без повторной записи (тот же профиль и location_id).",
        ],
        example_csv="sku,quantity\nART-001,10\nART-002,0.5\n",
    )


class CommerceCsvImportResponse(BaseModel):
    profile: str
    created: int
    updated: int
    skipped: int
    errors: list[str]


@router.post(
    "/{clinic_id}/commerce/stock-locations/{location_id}/balances/import-csv",
    response_model=CommerceCsvImportResponse,
)
async def commerce_stock_balance_import_csv(
    request: Request,
    clinic_id: UUID,
    location_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> CommerceCsvImportResponse:
    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "commerce_import_invalid_content_type",
                "message": "Ожидается CSV (text/csv)",
            },
        )
    try:
        raw_bytes = await file.read()
        content = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "commerce_import_decode_error",
                "message": "Файл должен быть в кодировке UTF-8",
            },
        ) from exc

    fname = ((file.filename or "upload.csv").strip()[:255] or "upload.csv")
    org_id = await _guard_clinic_org(clinic_id, current_admin, session)
    idem_client, idem_stored = _idempotency_client_and_storage_key(request)

    try:
        replay = await try_replay_committed_import(
            session,
            org_id,
            idem_client,
            source_profile=COMMERCE_STOCK_BALANCES_CSV_PROFILE,
            clinic_id=clinic_id,
            stock_location_id=location_id,
        )
    except CommerceImportJobError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "commerce_import_idempotency_scope_mismatch",
                "message": "Idempotency-Key уже использован для другого профиля или точки",
            },
        ) from None

    if replay is not None:
        return CommerceCsvImportResponse(
            profile=COMMERCE_STOCK_BALANCES_CSV_PROFILE,
            created=replay.created,
            updated=replay.updated,
            skipped=replay.skipped,
            errors=replay.errors,
        )

    try:
        result = await import_stock_balances_csv(
            session,
            organization_id=org_id,
            clinic_id=clinic_id,
            location_id=location_id,
            content=content,
        )
        await upsert_import_job_record(
            session,
            organization_id=org_id,
            clinic_id=clinic_id,
            stock_location_id=location_id,
            source_profile=COMMERCE_STOCK_BALANCES_CSV_PROFILE,
            idempotency_key_stored=idem_stored,
            file_name=fname,
            created_by_admin_id=current_admin.id,
            status=COMMERCE_IMPORT_STATUS_COMMITTED,
            payload_summary=build_commerce_import_payload_summary(
                source_profile=COMMERCE_STOCK_BALANCES_CSV_PROFILE,
                file_name=fname,
                result=result,
            ),
            last_error=None,
        )
        await session.commit()
    except CommerceStoreError as e:
        await session.rollback()
        code = str(e)
        if code == "stock_location_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "commerce_stock_location_not_found", "message": "Точка не найдена"},
            ) from None
        if code == "csv_no_header":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_import_csv_no_header", "message": "Пустой или некорректный CSV"},
            ) from None
        if code == "csv_balance_columns":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "commerce_import_csv_balance_columns",
                    "message": "Нужны колонки sku и quantity в заголовке",
                },
            ) from None
        if code == "csv_too_many_rows":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "commerce_import_csv_too_many_rows",
                    "message": f"Не более {COMMERCE_CSV_IMPORT_MAX_ROWS} строк данных",
                },
            ) from None
        raise
    except IntegrityError:
        await session.rollback()
        replay_after = await _commerce_replay_after_integrity_rollback(
            session,
            organization_id=org_id,
            idem_client=idem_client,
            source_profile=COMMERCE_STOCK_BALANCES_CSV_PROFILE,
            clinic_id=clinic_id,
            stock_location_id=location_id,
        )
        if replay_after is not None:
            return CommerceCsvImportResponse(
                profile=COMMERCE_STOCK_BALANCES_CSV_PROFILE,
                created=replay_after.created,
                updated=replay_after.updated,
                skipped=replay_after.skipped,
                errors=replay_after.errors,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "commerce_balance_import_conflict", "message": "Конфликт при записи остатков"},
        ) from None

    return CommerceCsvImportResponse(
        profile=COMMERCE_STOCK_BALANCES_CSV_PROFILE,
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
    )


class CommerceStockBalancePutBody(BaseModel):
    quantity: Decimal = Field(..., ge=0)


@router.put(
    "/{clinic_id}/commerce/stock-locations/{location_id}/balances/{item_id}",
    response_model=CommerceStockBalanceLineRead,
)
async def put_commerce_stock_balance(
    clinic_id: UUID,
    location_id: UUID,
    item_id: UUID,
    body: CommerceStockBalancePutBody,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> CommerceStockBalanceLineRead:
    org_id = await _guard_clinic_org(clinic_id, current_admin, session)
    try:
        await upsert_stock_balance(
            session,
            organization_id=org_id,
            clinic_id=clinic_id,
            location_id=location_id,
            item_id=item_id,
            quantity=body.quantity,
        )
        await session.commit()
    except CommerceStoreError as e:
        code = str(e)
        if code == "quantity_negative":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_quantity_invalid", "message": "Количество не может быть отрицательным"},
            ) from None
        if code == "stock_location_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "commerce_stock_location_not_found", "message": "Точка не найдена"},
            ) from None
        if code == "nomenclature_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "commerce_nomenclature_not_found", "message": "Позиция не найдена"},
            ) from None
        raise
    lines = await list_balance_lines_for_location(session, clinic_id, location_id)
    for ln in lines:
        if ln.nomenclature_item_id == item_id:
            return _balance_line_to_read(ln)
    raise HTTPException(status_code=500, detail="balance_line_missing_after_upsert")


@router.get(
    "/{clinic_id}/commerce/overview",
    response_model=CommerceOverviewResponse,
)
async def commerce_overview(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> CommerceOverviewResponse:
    org_id = await _guard_clinic_org(clinic_id, current_admin, session)
    loc_n = await count_locations(session, clinic_id)
    nom_n = await count_nomenclature(session, clinic_id)
    return CommerceOverviewResponse(
        clinic_id=str(clinic_id),
        organization_id=str(org_id),
        stock_locations_count=loc_n,
        nomenclature_items_count=nom_n,
    )


class CommerceImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_profile: str
    status: str
    idempotency_key: str
    file_name: str | None
    created_at: datetime
    payload_summary: dict | None = None
    last_error: str | None = None


@router.get(
    "/{clinic_id}/commerce/import-jobs",
    response_model=list[CommerceImportJobRead],
)
async def list_commerce_import_jobs(
    clinic_id: UUID,
    limit: int = Query(default=30, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> list[CommerceImportJobRead]:
    """Audit trail of CSV imports for this clinic (4-F5)."""
    org_id = await _guard_clinic_org(clinic_id, current_admin, session)
    rows = await list_import_jobs_for_clinic(
        session,
        organization_id=org_id,
        clinic_id=clinic_id,
        limit=limit,
    )
    return [CommerceImportJobRead.model_validate(r) for r in rows]


class CommerceNomenclatureCreateBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    unit: str = Field(default="pcs", max_length=32)
    sku: str | None = Field(None, max_length=64)


class CommerceNomenclatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str | None
    name: str
    unit: str
    is_active: bool
    created_at: datetime


@router.get(
    "/{clinic_id}/commerce/nomenclature",
    response_model=list[CommerceNomenclatureRead],
)
async def list_commerce_nomenclature(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> list[CommerceNomenclatureRead]:
    await _guard_clinic_org(clinic_id, current_admin, session)
    rows = await list_nomenclature_items(session, clinic_id)
    return [CommerceNomenclatureRead.model_validate(r) for r in rows]


class CommerceNomenclatureImportSpecResponse(BaseModel):
    profile: str
    encoding: str = "utf-8"
    description: str
    required_columns: list[str]
    optional_columns: list[str]
    max_rows: int
    row_matching: str
    notes: list[str]
    example_csv: str


@router.get(
    "/{clinic_id}/commerce/nomenclature/import-spec",
    response_model=CommerceNomenclatureImportSpecResponse,
)
async def commerce_nomenclature_import_spec(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> CommerceNomenclatureImportSpecResponse:
    """Machine-readable contract for CSV / 1C-style nomenclature loads (4-F4)."""
    await _guard_clinic_org(clinic_id, current_admin, session)
    return CommerceNomenclatureImportSpecResponse(
        profile=COMMERCE_NOMENCLATURE_CSV_PROFILE,
        description="Импорт номенклатуры Commerce в рамках клиники; UTF-8, разделитель запятая.",
        required_columns=["name"],
        optional_columns=["sku", "unit", "is_active"],
        max_rows=COMMERCE_CSV_IMPORT_MAX_ROWS,
        row_matching="При непустом sku строка сопоставляется с существующей позицией клиники по sku (обновление); иначе создаётся новая позиция без sku.",
        notes=[
            "Колонки без учёта регистра; BOM UTF-8 допускается.",
            "is_active: пусто/true/1 — активна; false/0/no/нет — выключена.",
            "При обновлении существующей строки по sku: если колонки is_active нет, признак активности не меняется.",
            "Ограничения: name ≤ 255, sku ≤ 64, unit ≤ 32.",
            "Заголовок HTTP Idempotency-Key: повтор с тем же ключом возвращает тот же результат без повторной записи (тот же профиль и клиника).",
        ],
        example_csv="name,sku,unit,is_active\n\"Бинт стерильный\",ART-001,pcs,true\n\"Паста\",ART-002,kg,1\n",
    )


@router.post(
    "/{clinic_id}/commerce/nomenclature/import-csv",
    response_model=CommerceCsvImportResponse,
)
async def commerce_nomenclature_import_csv(
    request: Request,
    clinic_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> CommerceCsvImportResponse:
    if file.content_type not in ("text/csv", "application/vnd.ms-excel", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "commerce_import_invalid_content_type",
                "message": "Ожидается CSV (text/csv)",
            },
        )
    try:
        raw_bytes = await file.read()
        content = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "commerce_import_decode_error",
                "message": "Файл должен быть в кодировке UTF-8",
            },
        ) from exc

    fname = ((file.filename or "upload.csv").strip()[:255] or "upload.csv")
    org_id = await _guard_clinic_org(clinic_id, current_admin, session)
    idem_client, idem_stored = _idempotency_client_and_storage_key(request)

    try:
        replay = await try_replay_committed_import(
            session,
            org_id,
            idem_client,
            source_profile=COMMERCE_NOMENCLATURE_CSV_PROFILE,
            clinic_id=clinic_id,
            stock_location_id=None,
        )
    except CommerceImportJobError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "commerce_import_idempotency_scope_mismatch",
                "message": "Idempotency-Key уже использован для другого профиля или точки",
            },
        ) from None

    if replay is not None:
        return CommerceCsvImportResponse(
            profile=COMMERCE_NOMENCLATURE_CSV_PROFILE,
            created=replay.created,
            updated=replay.updated,
            skipped=replay.skipped,
            errors=replay.errors,
        )

    try:
        result = await import_nomenclature_csv(
            session,
            organization_id=org_id,
            clinic_id=clinic_id,
            content=content,
        )
        await upsert_import_job_record(
            session,
            organization_id=org_id,
            clinic_id=clinic_id,
            stock_location_id=None,
            source_profile=COMMERCE_NOMENCLATURE_CSV_PROFILE,
            idempotency_key_stored=idem_stored,
            file_name=fname,
            created_by_admin_id=current_admin.id,
            status=COMMERCE_IMPORT_STATUS_COMMITTED,
            payload_summary=build_commerce_import_payload_summary(
                source_profile=COMMERCE_NOMENCLATURE_CSV_PROFILE,
                file_name=fname,
                result=result,
            ),
            last_error=None,
        )
        await session.commit()
    except CommerceStoreError as e:
        await session.rollback()
        code = str(e)
        if code == "csv_no_header":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_import_csv_no_header", "message": "Пустой или некорректный CSV"},
            ) from None
        if code == "csv_no_name_column":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "commerce_import_csv_no_name",
                    "message": "Нужна колонка name в первой строке (заголовок)",
                },
            ) from None
        if code == "csv_too_many_rows":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "commerce_import_csv_too_many_rows",
                    "message": f"Не более {COMMERCE_CSV_IMPORT_MAX_ROWS} строк данных",
                },
            ) from None
        raise
    except IntegrityError:
        await session.rollback()
        replay_after = await _commerce_replay_after_integrity_rollback(
            session,
            organization_id=org_id,
            idem_client=idem_client,
            source_profile=COMMERCE_NOMENCLATURE_CSV_PROFILE,
            clinic_id=clinic_id,
            stock_location_id=None,
        )
        if replay_after is not None:
            return CommerceCsvImportResponse(
                profile=COMMERCE_NOMENCLATURE_CSV_PROFILE,
                created=replay_after.created,
                updated=replay_after.updated,
                skipped=replay_after.skipped,
                errors=replay_after.errors,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "commerce_nomenclature_sku_conflict", "message": "Конфликт SKU при импорте"},
        ) from None

    return CommerceCsvImportResponse(
        profile=COMMERCE_NOMENCLATURE_CSV_PROFILE,
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
    )


class CommerceNomenclaturePatchBody(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    sku: str | None = None
    is_active: bool | None = None


@router.patch(
    "/{clinic_id}/commerce/nomenclature/{item_id}",
    response_model=CommerceNomenclatureRead,
)
async def patch_commerce_nomenclature(
    clinic_id: UUID,
    item_id: UUID,
    body: CommerceNomenclaturePatchBody,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> CommerceNomenclatureRead:
    await _guard_clinic_org(clinic_id, current_admin, session)
    row = await get_nomenclature_item(session, item_id, clinic_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "commerce_nomenclature_not_found", "message": "Позиция не найдена"},
        )
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return CommerceNomenclatureRead.model_validate(row)
    try:
        await apply_nomenclature_patch(session, row, patch)
        await session.commit()
        await session.refresh(row)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "commerce_nomenclature_sku_conflict", "message": "SKU уже занят для этой клиники"},
        ) from None
    return CommerceNomenclatureRead.model_validate(row)


@router.delete(
    "/{clinic_id}/commerce/nomenclature/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_commerce_nomenclature(
    clinic_id: UUID,
    item_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> None:
    await _guard_clinic_org(clinic_id, current_admin, session)
    ok = await delete_nomenclature_item(session, item_id, clinic_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "commerce_nomenclature_not_found", "message": "Позиция не найдена"},
        )
    await session.commit()


@router.post(
    "/{clinic_id}/commerce/nomenclature",
    response_model=CommerceNomenclatureRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_commerce_nomenclature(
    clinic_id: UUID,
    body: CommerceNomenclatureCreateBody,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> CommerceNomenclatureRead:
    org_id = await _guard_clinic_org(clinic_id, current_admin, session)
    try:
        row = await create_nomenclature_item(
            session,
            organization_id=org_id,
            clinic_id=clinic_id,
            name=body.name,
            unit=body.unit,
            sku=body.sku,
        )
        await session.commit()
        await session.refresh(row)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "commerce_nomenclature_sku_conflict", "message": "SKU уже занят для этой клиники"},
        ) from None
    return CommerceNomenclatureRead.model_validate(row)


class CommerceMovementDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stock_location_id: UUID
    to_stock_location_id: UUID | None = None
    doc_kind: str
    remark: str | None
    created_at: datetime


class CommerceMovementLineRead(BaseModel):
    nomenclature_item_id: UUID
    sku: str | None
    name: str
    unit: str
    quantity: Decimal


def _line_detail_to_read(d: CommerceDocumentLineDetail) -> CommerceMovementLineRead:
    return CommerceMovementLineRead(
        nomenclature_item_id=d.nomenclature_item_id,
        sku=d.sku,
        name=d.name,
        unit=d.unit,
        quantity=d.quantity,
    )


class CommerceMovementDocumentDetailRead(BaseModel):
    id: UUID
    stock_location_id: UUID
    to_stock_location_id: UUID | None = None
    doc_kind: str
    remark: str | None
    created_at: datetime
    lines: list[CommerceMovementLineRead]


@router.get(
    "/{clinic_id}/commerce/movements",
    response_model=list[CommerceMovementDocumentRead],
)
async def list_commerce_movements(
    clinic_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> list[CommerceMovementDocumentRead]:
    await _guard_clinic_org(clinic_id, current_admin, session)
    rows = await list_movement_documents(session, clinic_id)
    return [CommerceMovementDocumentRead.model_validate(r) for r in rows]


@router.get(
    "/{clinic_id}/commerce/movements/{document_id}",
    response_model=CommerceMovementDocumentDetailRead,
)
async def get_commerce_movement(
    clinic_id: UUID,
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("view_inventory")),
) -> CommerceMovementDocumentDetailRead:
    await _guard_clinic_org(clinic_id, current_admin, session)
    doc = await get_movement_document(session, document_id, clinic_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "commerce_document_not_found", "message": "Документ не найден"},
        )
    details = await list_document_line_details(session, document_id, clinic_id)
    return CommerceMovementDocumentDetailRead(
        id=doc.id,
        stock_location_id=doc.stock_location_id,
        to_stock_location_id=doc.to_stock_location_id,
        doc_kind=doc.doc_kind,
        remark=doc.remark,
        created_at=doc.created_at,
        lines=[_line_detail_to_read(x) for x in details],
    )


class CommerceMovementLineIn(BaseModel):
    nomenclature_item_id: UUID
    quantity: Decimal = Field(..., gt=0)


class CommerceMovementPostBody(BaseModel):
    stock_location_id: UUID
    to_stock_location_id: UUID | None = None
    doc_kind: Literal["goods_in", "goods_out", "goods_transfer"]
    remark: str | None = None
    lines: list[CommerceMovementLineIn] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _transfer_location_rules(self) -> CommerceMovementPostBody:
        if self.doc_kind == "goods_transfer":
            if self.to_stock_location_id is None:
                raise ValueError("to_stock_location_id required for goods_transfer")
            if self.to_stock_location_id == self.stock_location_id:
                raise ValueError("from and to stock locations must differ")
        elif self.to_stock_location_id is not None:
            raise ValueError("to_stock_location_id only for goods_transfer")
        return self


@router.post(
    "/{clinic_id}/commerce/movements",
    response_model=CommerceMovementDocumentDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_commerce_movement(
    clinic_id: UUID,
    body: CommerceMovementPostBody,
    session: AsyncSession = Depends(get_session),
    current_admin: AdminUser = Depends(get_current_admin),
    _: AdminContext = Depends(require_permissions("manage_inventory")),
) -> CommerceMovementDocumentDetailRead:
    org_id = await _guard_clinic_org(clinic_id, current_admin, session)
    tuples = [(ln.nomenclature_item_id, ln.quantity) for ln in body.lines]
    try:
        doc = await post_movement_document(
            session,
            organization_id=org_id,
            clinic_id=clinic_id,
            stock_location_id=body.stock_location_id,
            doc_kind=body.doc_kind,
            remark=body.remark,
            lines=tuples,
            to_stock_location_id=body.to_stock_location_id,
        )
        await session.commit()
        await session.refresh(doc)
    except CommerceStoreError as e:
        await session.rollback()
        code = str(e)
        if code == "invalid_doc_kind":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_invalid_doc_kind", "message": "Некорректный тип документа"},
            ) from None
        if code == "lines_required":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_lines_required", "message": "Нужна хотя бы одна строка"},
            ) from None
        if code == "line_quantity_invalid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_line_qty_invalid", "message": "Количество в строке должно быть > 0"},
            ) from None
        if code == "insufficient_stock":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "commerce_insufficient_stock", "message": "Недостаточно остатка для расхода"},
            ) from None
        if code == "stock_location_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "commerce_stock_location_not_found", "message": "Точка не найдена"},
            ) from None
        if code == "nomenclature_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "commerce_nomenclature_not_found", "message": "Позиция не найдена"},
            ) from None
        if code == "transfer_to_required":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_transfer_to_required", "message": "Укажите точку назначения для перемещения"},
            ) from None
        if code == "transfer_same_location":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_transfer_same_location", "message": "Исходная и целевая точки должны различаться"},
            ) from None
        if code == "transfer_destination_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "commerce_transfer_destination_not_found", "message": "Точка назначения не найдена"},
            ) from None
        if code == "transfer_to_unexpected":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "commerce_transfer_to_unexpected", "message": "to_stock_location_id только для перемещения"},
            ) from None
        raise
    details = await list_document_line_details(session, doc.id, clinic_id)
    return CommerceMovementDocumentDetailRead(
        id=doc.id,
        stock_location_id=doc.stock_location_id,
        to_stock_location_id=doc.to_stock_location_id,
        doc_kind=doc.doc_kind,
        remark=doc.remark,
        created_at=doc.created_at,
        lines=[_line_detail_to_read(x) for x in details],
    )
