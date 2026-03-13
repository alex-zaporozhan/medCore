"""Protocol for notification delivery (Telegram, SMS, Email)."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NotificationSender(Protocol):
    """Interface for sending a single notification to one channel."""

    async def send(
        self,
        *,
        chat_id: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        message: str,
        template: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Send the message via this channel. Raises on failure."""
        ...
