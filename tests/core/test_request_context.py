from uuid import uuid4

import pytest
from fastapi import FastAPI

from src.api.v1.dependencies import AdminContext, get_request_context
from src.core.context import RequestContext


def test_request_context_basic_fields():
    clinic_id = uuid4()
    user_id = uuid4()
    ctx = RequestContext(
        clinic_id=clinic_id,
        user_id=user_id,
        user_type="admin",
        roles={"role1"},
        permissions={"perm1"},
    )

    assert ctx.clinic_id == clinic_id
    assert ctx.user_id == user_id
    assert ctx.user_type == "admin"
    assert "role1" in ctx.roles
    assert "perm1" in ctx.permissions


@pytest.mark.asyncio
async def test_get_request_context_system_fallback(monkeypatch):
    """
    When no Authorization header is provided, get_request_context should
    return a system-level RequestContext with empty clinic_id and permissions.
    """

    async def _dependency_no_auth() -> RequestContext:
        return await get_request_context(authorization=None)  # type: ignore[arg-type]

    ctx = await _dependency_no_auth()

    assert isinstance(ctx, RequestContext)
    assert ctx.clinic_id is None
    assert ctx.user_id is None
    assert ctx.user_type == "system"
    assert ctx.roles == set()
    assert ctx.permissions == set()


def test_admin_context_is_subclass_of_request_context():
    """
    AdminContext is a thin typed wrapper over RequestContext and should
    behave as its subclass for type checks.
    """

    app = FastAPI()

    @app.get("/me")
    async def me(context: AdminContext = pytest.skip("dependency not executed in unit test")):  # type: ignore[unused-ignore]
        return {"clinic_id": str(context.clinic_id) if context.clinic_id else None}

    # We don't actually call the endpoint here; the important part is that
    # AdminContext is available for FastAPI type usage and is a subclass.
    assert issubclass(AdminContext, RequestContext)

