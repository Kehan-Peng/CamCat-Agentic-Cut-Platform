from __future__ import annotations

import asyncio
import json

from camcat.api import internal_error_handler
from starlette.requests import Request


def test_unhandled_error_uses_envelope_without_exception_details() -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "headers": [(b"x-request-id", b"request-123")],
        }
    )
    request.state.request_id = "request-123"

    response = asyncio.run(internal_error_handler(request, RuntimeError("secret filesystem path")))
    payload = json.loads(response.body)

    assert response.status_code == 500
    assert payload == {
        "error": {
            "code": "internal_error",
            "message": "服务器无法完成请求。",
            "details": {},
            "request_id": "request-123",
        }
    }
    assert "secret filesystem path" not in response.body.decode()
