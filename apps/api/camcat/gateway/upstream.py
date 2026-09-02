from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx


class BailianUpstreamError(RuntimeError):
    """A sanitized failure returned by or while reaching Bailian."""


class BailianHttpUpstream:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 120,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        normalized_url = base_url.rstrip("/")
        if not normalized_url.startswith(("http://", "https://")):
            raise ValueError("Bailian base URL must be an absolute HTTP(S) URL")
        if not api_key.strip():
            raise ValueError("Bailian API key is required")
        if max_retries < 0:
            raise ValueError("Bailian max_retries must be nonnegative")
        self._base_url = normalized_url
        self._max_retries = max_retries
        self._sleeper = sleeper
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    def post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not path.startswith("/"):
            raise ValueError("Bailian request path must start with a slash")
        last_error: BailianUpstreamError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.post(f"{self._base_url}{path}", json=payload)
            except httpx.TransportError as exc:
                last_error = BailianUpstreamError(
                    f"Bailian transport failure: {type(exc).__name__}"
                )
                if attempt < self._max_retries:
                    self._sleeper(0.25 * (2**attempt))
                    continue
                raise last_error from exc

            if response.status_code == 429 or response.status_code >= 500:
                last_error = BailianUpstreamError(
                    f"Bailian transient HTTP response {response.status_code}"
                )
                if attempt < self._max_retries:
                    self._sleeper(0.25 * (2**attempt))
                    continue
                raise last_error
            if response.is_error:
                raise BailianUpstreamError(
                    f"Bailian rejected the request with HTTP {response.status_code}"
                )
            try:
                body = response.json()
            except ValueError as exc:
                raise BailianUpstreamError("Bailian returned invalid JSON") from exc
            if not isinstance(body, dict):
                raise BailianUpstreamError("Bailian returned non-object JSON")
            return body

        raise last_error or BailianUpstreamError("Bailian request failed")

    def close(self) -> None:
        self._client.close()
