"""Per-organization RAG KB (text store + scoped search) — §24.3 isolation by organization_id."""

from __future__ import annotations

import uuid
from typing import NamedTuple, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.domain.entities.organization_rag_kb_document import OrganizationRagKbDocument


def escape_ilike_user_fragment(fragment: str) -> str:
    """
    Экранирует `%`, `_`, `\\` для ILIKE с ``ESCAPE '\\'`` (PostgreSQL).

    Без этого пользовательский `%`/`_` ведут себя как wildcards — шире выдача и
    непредсказуемые совпадения (не SQL-инъекция при bind-параметрах, но логическая дыра).
    """
    return (
        fragment.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


class DeletedRagKbSnapshot(NamedTuple):
    id: uuid.UUID
    title: str


async def count_documents_for_org(session: AsyncSession, organization_id: uuid.UUID) -> int:
    res = await session.execute(
        select(func.count())
        .select_from(OrganizationRagKbDocument)
        .where(OrganizationRagKbDocument.organization_id == organization_id)
    )
    return int(res.scalar_one() or 0)


async def list_documents(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    limit: int = 50,
) -> Sequence[OrganizationRagKbDocument]:
    lim = max(1, min(limit, 200))
    res = await session.execute(
        select(OrganizationRagKbDocument)
        .where(OrganizationRagKbDocument.organization_id == organization_id)
        .order_by(OrganizationRagKbDocument.updated_at.desc())
        .limit(lim)
    )
    return res.scalars().all()


async def create_document(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    title: str,
    body: str,
) -> OrganizationRagKbDocument:
    row = OrganizationRagKbDocument(
        id=uuid.uuid4(),
        organization_id=organization_id,
        title=title.strip()[:255],
        body=body.strip(),
    )
    session.add(row)
    await session.flush()
    return row


async def delete_document(
    session: AsyncSession,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
) -> DeletedRagKbSnapshot | None:
    row = await session.get(OrganizationRagKbDocument, document_id)
    if row is None or row.organization_id != organization_id:
        return None
    snap = DeletedRagKbSnapshot(id=row.id, title=row.title)
    await session.delete(row)
    await session.flush()
    return snap


async def get_document(
    session: AsyncSession,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
) -> OrganizationRagKbDocument | None:
    row = await session.get(OrganizationRagKbDocument, document_id)
    if row is None or row.organization_id != organization_id:
        return None
    return row


async def update_document(
    session: AsyncSession,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    title: str | None,
    body: str | None,
) -> OrganizationRagKbDocument | None:
    row = await session.get(OrganizationRagKbDocument, document_id)
    if row is None or row.organization_id != organization_id:
        return None
    if title is None and body is None:
        return row
    if title is not None:
        row.title = title.strip()[:255]
    if body is not None:
        row.body = body.strip()
    await session.flush()
    return row


def _normalized_search_mode() -> str:
    m = (settings.rag_kb_search_mode or "ilike").strip().lower()
    if m not in ("ilike", "fts", "hybrid"):
        return "ilike"
    return m


def get_rag_kb_search_mode_label() -> str:
    """Метка для метрик / логов (ilike | fts | hybrid)."""
    return _normalized_search_mode()


async def _search_ilike(
    session: AsyncSession,
    organization_id: uuid.UUID,
    query: str,
    *,
    limit: int,
) -> list[OrganizationRagKbDocument]:
    q = (query or "").strip()
    if len(q) < 2:
        return []
    lim = max(1, min(limit, 25))
    literal = escape_ilike_user_fragment(q[:200])
    pattern = f"%{literal}%"
    esc = "\\"
    res = await session.execute(
        select(OrganizationRagKbDocument)
        .where(
            OrganizationRagKbDocument.organization_id == organization_id,
            or_(
                OrganizationRagKbDocument.title.ilike(pattern, escape=esc),
                OrganizationRagKbDocument.body.ilike(pattern, escape=esc),
            ),
        )
        .order_by(OrganizationRagKbDocument.updated_at.desc())
        .limit(lim)
    )
    return list(res.scalars().all())


async def _search_fts(
    session: AsyncSession,
    organization_id: uuid.UUID,
    query: str,
    *,
    limit: int,
) -> list[OrganizationRagKbDocument]:
    """PostgreSQL `plainto_tsquery` + `@@` on generated `search_tsv` (GIN)."""
    q = (query or "").strip()
    if len(q) < 2:
        return []
    lim = max(1, min(limit, 25))
    token = q[:200]
    tsq = func.plainto_tsquery("simple", token)
    res = await session.execute(
        select(OrganizationRagKbDocument)
        .where(
            OrganizationRagKbDocument.organization_id == organization_id,
            OrganizationRagKbDocument.search_tsv.op("@@")(tsq),
        )
        .order_by(OrganizationRagKbDocument.updated_at.desc())
        .limit(lim)
    )
    return list(res.scalars().all())


async def search_documents_for_org(
    session: AsyncSession,
    organization_id: uuid.UUID,
    query: str,
    *,
    limit: int = 8,
) -> list[OrganizationRagKbDocument]:
    """
    Retrieval v1: ILIKE (default), либо FTS (`rag_kb_search_mode=fts`), либо hybrid (FTS затем ILIKE).

    Векторный поиск — отдельная фаза (см. ADR-014).
    """
    mode = _normalized_search_mode()
    if mode == "ilike":
        return await _search_ilike(session, organization_id, query, limit=limit)
    if mode == "fts":
        return await _search_fts(session, organization_id, query, limit=limit)
    hits = await _search_fts(session, organization_id, query, limit=limit)
    if hits:
        return hits
    return await _search_ilike(session, organization_id, query, limit=limit)
