"""Structured logging configuration."""

import json
import logging
import sys
from typing import Any

from src.core.config import settings
from src.core.datetime_utils import to_iso8601_utc, utc_now
from src.core.pii_mask import mask_pii_value, mask_phones_in_text


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        msg = record.getMessage()
        if settings.log_mask_pii:
            msg = mask_phones_in_text(msg)

        log_data: dict[str, Any] = {
            "timestamp": to_iso8601_utc(utc_now()),
            "level": record.levelname,
            "logger": record.name,
            "message": msg,
        }

        # Add exception info if present
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            if settings.log_mask_pii:
                exc_text = mask_phones_in_text(exc_text)
            log_data["exception"] = exc_text

        # Add extra fields
        if hasattr(record, "extra"):
            extra = record.extra
            if settings.log_mask_pii:
                extra = mask_pii_value(extra)
            log_data.update(extra)

        return json.dumps(log_data, ensure_ascii=False)


class _PiiPlainFormatter(logging.Formatter):
    """Plain formatter with optional phone masking in the message."""

    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        if settings.log_mask_pii:
            return mask_phones_in_text(s)
        return s


def setup_logging() -> None:
    """Configure logging based on settings."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Set formatter
    if settings.log_format == "json":
        formatter: logging.Formatter = JSONFormatter()
    else:
        formatter = _PiiPlainFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Canary log for initialization
    logger = logging.getLogger(__name__)
    logger.info("[dental-booking] Logging initialized", extra={"component": "logging"})


# Initialize logging on import
setup_logging()
