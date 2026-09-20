from __future__ import annotations

from camcat.api import app


def _schema_ref(schema: dict[str, object]) -> str:
    return str(schema["$ref"])


def test_every_asset_list_uses_the_cursor_page_envelope() -> None:
    schema = app.openapi()
    response = schema["paths"]["/api/v1/videos"]["get"]["responses"]["200"]
    body_schema = response["content"]["application/json"]["schema"]

    assert _schema_ref(body_schema).endswith("/PageResponse")


def test_openapi_documents_the_shared_error_envelope() -> None:
    schema = app.openapi()
    session_path = schema["paths"]["/api/v1/editing/sessions/{session_id}"]
    assert "patch" not in session_path
    response = schema["paths"]["/api/v1/editing/sessions/{session_id}/commands"]["post"][
        "responses"
    ]["409"]
    body_schema = response["content"]["application/json"]["schema"]

    assert _schema_ref(body_schema).endswith("/ErrorEnvelope")


def test_public_mutation_contract_is_typed_commands_only() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert "post" in paths["/api/v1/editing/sessions/{session_id}/commands"]
    components = schema["components"]["schemas"]
    assert "EditCommandBatch" in components
    assert "PatchEditingSessionRequest" not in components
    assert "PatchOperationRequest" not in components
