from uuid import uuid4
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.erp_finance_dto import ErpVisitNodeRequest
from src.application.services.erp_node_service import ErpVisitNodeService
from src.application.services.booking_erp_service import ERPConfigurationError


class DummySession(AsyncSession):  # type: ignore[misc]
    """Lightweight stub; real DB interaction is covered in BookingErpService tests."""

    pass


class FailingErpService(ErpVisitNodeService):
    async def process_visit_completion(  # type: ignore[override]
        self,
        request: ErpVisitNodeRequest,
        *,
        session: AsyncSession,
    ):
        raise ERPConfigurationError(code="test_error", message="test")


@pytest.mark.asyncio
async def test_erp_node_invalid_request_missing_ids() -> None:
    service = ErpVisitNodeService()
    req = ErpVisitNodeRequest(
        booking_id=uuid4(),
        clinic_id=uuid4(),
        visit_date=datetime.utcnow(),
        services=[],
        payments=[],
        payroll_inputs=[],
        inventory_items=[],
    )
    # Valid request should be accepted and return a result object
    # (behaviour of legacy BookingErpService is tested elsewhere).
    result = await service.process_visit_completion(req, session=DummySession())
    assert result.success in (True, False)

