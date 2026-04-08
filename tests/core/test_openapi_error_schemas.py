"""OpenAPI exposes shared error body schemas (1c-Q4 partial)."""

from fastapi.testclient import TestClient

from src.main import app


def test_openapi_includes_api_error_component_schemas() -> None:
    client = TestClient(app)
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schemas = r.json().get("components", {}).get("schemas", {})
    assert "ApiHttpErrorBody" in schemas
    assert "ApiValidationErrorBody" in schemas
    assert "ApiInternalErrorBody" in schemas
    props = schemas["ApiHttpErrorBody"].get("properties", {})
    assert "code" in props and "detail" in props


def test_openapi_v1_operations_include_standard_error_response_refs() -> None:
    """Mounted api_router merges STANDARD_OPENAPI_ERROR_RESPONSES into every op (10-Q7)."""
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})
    found = False
    for path_key, methods in paths.items():
        if "/api/v1/" not in path_key:
            continue
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.startswith("x-") or not isinstance(op, dict):
                continue
            resp = op.get("responses", {})
            r403 = resp.get("403") or resp.get(403)
            r422 = resp.get("422") or resp.get(422)
            if not r403 or not r422:
                continue
            ref403 = (
                r403.get("content", {})
                .get("application/json", {})
                .get("schema", {})
                .get("$ref")
            )
            ref422 = (
                r422.get("content", {})
                .get("application/json", {})
                .get("schema", {})
                .get("$ref")
            )
            if ref403 == "#/components/schemas/ApiHttpErrorBody" and ref422 == "#/components/schemas/ApiValidationErrorBody":
                found = True
                break
        if found:
            break
    assert found, "expected at least one /api/v1 operation with 403+422 standard error refs"


def test_openapi_embed_public_assistant_and_rag_documented() -> None:
    """1c-Q4: успешные тела + пример доменного 400 для публичного embed (§24)."""
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    paths = spec.get("paths", {})

    asst = paths.get("/api/v1/public/embed/v1/assistant/message", {})
    asst_post = asst.get("post", {})
    assert asst_post.get("summary")
    ok_asst = asst_post.get("responses", {}).get("200", {})
    ref_asst = (
        ok_asst.get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("$ref", "")
    )
    assert ref_asst.endswith("EmbedAssistantMessageResponse"), ref_asst
    ex400 = (
        asst_post.get("responses", {})
        .get("400", {})
        .get("content", {})
        .get("application/json", {})
        .get("example", {})
    )
    assert ex400.get("code") == "embed_ai_input_too_long"

    rag = paths.get("/api/v1/public/embed/v1/rag/search", {})
    rag_post = rag.get("post", {})
    assert rag_post.get("summary")
    ref_rag = (
        rag_post.get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("$ref", "")
    )
    assert ref_rag.endswith("EmbedRagSearchResponse"), ref_rag

    ex403_rag = (
        rag_post.get("responses", {})
        .get("403", {})
        .get("content", {})
        .get("application/json", {})
        .get("example", {})
    )
    assert ex403_rag.get("code") == "entitlement_required"
    assert "ai.rag.org_kb" in (ex403_rag.get("details") or {}).get("keys", [])

    ex403_asst = (
        asst_post.get("responses", {})
        .get("403", {})
        .get("content", {})
        .get("application/json", {})
        .get("example", {})
    )
    assert ex403_asst.get("code") == "entitlement_required"
    assert "ai.assistant.chat" in (ex403_asst.get("details") or {}).get("keys", [])
