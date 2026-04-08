"""Commerce store bounded context — minimal read/write (Phase 4, ADR-013)."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from sqlalchemy import cast, func, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric

from src.domain.entities.clinic import Clinic
from src.domain.entities.commerce_document import CommerceDocument
from src.domain.entities.commerce_document_line import CommerceDocumentLine
from src.domain.entities.commerce_nomenclature_item import CommerceNomenclatureItem
from src.domain.entities.commerce_stock_balance import CommerceStockBalance
from src.domain.entities.commerce_stock_location import CommerceStockLocation

DOC_KIND_GOODS_IN = "goods_in"
DOC_KIND_GOODS_OUT = "goods_out"
DOC_KIND_GOODS_TRANSFER = "goods_transfer"

COMMERCE_NOMENCLATURE_CSV_PROFILE = "commerce_nomenclature_csv_v1"
COMMERCE_STOCK_BALANCES_CSV_PROFILE = "commerce_stock_balances_csv_v1"
COMMERCE_CSV_IMPORT_MAX_ROWS = 2000
COMMERCE_NOMENCLATURE_IMPORT_MAX_ROWS = COMMERCE_CSV_IMPORT_MAX_ROWS
_MAX_CSV_IMPORT_ERROR_LINES = 50


class CommerceBalanceLine(NamedTuple):
    balance_id: uuid.UUID | None
    nomenclature_item_id: uuid.UUID
    sku: str | None
    name: str
    unit: str
    quantity: Decimal


class CommerceNetworkClinicRollup(NamedTuple):
    """Read-model row: commerce aggregates per clinic in an organization (4-F3)."""

    clinic_id: uuid.UUID
    clinic_name: str
    stock_locations_count: int
    nomenclature_items_count: int
    total_on_hand_quantity: Decimal


class CommerceNetworkOverviewResult(NamedTuple):
    organization_id: uuid.UUID
    clinics: list[CommerceNetworkClinicRollup]
    stock_locations_total: int
    nomenclature_items_total: int
    total_on_hand_quantity: Decimal


class CommerceCsvImportResult(NamedTuple):
    """Outcome of commerce CSV imports (4-F4); partial apply with per-row errors."""

    created: int
    updated: int
    skipped: int
    errors: list[str]


CommerceNomenclatureImportResult = CommerceCsvImportResult


class CommerceStoreError(Exception):
    """Domain error for commerce operations."""


async def resolve_org_for_clinic(session: AsyncSession, clinic_id: uuid.UUID) -> uuid.UUID:
    res = await session.execute(select(Clinic.organization_id).where(Clinic.id == clinic_id).limit(1))
    org_id = res.scalar_one_or_none()
    if org_id is None:
        raise CommerceStoreError("clinic_not_found")
    return org_id


async def count_locations(session: AsyncSession, clinic_id: uuid.UUID) -> int:
    res = await session.execute(
        select(func.count()).select_from(CommerceStockLocation).where(CommerceStockLocation.clinic_id == clinic_id)
    )
    return int(res.scalar_one())


async def count_nomenclature(session: AsyncSession, clinic_id: uuid.UUID) -> int:
    res = await session.execute(
        select(func.count())
        .select_from(CommerceNomenclatureItem)
        .where(CommerceNomenclatureItem.clinic_id == clinic_id)
    )
    return int(res.scalar_one())


async def get_commerce_network_overview(
    session: AsyncSession,
    organization_id: uuid.UUID,
) -> CommerceNetworkOverviewResult:
    """Aggregate stock locations, nomenclature counts, and on-hand qty per clinic (org-wide read model)."""
    loc_sq = (
        select(
            CommerceStockLocation.clinic_id.label("clinic_id"),
            func.count().label("loc_count"),
        )
        .group_by(CommerceStockLocation.clinic_id)
        .subquery()
    )
    nom_sq = (
        select(
            CommerceNomenclatureItem.clinic_id.label("clinic_id"),
            func.count().label("nom_count"),
        )
        .group_by(CommerceNomenclatureItem.clinic_id)
        .subquery()
    )
    bal_sq = (
        select(
            CommerceStockBalance.clinic_id.label("clinic_id"),
            func.sum(CommerceStockBalance.quantity).label("qty_sum"),
        )
        .group_by(CommerceStockBalance.clinic_id)
        .subquery()
    )
    lc = loc_sq.c.loc_count
    nn = nom_sq.c.nom_count
    qq = bal_sq.c.qty_sum
    zero_qty = cast(literal(0), Numeric(14, 4))
    stmt = (
        select(
            Clinic.id,
            Clinic.name,
            func.coalesce(lc, 0).label("locs"),
            func.coalesce(nn, 0).label("noms"),
            func.coalesce(qq, zero_qty).label("qty"),
        )
        .select_from(Clinic)
        .outerjoin(loc_sq, loc_sq.c.clinic_id == Clinic.id)
        .outerjoin(nom_sq, nom_sq.c.clinic_id == Clinic.id)
        .outerjoin(bal_sq, bal_sq.c.clinic_id == Clinic.id)
        .where(Clinic.organization_id == organization_id)
        .order_by(Clinic.name)
    )
    res = await session.execute(stmt)
    clinics: list[CommerceNetworkClinicRollup] = []
    tot_locs = 0
    tot_noms = 0
    tot_qty = Decimal(0)
    for row in res.mappings().all():
        loc_n = int(row["locs"])
        nom_n = int(row["noms"])
        q = Decimal(str(row["qty"]))
        clinics.append(
            CommerceNetworkClinicRollup(
                clinic_id=row["id"],
                clinic_name=row["name"],
                stock_locations_count=loc_n,
                nomenclature_items_count=nom_n,
                total_on_hand_quantity=q,
            )
        )
        tot_locs += loc_n
        tot_noms += nom_n
        tot_qty += q
    return CommerceNetworkOverviewResult(
        organization_id=organization_id,
        clinics=clinics,
        stock_locations_total=tot_locs,
        nomenclature_items_total=tot_noms,
        total_on_hand_quantity=tot_qty,
    )


async def create_nomenclature_item(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    clinic_id: uuid.UUID,
    name: str,
    unit: str,
    sku: str | None,
) -> CommerceNomenclatureItem:
    row = CommerceNomenclatureItem(
        organization_id=organization_id,
        clinic_id=clinic_id,
        name=name.strip(),
        unit=unit.strip() or "pcs",
        sku=sku.strip() if sku else None,
    )
    session.add(row)
    await session.flush()
    return row


async def list_nomenclature_items(
    session: AsyncSession,
    clinic_id: uuid.UUID,
) -> list[CommerceNomenclatureItem]:
    res = await session.execute(
        select(CommerceNomenclatureItem)
        .where(CommerceNomenclatureItem.clinic_id == clinic_id)
        .order_by(CommerceNomenclatureItem.created_at.desc())
    )
    return list(res.scalars().all())


async def get_nomenclature_item(
    session: AsyncSession,
    item_id: uuid.UUID,
    clinic_id: uuid.UUID,
) -> CommerceNomenclatureItem | None:
    res = await session.execute(
        select(CommerceNomenclatureItem).where(
            CommerceNomenclatureItem.id == item_id,
            CommerceNomenclatureItem.clinic_id == clinic_id,
        )
    )
    return res.scalar_one_or_none()


async def get_nomenclature_item_by_sku(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    sku: str,
) -> CommerceNomenclatureItem | None:
    key = sku.strip()
    if not key:
        return None
    res = await session.execute(
        select(CommerceNomenclatureItem).where(
            CommerceNomenclatureItem.clinic_id == clinic_id,
            CommerceNomenclatureItem.sku == key,
        )
    )
    return res.scalar_one_or_none()


def _parse_csv_bool_active(raw: str) -> bool:
    s = (raw or "").strip().lower()
    if not s:
        return True
    if s in ("0", "false", "no", "n", "нет", "off"):
        return False
    return True


def _normalize_csv_row_keys(row: dict[str, str | None]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in row.items():
        nk = (k or "").strip().lower().lstrip("\ufeff")
        if isinstance(v, str):
            out[nk] = v.strip()
        elif v is None:
            out[nk] = ""
        else:
            out[nk] = str(v).strip()
    return out


async def import_nomenclature_csv(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    clinic_id: uuid.UUID,
    content: str,
    max_rows: int | None = None,
) -> CommerceCsvImportResult:
    """Upsert nomenclature from CSV (UTF-8). Column name required; sku matches existing rows per clinic."""
    limit = max_rows if max_rows is not None else COMMERCE_CSV_IMPORT_MAX_ROWS
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise CommerceStoreError("csv_no_header")
    fields_lower = {(f or "").strip().lower().lstrip("\ufeff") for f in reader.fieldnames}
    if "name" not in fields_lower:
        raise CommerceStoreError("csv_no_name_column")

    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for idx, raw in enumerate(reader, start=2):
        if idx - 2 >= limit:
            raise CommerceStoreError("csv_too_many_rows")
        row = _normalize_csv_row_keys(raw)
        name = (row.get("name") or "").strip()
        if not name:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: пустое поле name")
            continue
        if len(name) > 255:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: name длиннее 255 символов")
            continue

        sku_raw = (row.get("sku") or "").strip() or None
        if sku_raw and len(sku_raw) > 64:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: sku длиннее 64 символов")
            continue

        unit = (row.get("unit") or "pcs").strip() or "pcs"
        if len(unit) > 32:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: unit длиннее 32 символов")
            continue

        has_active_col = "is_active" in row
        is_active = _parse_csv_bool_active(row["is_active"]) if has_active_col else True

        if sku_raw:
            existing = await get_nomenclature_item_by_sku(session, clinic_id, sku_raw)
            if existing is not None:
                patch: dict = {"name": name, "unit": unit}
                if has_active_col:
                    patch["is_active"] = is_active
                await apply_nomenclature_patch(session, existing, patch)
                updated += 1
            else:
                new_row = await create_nomenclature_item(
                    session,
                    organization_id=organization_id,
                    clinic_id=clinic_id,
                    name=name,
                    unit=unit,
                    sku=sku_raw,
                )
                if has_active_col and not is_active:
                    await apply_nomenclature_patch(session, new_row, {"is_active": False})
                created += 1
        else:
            new_row = await create_nomenclature_item(
                session,
                organization_id=organization_id,
                clinic_id=clinic_id,
                name=name,
                unit=unit,
                sku=None,
            )
            if has_active_col and not is_active:
                await apply_nomenclature_patch(session, new_row, {"is_active": False})
            created += 1

    return CommerceCsvImportResult(
        created=created,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )


async def import_stock_balances_csv(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    clinic_id: uuid.UUID,
    location_id: uuid.UUID,
    content: str,
    max_rows: int | None = None,
) -> CommerceCsvImportResult:
    """Set on-hand quantity per nomenclature row at one stock location; match by sku within clinic."""
    limit = max_rows if max_rows is not None else COMMERCE_CSV_IMPORT_MAX_ROWS
    if await get_stock_location(session, location_id, clinic_id) is None:
        raise CommerceStoreError("stock_location_not_found")

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise CommerceStoreError("csv_no_header")
    fields_lower = {(f or "").strip().lower().lstrip("\ufeff") for f in reader.fieldnames}
    if "sku" not in fields_lower or "quantity" not in fields_lower:
        raise CommerceStoreError("csv_balance_columns")

    created = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for idx, raw in enumerate(reader, start=2):
        if idx - 2 >= limit:
            raise CommerceStoreError("csv_too_many_rows")
        row = _normalize_csv_row_keys(raw)
        sku_raw = (row.get("sku") or "").strip()
        if not sku_raw:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: пустой sku")
            continue
        if len(sku_raw) > 64:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: sku длиннее 64 символов")
            continue

        qty_s = (row.get("quantity") or "").strip().replace(",", ".")
        if not qty_s:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: пустое quantity")
            continue
        try:
            quantity = Decimal(qty_s)
        except InvalidOperation:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: некорректное quantity")
            continue
        if quantity < 0:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: quantity не может быть отрицательным")
            continue

        item = await get_nomenclature_item_by_sku(session, clinic_id, sku_raw)
        if item is None:
            skipped += 1
            if len(errors) < _MAX_CSV_IMPORT_ERROR_LINES:
                errors.append(f"Строка {idx}: номенклатура с sku «{sku_raw}» не найдена")
            continue

        had = (
            await session.execute(
                select(CommerceStockBalance.id)
                .where(
                    CommerceStockBalance.stock_location_id == location_id,
                    CommerceStockBalance.nomenclature_item_id == item.id,
                    CommerceStockBalance.clinic_id == clinic_id,
                )
                .limit(1)
            )
        ).scalar_one_or_none() is not None

        await upsert_stock_balance(
            session,
            organization_id=organization_id,
            clinic_id=clinic_id,
            location_id=location_id,
            item_id=item.id,
            quantity=quantity,
        )
        if had:
            updated += 1
        else:
            created += 1

    return CommerceCsvImportResult(
        created=created,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )


async def apply_nomenclature_patch(
    session: AsyncSession,
    row: CommerceNomenclatureItem,
    data: dict,
) -> CommerceNomenclatureItem:
    if "name" in data:
        row.name = str(data["name"]).strip()
    if "unit" in data:
        row.unit = str(data["unit"]).strip() or "pcs"
    if "sku" in data:
        s = data["sku"]
        row.sku = s.strip() if isinstance(s, str) and s.strip() else None
    if "is_active" in data:
        row.is_active = bool(data["is_active"])
    await session.flush()
    return row


async def delete_nomenclature_item(
    session: AsyncSession,
    item_id: uuid.UUID,
    clinic_id: uuid.UUID,
) -> bool:
    row = await get_nomenclature_item(session, item_id, clinic_id)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def _unset_default_for_clinic(session: AsyncSession, clinic_id: uuid.UUID) -> None:
    await session.execute(
        update(CommerceStockLocation)
        .where(CommerceStockLocation.clinic_id == clinic_id)
        .values(is_default=False)
    )


async def list_stock_locations(
    session: AsyncSession,
    clinic_id: uuid.UUID,
) -> list[CommerceStockLocation]:
    res = await session.execute(
        select(CommerceStockLocation)
        .where(CommerceStockLocation.clinic_id == clinic_id)
        .order_by(CommerceStockLocation.is_default.desc(), CommerceStockLocation.created_at)
    )
    return list(res.scalars().all())


async def get_stock_location(
    session: AsyncSession,
    location_id: uuid.UUID,
    clinic_id: uuid.UUID,
) -> CommerceStockLocation | None:
    res = await session.execute(
        select(CommerceStockLocation).where(
            CommerceStockLocation.id == location_id,
            CommerceStockLocation.clinic_id == clinic_id,
        )
    )
    return res.scalar_one_or_none()


async def create_stock_location(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    clinic_id: uuid.UUID,
    name: str,
    code: str | None,
    is_default: bool,
) -> CommerceStockLocation:
    if is_default:
        await _unset_default_for_clinic(session, clinic_id)
    row = CommerceStockLocation(
        organization_id=organization_id,
        clinic_id=clinic_id,
        name=name.strip(),
        code=code.strip() if code else None,
        is_default=is_default,
    )
    session.add(row)
    await session.flush()
    return row


async def apply_stock_location_patch(
    session: AsyncSession,
    row: CommerceStockLocation,
    data: dict,
) -> CommerceStockLocation:
    """Apply partial update; keys only from model_dump(exclude_unset=True)."""
    if "name" in data:
        row.name = str(data["name"]).strip()
    if "code" in data:
        c = data["code"]
        row.code = c.strip() if isinstance(c, str) and c.strip() else None
    if "is_default" in data:
        if data["is_default"] is True:
            await _unset_default_for_clinic(session, row.clinic_id)
        row.is_default = bool(data["is_default"])
    await session.flush()
    return row


async def delete_stock_location(
    session: AsyncSession,
    location_id: uuid.UUID,
    clinic_id: uuid.UUID,
) -> bool:
    row = await get_stock_location(session, location_id, clinic_id)
    if row is None:
        return False
    await session.delete(row)
    await session.flush()
    return True


async def create_default_stock_location(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    clinic_id: uuid.UUID,
    name: str = "Основная точка",
) -> CommerceStockLocation:
    return await create_stock_location(
        session,
        organization_id=organization_id,
        clinic_id=clinic_id,
        name=name,
        code=None,
        is_default=True,
    )


_zero_qty = cast(literal(0), Numeric(14, 4))


async def list_balance_lines_for_location(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    location_id: uuid.UUID,
) -> list[CommerceBalanceLine]:
    qty = func.coalesce(CommerceStockBalance.quantity, _zero_qty).label("quantity")
    stmt = (
        select(
            CommerceStockBalance.id.label("balance_id"),
            CommerceNomenclatureItem.id.label("nomenclature_item_id"),
            CommerceNomenclatureItem.sku,
            CommerceNomenclatureItem.name,
            CommerceNomenclatureItem.unit,
            qty,
        )
        .select_from(CommerceNomenclatureItem)
        .outerjoin(
            CommerceStockBalance,
            (CommerceStockBalance.nomenclature_item_id == CommerceNomenclatureItem.id)
            & (CommerceStockBalance.stock_location_id == location_id)
            & (CommerceStockBalance.clinic_id == clinic_id),
        )
        .where(CommerceNomenclatureItem.clinic_id == clinic_id)
        .order_by(CommerceNomenclatureItem.name)
    )
    res = await session.execute(stmt)
    out: list[CommerceBalanceLine] = []
    for m in res.mappings().all():
        bid = m["balance_id"]
        out.append(
            CommerceBalanceLine(
                balance_id=bid,
                nomenclature_item_id=m["nomenclature_item_id"],
                sku=m["sku"],
                name=m["name"],
                unit=m["unit"],
                quantity=Decimal(str(m["quantity"])),
            )
        )
    return out


async def upsert_stock_balance(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    clinic_id: uuid.UUID,
    location_id: uuid.UUID,
    item_id: uuid.UUID,
    quantity: Decimal,
) -> CommerceStockBalance:
    if quantity < 0:
        raise CommerceStoreError("quantity_negative")
    loc = await get_stock_location(session, location_id, clinic_id)
    if loc is None:
        raise CommerceStoreError("stock_location_not_found")
    item = await get_nomenclature_item(session, item_id, clinic_id)
    if item is None:
        raise CommerceStoreError("nomenclature_not_found")
    res = await session.execute(
        select(CommerceStockBalance).where(
            CommerceStockBalance.stock_location_id == location_id,
            CommerceStockBalance.nomenclature_item_id == item_id,
            CommerceStockBalance.clinic_id == clinic_id,
        )
    )
    row = res.scalar_one_or_none()
    now = datetime.now(UTC)
    if row is None:
        row = CommerceStockBalance(
            organization_id=organization_id,
            clinic_id=clinic_id,
            stock_location_id=location_id,
            nomenclature_item_id=item_id,
            quantity=quantity,
            updated_at=now,
        )
        session.add(row)
    else:
        row.quantity = quantity
        row.updated_at = now
    await session.flush()
    await session.refresh(row)
    return row


async def apply_balance_delta(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    clinic_id: uuid.UUID,
    location_id: uuid.UUID,
    item_id: uuid.UUID,
    delta: Decimal,
) -> None:
    """Adjust stock balance by delta; negative result raises insufficient_stock."""
    if delta == 0:
        return
    res = await session.execute(
        select(CommerceStockBalance).where(
            CommerceStockBalance.stock_location_id == location_id,
            CommerceStockBalance.nomenclature_item_id == item_id,
            CommerceStockBalance.clinic_id == clinic_id,
        )
    )
    row = res.scalar_one_or_none()
    now = datetime.now(UTC)
    current = row.quantity if row else Decimal(0)
    new_qty = current + delta
    if new_qty < 0:
        raise CommerceStoreError("insufficient_stock")
    if row is None:
        if new_qty > 0:
            session.add(
                CommerceStockBalance(
                    organization_id=organization_id,
                    clinic_id=clinic_id,
                    stock_location_id=location_id,
                    nomenclature_item_id=item_id,
                    quantity=new_qty,
                    updated_at=now,
                )
            )
    else:
        row.quantity = new_qty
        row.updated_at = now
    await session.flush()


async def list_movement_documents(
    session: AsyncSession,
    clinic_id: uuid.UUID,
    *,
    limit: int = 50,
) -> list[CommerceDocument]:
    res = await session.execute(
        select(CommerceDocument)
        .where(CommerceDocument.clinic_id == clinic_id)
        .order_by(CommerceDocument.created_at.desc())
        .limit(limit)
    )
    return list(res.scalars().all())


async def get_movement_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    clinic_id: uuid.UUID,
) -> CommerceDocument | None:
    res = await session.execute(
        select(CommerceDocument).where(
            CommerceDocument.id == document_id,
            CommerceDocument.clinic_id == clinic_id,
        )
    )
    return res.scalar_one_or_none()


class CommerceDocumentLineDetail(NamedTuple):
    line_id: uuid.UUID
    nomenclature_item_id: uuid.UUID
    sku: str | None
    name: str
    unit: str
    quantity: Decimal


async def list_document_line_details(
    session: AsyncSession,
    document_id: uuid.UUID,
    clinic_id: uuid.UUID,
) -> list[CommerceDocumentLineDetail]:
    stmt = (
        select(
            CommerceDocumentLine.id.label("line_id"),
            CommerceNomenclatureItem.id.label("nomenclature_item_id"),
            CommerceNomenclatureItem.sku,
            CommerceNomenclatureItem.name,
            CommerceNomenclatureItem.unit,
            CommerceDocumentLine.quantity,
        )
        .select_from(CommerceDocumentLine)
        .join(
            CommerceNomenclatureItem,
            CommerceNomenclatureItem.id == CommerceDocumentLine.nomenclature_item_id,
        )
        .where(
            CommerceDocumentLine.document_id == document_id,
            CommerceDocumentLine.clinic_id == clinic_id,
        )
        .order_by(CommerceNomenclatureItem.name)
    )
    res = await session.execute(stmt)
    return [
        CommerceDocumentLineDetail(
            line_id=m["line_id"],
            nomenclature_item_id=m["nomenclature_item_id"],
            sku=m["sku"],
            name=m["name"],
            unit=m["unit"],
            quantity=Decimal(str(m["quantity"])),
        )
        for m in res.mappings().all()
    ]


async def post_movement_document(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    clinic_id: uuid.UUID,
    stock_location_id: uuid.UUID,
    doc_kind: str,
    remark: str | None,
    lines: list[tuple[uuid.UUID, Decimal]],
    to_stock_location_id: uuid.UUID | None = None,
) -> CommerceDocument:
    if doc_kind not in (DOC_KIND_GOODS_IN, DOC_KIND_GOODS_OUT, DOC_KIND_GOODS_TRANSFER):
        raise CommerceStoreError("invalid_doc_kind")
    if not lines:
        raise CommerceStoreError("lines_required")

    if doc_kind == DOC_KIND_GOODS_TRANSFER:
        if to_stock_location_id is None:
            raise CommerceStoreError("transfer_to_required")
        if to_stock_location_id == stock_location_id:
            raise CommerceStoreError("transfer_same_location")
        if await get_stock_location(session, stock_location_id, clinic_id) is None:
            raise CommerceStoreError("stock_location_not_found")
        if await get_stock_location(session, to_stock_location_id, clinic_id) is None:
            raise CommerceStoreError("transfer_destination_not_found")
    elif to_stock_location_id is not None:
        raise CommerceStoreError("transfer_to_unexpected")
    else:
        loc = await get_stock_location(session, stock_location_id, clinic_id)
        if loc is None:
            raise CommerceStoreError("stock_location_not_found")

    merged: dict[uuid.UUID, Decimal] = {}
    for item_id, qty in lines:
        if qty <= 0:
            raise CommerceStoreError("line_quantity_invalid")
        merged[item_id] = merged.get(item_id, Decimal(0)) + qty

    for item_id in merged:
        if await get_nomenclature_item(session, item_id, clinic_id) is None:
            raise CommerceStoreError("nomenclature_not_found")

    doc = CommerceDocument(
        organization_id=organization_id,
        clinic_id=clinic_id,
        stock_location_id=stock_location_id,
        to_stock_location_id=to_stock_location_id if doc_kind == DOC_KIND_GOODS_TRANSFER else None,
        doc_kind=doc_kind,
        remark=remark.strip() if remark and remark.strip() else None,
    )
    session.add(doc)
    await session.flush()

    for item_id, qty in merged.items():
        session.add(
            CommerceDocumentLine(
                organization_id=organization_id,
                clinic_id=clinic_id,
                document_id=doc.id,
                nomenclature_item_id=item_id,
                quantity=qty,
            )
        )
    await session.flush()

    if doc_kind == DOC_KIND_GOODS_TRANSFER:
        to_loc = to_stock_location_id
        if to_loc is None:
            raise CommerceStoreError("transfer_to_required")
        for item_id, qty in merged.items():
            await apply_balance_delta(
                session,
                organization_id=organization_id,
                clinic_id=clinic_id,
                location_id=stock_location_id,
                item_id=item_id,
                delta=-qty,
            )
            await apply_balance_delta(
                session,
                organization_id=organization_id,
                clinic_id=clinic_id,
                location_id=to_loc,
                item_id=item_id,
                delta=qty,
            )
    else:
        sign = Decimal(1) if doc_kind == DOC_KIND_GOODS_IN else Decimal(-1)
        for item_id, qty in merged.items():
            await apply_balance_delta(
                session,
                organization_id=organization_id,
                clinic_id=clinic_id,
                location_id=stock_location_id,
                item_id=item_id,
                delta=sign * qty,
            )

    await session.refresh(doc)
    return doc
