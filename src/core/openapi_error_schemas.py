"""Shared OpenAPI component schemas for HTTP error bodies (1c-Q4 partial / §28).

Per-route ``responses`` may reference these via
``{"schema": {"$ref": "#/components/schemas/ApiHttpErrorBody"}}``.
Canonical contract: docs/architecture/API_PUBLIC_ERROR_CODES.md
"""

from __future__ import annotations

from typing import Any


def _json_schema_ref(name: str) -> dict[str, Any]:
    return {
        "application/json": {
            "schema": {"$ref": f"#/components/schemas/{name}"},
        }
    }


# Merged onto every path operation when mounting ``api_router`` (main.py).
# Route-specific ``responses`` override these for the same status code (FastAPI merge order).
# Representative 403 bodies for entitlement gates (1c-Q4); use on routers with ``require_entitlement``.
OPENAPI_403_ENTITLEMENT_GATE_RESPONSE: dict[str, Any] = {
    "description": (
        "Forbidden — entitlement gate (SaaS tariff) or Box edition block; "
        "see examples `entitlement_required` / `box_forbidden`."
    ),
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/ApiHttpErrorBody"},
            "examples": {
                "entitlement_required": {
                    "summary": "SaaS org lacks required tariff option",
                    "value": {
                        "detail": "Требуется активная опция тарифа для этой организации.",
                        "code": "entitlement_required",
                        "details": {"keys": ["commerce.store_network"]},
                    },
                },
                "box_forbidden": {
                    "summary": "Box edition — module not in product boundary",
                    "value": {
                        "detail": "This module is not available in Box edition.",
                        "code": "box_forbidden",
                        "details": {"keys": ["omni.embed.bundle"]},
                    },
                },
            },
        }
    },
}


STANDARD_OPENAPI_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "Bad request (HTTPException or business rule)",
        "content": _json_schema_ref("ApiHttpErrorBody"),
    },
    401: {
        "description": "Unauthorized — missing or invalid Bearer token",
        "content": _json_schema_ref("ApiHttpErrorBody"),
    },
    403: {
        "description": "Forbidden — RBAC, entitlement gate, or tenant rule",
        "content": _json_schema_ref("ApiHttpErrorBody"),
    },
    404: {
        "description": "Not found",
        "content": _json_schema_ref("ApiHttpErrorBody"),
    },
    405: {
        "description": "Method not allowed",
        "content": _json_schema_ref("ApiHttpErrorBody"),
    },
    409: {
        "description": "Conflict (e.g. idempotency, state)",
        "content": _json_schema_ref("ApiHttpErrorBody"),
    },
    422: {
        "description": "Validation error (Pydantic / FastAPI)",
        "content": _json_schema_ref("ApiValidationErrorBody"),
    },
    429: {
        "description": "Rate limited",
        "content": _json_schema_ref("ApiHttpErrorBody"),
    },
    500: {
        "description": "Internal server error (unhandled exception; no stack in body)",
        "content": _json_schema_ref("ApiInternalErrorBody"),
    },
}


def merge_public_error_schemas_into_openapi(schema: dict[str, Any]) -> None:
    """Register reusable JSON Schemas under ``components.schemas``."""
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    schemas["ApiHttpErrorBody"] = {
        "title": "ApiHttpErrorBody",
        "description": (
            "Unified 4xx/5xx JSON from HTTPException handler (main.py). "
            "Field ``code`` is lowercase snake_case. See API_PUBLIC_ERROR_CODES.md."
        ),
        "type": "object",
        "required": ["detail", "code"],
        "additionalProperties": True,
        "properties": {
            "detail": {"type": "string", "description": "Human-readable message"},
            "code": {
                "type": "string",
                "description": "Stable machine code (snake_case)",
            },
            "details": {
                "type": "object",
                "additionalProperties": True,
                "description": "Optional structured fields (e.g. site_key, field)",
            },
            "trace_id": {"type": "string"},
        },
    }
    schemas["ApiValidationErrorBody"] = {
        "title": "ApiValidationErrorBody",
        "description": "422 from RequestValidationError handler (Pydantic/FastAPI).",
        "type": "object",
        "required": ["detail", "code", "errors"],
        "additionalProperties": True,
        "properties": {
            "detail": {"type": "string"},
            "code": {"type": "string", "default": "validation_error"},
            "errors": {
                "type": "array",
                "items": {"type": "object", "additionalProperties": True},
            },
            "trace_id": {"type": "string"},
        },
    }
    schemas["ApiInternalErrorBody"] = {
        "title": "ApiInternalErrorBody",
        "description": "500 from unhandled exception handler (no stack in body).",
        "type": "object",
        "required": ["detail", "code"],
        "properties": {
            "detail": {"type": "string"},
            "code": {"type": "string", "default": "internal_server_error"},
            "trace_id": {"type": "string"},
        },
    }
