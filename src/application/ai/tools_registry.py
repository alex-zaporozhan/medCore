from __future__ import annotations

from uuid import UUID

from src.application.ai.tools_base import Tool
from src.application.ai.tools_booking import CreateBookingTool, GetAvailableSlotsTool


def get_default_tools_for_clinic(clinic_id: UUID) -> dict[str, Tool]:
    """
    Return default tool set for given clinic.

    For phase 1 this is a static mapping; clinic_id is kept for future
    per-clinic configuration but not used directly by tools yet.
    """
    return {
        "get_available_slots": GetAvailableSlotsTool(),
        "create_booking": CreateBookingTool(),
    }

