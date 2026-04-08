"""Phase 4 Commerce: entitlement commerce.store_network, overview + nomenclature stub."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, select, update

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic
from src.domain.entities.commerce_document import CommerceDocument
from src.domain.entities.commerce_import_job import CommerceImportJob
from src.domain.entities.commerce_nomenclature_item import CommerceNomenclatureItem
from src.domain.entities.commerce_stock_balance import CommerceStockBalance
from src.domain.entities.commerce_stock_location import CommerceStockLocation
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement


@pytest.fixture(autouse=True)
async def _restore_seed_admin_after_commerce_case(db_session, seed_data):
    """Revert org binding after SaaS-style commerce tests."""
    yield
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one_or_none()
    if admin is None:
        return
    oid = admin.organization_id
    admin.organization_id = None
    if oid is not None:
        await db_session.execute(delete(CommerceImportJob).where(CommerceImportJob.organization_id == oid))
        await db_session.execute(delete(CommerceDocument).where(CommerceDocument.organization_id == oid))
        await db_session.execute(
            delete(CommerceStockBalance).where(CommerceStockBalance.organization_id == oid)
        )
        await db_session.execute(
            delete(CommerceNomenclatureItem).where(
                CommerceNomenclatureItem.organization_id == oid
            )
        )
        await db_session.execute(
            delete(CommerceStockLocation).where(CommerceStockLocation.organization_id == oid)
        )
        await db_session.execute(update(Clinic).where(Clinic.organization_id == oid).values(organization_id=None))
        await db_session.execute(
            delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == oid)
        )
        await db_session.execute(delete(Organization).where(Organization.id == oid))
    await db_session.commit()


def _http_error_code(payload: dict) -> str | None:
    d = payload.get("detail")
    if isinstance(d, dict):
        c = d.get("code")
        if c is not None:
            return str(c).lower()
    c = payload.get("code")
    return str(c).lower() if c is not None else None


async def _bind_seed_clinic_to_org(db_session, seed_data: dict) -> uuid.UUID:
    org_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Commerce test org"))
    await db_session.flush()
    res = await db_session.execute(
        select(AdminUser).where(AdminUser.email == seed_data["admin_email"]).limit(1)
    )
    admin = res.scalar_one()
    cres = await db_session.execute(select(Clinic).where(Clinic.id == admin.clinic_id).limit(1))
    clinic = cres.scalar_one()
    clinic.organization_id = org_id
    admin.organization_id = org_id
    await db_session.commit()
    return org_id


@pytest.mark.asyncio
async def test_commerce_overview_403_without_store_entitlement(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = await _bind_seed_clinic_to_org(db_session, seed_data)
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="test",
        )
    )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/clinics/{seed_data['clinic_id']}/commerce/overview",
        headers=headers,
    )
    assert r.status_code == 403, r.text
    assert _http_error_code(r.json()) == "entitlement_required"


@pytest.mark.asyncio
async def test_commerce_overview_200_with_entitlement(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = await _bind_seed_clinic_to_org(db_session, seed_data)
    for key in ("core.base", "commerce.store_network"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    r = await client.get(
        f"/api/v1/admin/clinics/{seed_data['clinic_id']}/commerce/overview",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["stock_locations_count"] == 0
    assert data["nomenclature_items_count"] == 0
    assert data["clinic_id"] == str(seed_data["clinic_id"])


@pytest.mark.asyncio
async def test_commerce_overview_404_when_path_clinic_not_admin_clinic(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    """ADR-013: админский контур Commerce привязан к «домашней» клинике в пути; чужой UUID → 404."""
    org_id = await _bind_seed_clinic_to_org(db_session, seed_data)
    for key in ("core.base", "commerce.store_network"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    foreign = str(uuid.uuid4())
    r = await client.get(f"/api/v1/admin/clinics/{foreign}/commerce/overview", headers=headers)
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_commerce_create_nomenclature(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = await _bind_seed_clinic_to_org(db_session, seed_data)
    for key in ("core.base", "commerce.store_network"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cid = str(seed_data["clinic_id"])
    r = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=headers,
        json={"name": "Тестовая позиция", "unit": "pcs", "sku": "SKU-COMM-1"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["sku"] == "SKU-COMM-1"

    r2 = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/overview", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["nomenclature_items_count"] == 1


@pytest.mark.asyncio
async def test_commerce_sku_conflict_409(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = await _bind_seed_clinic_to_org(db_session, seed_data)
    for key in ("core.base", "commerce.store_network"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()

    headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}
    cid = str(seed_data["clinic_id"])
    body = {"name": "A", "sku": "DUP-SKU"}
    assert (await client.post(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature", headers=headers, json=body)).status_code == 201
    r = await client.post(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature", headers=headers, json=body)
    assert r.status_code == 409
    assert _http_error_code(r.json()) == "commerce_nomenclature_sku_conflict"


def _commerce_headers(admin_auth: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_auth['access_token']}"}


async def _grant_commerce(db_session, seed_data: dict) -> uuid.UUID:
    org_id = await _bind_seed_clinic_to_org(db_session, seed_data)
    for key in ("core.base", "commerce.store_network"):
        db_session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=org_id,
                entitlement_key=key,
                source="test",
            )
        )
    await db_session.commit()
    return org_id


@pytest.mark.asyncio
async def test_commerce_stock_locations_crud_and_single_default(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r0 = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/stock-locations", headers=h)
    assert r0.status_code == 200
    assert r0.json() == []

    r1 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Точка А", "code": "A", "is_default": True},
    )
    assert r1.status_code == 201
    loc_a = r1.json()
    assert loc_a["is_default"] is True

    r2 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Точка Б", "is_default": True},
    )
    assert r2.status_code == 201
    loc_b_id = r2.json()["id"]

    r_list = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/stock-locations", headers=h)
    assert r_list.status_code == 200
    items = r_list.json()
    assert len(items) == 2
    defaults = [x for x in items if x["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == loc_b_id

    r_patch = await client.patch(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_a['id']}",
        headers=h,
        json={"is_default": True},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["is_default"] is True

    r_list2 = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/stock-locations", headers=h)
    items2 = r_list2.json()
    assert len([x for x in items2 if x["is_default"]]) == 1
    assert [x for x in items2 if x["is_default"]][0]["id"] == loc_a["id"]

    r_del = await client.delete(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_b_id}",
        headers=h,
    )
    assert r_del.status_code == 204

    r404 = await client.delete(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{uuid.uuid4()}",
        headers=h,
    )
    assert r404.status_code == 404


@pytest.mark.asyncio
async def test_commerce_nomenclature_list_patch_delete(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r_empty = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature", headers=h)
    assert r_empty.status_code == 200
    assert r_empty.json() == []

    r_create = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "Позиция 1", "unit": "pcs", "sku": "NOM-1"},
    )
    assert r_create.status_code == 201
    item_id = r_create.json()["id"]

    r_list = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature", headers=h)
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1
    assert r_list.json()[0]["name"] == "Позиция 1"
    assert r_list.json()[0]["is_active"] is True

    r_patch = await client.patch(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/{item_id}",
        headers=h,
        json={"name": "Переименовано", "is_active": False},
    )
    assert r_patch.status_code == 200
    assert r_patch.json()["name"] == "Переименовано"
    assert r_patch.json()["is_active"] is False

    r_del = await client.delete(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/{item_id}", headers=h)
    assert r_del.status_code == 204

    r_list2 = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature", headers=h)
    assert r_list2.json() == []

    r404 = await client.delete(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/{uuid.uuid4()}",
        headers=h,
    )
    assert r404.status_code == 404


@pytest.mark.asyncio
async def test_commerce_nomenclature_patch_sku_conflict_409(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r1 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "A", "sku": "SKU-A"},
    )
    r2 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "B", "sku": "SKU-B"},
    )
    assert r1.status_code == 201 and r2.status_code == 201
    b_id = r2.json()["id"]

    r_conflict = await client.patch(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/{b_id}",
        headers=h,
        json={"sku": "SKU-A"},
    )
    assert r_conflict.status_code == 409
    assert _http_error_code(r_conflict.json()) == "commerce_nomenclature_sku_conflict"


@pytest.mark.asyncio
async def test_commerce_stock_balances_list_and_put(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r_loc = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад 1", "is_default": True},
    )
    assert r_loc.status_code == 201
    loc_id = r_loc.json()["id"]

    r_nom = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "Товар X", "sku": "X-1", "unit": "pcs"},
    )
    assert r_nom.status_code == 201
    item_id = r_nom.json()["id"]

    r_list0 = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances",
        headers=h,
    )
    assert r_list0.status_code == 200
    rows0 = r_list0.json()
    assert len(rows0) == 1
    assert rows0[0]["nomenclature_item_id"] == item_id
    assert rows0[0]["balance_id"] is None
    assert rows0[0]["quantity"] in ("0", 0, "0.0000")

    r_put = await client.put(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances/{item_id}",
        headers=h,
        json={"quantity": "12.5"},
    )
    assert r_put.status_code == 200, r_put.text
    assert Decimal(str(r_put.json()["quantity"])) == Decimal("12.5")
    assert r_put.json()["balance_id"] is not None

    r_list1 = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances",
        headers=h,
    )
    assert Decimal(str(r_list1.json()[0]["quantity"])) == Decimal("12.5")
    assert r_list1.json()[0]["balance_id"] is not None

    r404 = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{uuid.uuid4()}/balances",
        headers=h,
    )
    assert r404.status_code == 404


@pytest.mark.asyncio
async def test_commerce_movement_goods_in_and_list(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r_loc = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад М", "is_default": True},
    )
    assert r_loc.status_code == 201
    loc_id = r_loc.json()["id"]

    r_nom = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "Товар М", "sku": "M-1", "unit": "pcs"},
    )
    assert r_nom.status_code == 201
    item_id = r_nom.json()["id"]

    r_mov = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/movements",
        headers=h,
        json={
            "stock_location_id": loc_id,
            "doc_kind": "goods_in",
            "remark": "Поставка",
            "lines": [{"nomenclature_item_id": item_id, "quantity": "5"}],
        },
    )
    assert r_mov.status_code == 201, r_mov.text
    doc = r_mov.json()
    assert doc["doc_kind"] == "goods_in"
    assert len(doc["lines"]) == 1
    assert Decimal(str(doc["lines"][0]["quantity"])) == Decimal(5)

    r_bal = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances",
        headers=h,
    )
    assert r_bal.status_code == 200
    rows = r_bal.json()
    assert len(rows) == 1
    assert Decimal(str(rows[0]["quantity"])) == Decimal(5)

    r_list = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/movements", headers=h)
    assert r_list.status_code == 200
    assert len(r_list.json()) == 1

    r_one = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/movements/{doc['id']}",
        headers=h,
    )
    assert r_one.status_code == 200
    assert r_one.json()["lines"][0]["name"] == "Товар М"


@pytest.mark.asyncio
async def test_commerce_movement_goods_out_insufficient_409(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r_loc = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад У", "is_default": True},
    )
    loc_id = r_loc.json()["id"]

    r_nom = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "Товар У", "sku": "U-1", "unit": "pcs"},
    )
    item_id = r_nom.json()["id"]

    r_bad = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/movements",
        headers=h,
        json={
            "stock_location_id": loc_id,
            "doc_kind": "goods_out",
            "lines": [{"nomenclature_item_id": item_id, "quantity": "1"}],
        },
    )
    assert r_bad.status_code == 409
    assert _http_error_code(r_bad.json()) == "commerce_insufficient_stock"


@pytest.mark.asyncio
async def test_commerce_transfer_moves_stock_between_locations(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r_a = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад А", "is_default": True},
    )
    r_b = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад Б", "is_default": False},
    )
    assert r_a.status_code == 201 and r_b.status_code == 201
    loc_a = r_a.json()["id"]
    loc_b = r_b.json()["id"]

    r_nom = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "Товар Т", "sku": "T-1", "unit": "pcs"},
    )
    item_id = r_nom.json()["id"]

    assert (
        await client.post(
            f"/api/v1/admin/clinics/{cid}/commerce/movements",
            headers=h,
            json={
                "stock_location_id": loc_a,
                "doc_kind": "goods_in",
                "lines": [{"nomenclature_item_id": item_id, "quantity": "10"}],
            },
        )
    ).status_code == 201

    r_tr = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/movements",
        headers=h,
        json={
            "stock_location_id": loc_a,
            "to_stock_location_id": loc_b,
            "doc_kind": "goods_transfer",
            "lines": [{"nomenclature_item_id": item_id, "quantity": "4"}],
        },
    )
    assert r_tr.status_code == 201, r_tr.text
    doc = r_tr.json()
    assert doc["doc_kind"] == "goods_transfer"
    assert doc["to_stock_location_id"] == loc_b

    bal_a = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_a}/balances",
        headers=h,
    )
    bal_b = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_b}/balances",
        headers=h,
    )
    assert Decimal(str(bal_a.json()[0]["quantity"])) == Decimal(6)
    assert Decimal(str(bal_b.json()[0]["quantity"])) == Decimal(4)


@pytest.mark.asyncio
async def test_commerce_transfer_insufficient_at_source_409(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r_a = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад Источник", "is_default": True},
    )
    r_b = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад Приёмник", "is_default": False},
    )
    loc_a = r_a.json()["id"]
    loc_b = r_b.json()["id"]

    r_nom = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "Товар П", "sku": "P-1", "unit": "pcs"},
    )
    item_id = r_nom.json()["id"]

    r_bad = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/movements",
        headers=h,
        json={
            "stock_location_id": loc_a,
            "to_stock_location_id": loc_b,
            "doc_kind": "goods_transfer",
            "lines": [{"nomenclature_item_id": item_id, "quantity": "1"}],
        },
    )
    assert r_bad.status_code == 409
    assert _http_error_code(r_bad.json()) == "commerce_insufficient_stock"


@pytest.mark.asyncio
async def test_commerce_network_overview_403_without_store_entitlement(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = await _bind_seed_clinic_to_org(db_session, seed_data)
    db_session.add(
        OrganizationEntitlement(
            id=uuid.uuid4(),
            organization_id=org_id,
            entitlement_key="core.base",
            source="test",
        )
    )
    await db_session.commit()
    h = _commerce_headers(admin_auth)
    r = await client.get("/api/v1/admin/organization/commerce/network-overview", headers=h)
    assert r.status_code == 403, r.text
    assert _http_error_code(r.json()) == "entitlement_required"


@pytest.mark.asyncio
async def test_commerce_network_overview_multi_clinic_rollups(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    org_id = await _grant_commerce(db_session, seed_data)
    clinic_b_id = uuid.uuid4()
    db_session.add(
        Clinic(
            id=clinic_b_id,
            organization_id=org_id,
            name="Commerce Clinic B",
            prepayment_amount=500,
            clinic_slug=f"commerce-b-{clinic_b_id.hex[:12]}",
        )
    )
    await db_session.commit()

    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r_loc = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Сеть Точка 1", "is_default": True},
    )
    assert r_loc.status_code == 201
    loc_id = r_loc.json()["id"]
    r_nom = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "SKU сеть", "sku": "NET-1", "unit": "pcs"},
    )
    assert r_nom.status_code == 201
    item_id = r_nom.json()["id"]
    r_put = await client.put(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances/{item_id}",
        headers=h,
        json={"quantity": "7.5"},
    )
    assert r_put.status_code == 200

    r_net = await client.get("/api/v1/admin/organization/commerce/network-overview", headers=h)
    assert r_net.status_code == 200, r_net.text
    body = r_net.json()
    assert body["organization_id"] == str(org_id)
    assert body["totals"]["stock_locations_total"] == 1
    assert body["totals"]["nomenclature_items_total"] == 1
    assert Decimal(str(body["totals"]["total_on_hand_quantity"])) == Decimal("7.5")

    by_name = {c["clinic_name"]: c for c in body["clinics"]}
    assert "Commerce Clinic B" in by_name
    assert "Test Clinic" in by_name
    assert by_name["Commerce Clinic B"]["stock_locations_count"] == 0
    assert by_name["Commerce Clinic B"]["nomenclature_items_count"] == 0
    assert Decimal(str(by_name["Commerce Clinic B"]["total_on_hand_quantity"])) == Decimal(0)
    assert by_name["Test Clinic"]["stock_locations_count"] == 1
    assert by_name["Test Clinic"]["nomenclature_items_count"] == 1
    assert Decimal(str(by_name["Test Clinic"]["total_on_hand_quantity"])) == Decimal("7.5")


@pytest.mark.asyncio
async def test_commerce_nomenclature_import_spec_200(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)
    r = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-spec",
        headers=h,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["profile"] == "commerce_nomenclature_csv_v1"
    assert "name" in data["required_columns"]
    assert "sku" in data["optional_columns"]
    assert data["max_rows"] >= 100


@pytest.mark.asyncio
async def test_commerce_nomenclature_import_csv_create_update_and_skip(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    csv1 = "name,sku,unit,is_active\nAlpha,IMP-1,pcs,true\nBeta,IMP-2,kg,false\n"
    r1 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-csv",
        headers=h,
        files={"file": ("nom.csv", csv1.encode("utf-8"), "text/csv")},
    )
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1["created"] == 2
    assert b1["updated"] == 0
    assert b1["skipped"] == 0

    csv2 = "name,sku,unit\nAlpha2,IMP-1,pcs\nBeta2,IMP-2,kg\n"
    r2 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-csv",
        headers=h,
        files={"file": ("nom.csv", csv2.encode("utf-8"), "text/csv")},
    )
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    assert b2["created"] == 0
    assert b2["updated"] == 2

    r_list = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature", headers=h)
    by_sku = {x["sku"]: x for x in r_list.json()}
    assert by_sku["IMP-1"]["name"] == "Alpha2"
    assert by_sku["IMP-2"]["name"] == "Beta2"
    assert by_sku["IMP-2"]["is_active"] is False

    csv3 = "name,sku\n,SKIPPED\nGamma,IMP-3\n"
    r3 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-csv",
        headers=h,
        files={"file": ("nom.csv", csv3.encode("utf-8"), "text/csv")},
    )
    assert r3.status_code == 200, r3.text
    b3 = r3.json()
    assert b3["created"] == 1
    assert b3["skipped"] == 1
    assert b3["errors"]


@pytest.mark.asyncio
async def test_commerce_nomenclature_import_csv_no_name_column_400(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)
    bad = "sku,unit\nX,pcs\n"
    r = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-csv",
        headers=h,
        files={"file": ("bad.csv", bad.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 400
    assert _http_error_code(r.json()) == "commerce_import_csv_no_name"


@pytest.mark.asyncio
async def test_commerce_balance_import_spec_404_unknown_location(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)
    fake_loc = str(uuid.uuid4())
    r = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{fake_loc}/balances/import-spec",
        headers=h,
    )
    assert r.status_code == 404
    assert _http_error_code(r.json()) == "commerce_stock_location_not_found"


@pytest.mark.asyncio
async def test_commerce_balance_import_csv_create_and_update(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)

    r_loc = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад CSV", "is_default": True},
    )
    assert r_loc.status_code == 201
    loc_id = r_loc.json()["id"]

    r_nom = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "Товар CSV", "sku": "BAL-CSV-1", "unit": "pcs"},
    )
    assert r_nom.status_code == 201

    csv1 = "sku,quantity\nBAL-CSV-1,12.5\n"
    r1 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances/import-csv",
        headers=h,
        files={"file": ("b.csv", csv1.encode("utf-8"), "text/csv")},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["profile"] == "commerce_stock_balances_csv_v1"
    assert r1.json()["created"] == 1
    assert r1.json()["updated"] == 0

    csv2 = "sku,quantity\nBAL-CSV-1,3\n"
    r2 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances/import-csv",
        headers=h,
        files={"file": ("b.csv", csv2.encode("utf-8"), "text/csv")},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["created"] == 0
    assert r2.json()["updated"] == 1

    r_bal = await client.get(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances",
        headers=h,
    )
    assert r_bal.status_code == 200
    lines = r_bal.json()
    row = next(x for x in lines if x["sku"] == "BAL-CSV-1")
    assert Decimal(str(row["quantity"])) == Decimal(3)


@pytest.mark.asyncio
async def test_commerce_balance_import_csv_missing_columns_400(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)
    r_loc = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "Склад X", "is_default": True},
    )
    loc_id = r_loc.json()["id"]
    bad = "sku_only\nX\n"
    r = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances/import-csv",
        headers=h,
        files={"file": ("bad.csv", bad.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 400
    assert _http_error_code(r.json()) == "commerce_import_csv_balance_columns"


@pytest.mark.asyncio
async def test_commerce_nomenclature_import_idempotency_replays_without_duplicates(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)
    csv_body = "name,sku\nIdem A,IDEM-A\n"
    key = "idem-nom-1"
    headers = {**h, "Idempotency-Key": key}
    r1 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-csv",
        headers=headers,
        files={"file": ("n.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["created"] == 1

    r_list = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature", headers=h)
    n_after_first = len(r_list.json())

    r2 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-csv",
        headers=headers,
        files={"file": ("n.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["created"] == r1.json()["created"]

    r_list2 = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/nomenclature", headers=h)
    assert len(r_list2.json()) == n_after_first


@pytest.mark.asyncio
async def test_commerce_import_idempotency_scope_mismatch_409(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)
    shared = "shared-key-xyz"
    r1 = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-csv",
        headers={**h, "Idempotency-Key": shared},
        files={"file": ("n.csv", b"name,sku\nX,SK-1\n", "text/csv")},
    )
    assert r1.status_code == 200, r1.text

    r_loc = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations",
        headers=h,
        json={"name": "L1", "is_default": True},
    )
    loc_id = r_loc.json()["id"]
    await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature",
        headers=h,
        json={"name": "For bal", "sku": "SK-1", "unit": "pcs"},
    )

    r_bad = await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/stock-locations/{loc_id}/balances/import-csv",
        headers={**h, "Idempotency-Key": shared},
        files={"file": ("b.csv", b"sku,quantity\nSK-1,1\n", "text/csv")},
    )
    assert r_bad.status_code == 409
    assert _http_error_code(r_bad.json()) == "commerce_import_idempotency_scope_mismatch"


@pytest.mark.asyncio
async def test_commerce_import_jobs_list_after_nomenclature_csv(
    client: AsyncClient,
    admin_auth: dict,
    seed_data: dict,
    db_session,
) -> None:
    await _grant_commerce(db_session, seed_data)
    cid = str(seed_data["clinic_id"])
    h = _commerce_headers(admin_auth)
    await client.post(
        f"/api/v1/admin/clinics/{cid}/commerce/nomenclature/import-csv",
        headers=h,
        files={"file": ("n.csv", b"name,sku\nJ,J-1\n", "text/csv")},
    )
    rj = await client.get(f"/api/v1/admin/clinics/{cid}/commerce/import-jobs", headers=h)
    assert rj.status_code == 200, rj.text
    jobs = rj.json()
    assert len(jobs) >= 1
    assert jobs[0]["source_profile"] == "commerce_nomenclature_csv_v1"
    assert jobs[0]["status"] == "committed"
