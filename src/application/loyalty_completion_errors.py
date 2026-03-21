"""Exceptions that must block visit completion (BKG_CORE G1 / ERP_LOYALTY policy).

Subclasses are raised from subscription and wallet loyalty paths; ``BookingCompletionService``
maps them to LOYALTY_MISMATCH tasks and structured failure (no ``completed`` status).
"""

from __future__ import annotations


class LoyaltyVisitCompletionBlocked(Exception):
    """Business rules forbid completing the visit until loyalty context is fixed."""

    code: str = "loyalty_visit_blocked"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
