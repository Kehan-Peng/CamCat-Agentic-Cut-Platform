from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from camcat.config import get_settings
from camcat.gateway.app import GatewayConfig, create_gateway_app
from camcat.gateway.upstream import BailianHttpUpstream
from camcat.services.object_store import ObjectStore

settings = get_settings()
object_store = ObjectStore(settings)
upstream = BailianHttpUpstream(
    base_url=settings.bailian_api_host,
    api_key=settings.bailian_api_key.get_secret_value(),
    timeout_seconds=settings.provider_timeout_seconds,
    max_retries=settings.provider_max_retries,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    object_store.ensure_bucket()
    yield
    upstream.close()


app = create_gateway_app(
    GatewayConfig(
        incoming_api_key=settings.provider_gateway_api_key.get_secret_value(),
    ),
    object_store=object_store,
    upstream=upstream,
)
app.router.lifespan_context = lifespan
