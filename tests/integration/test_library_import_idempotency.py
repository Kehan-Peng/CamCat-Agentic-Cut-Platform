from __future__ import annotations

from uuid import uuid4

import pytest
from camcat.api import app
from camcat.database import SessionLocal
from camcat.models import Asset, AssetStatus
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def test_library_import_is_idempotent_by_source_and_license() -> None:
    source_url = f"https://pixabay.com/videos/id-{uuid4()}/"
    with SessionLocal() as db:
        asset = Asset(
            owner_id="library-idempotency",
            filename="existing.mp4",
            content_type="video/mp4",
            size_bytes=1,
            storage_key=f"integration/idempotency/{uuid4()}.mp4",
            duration_seconds=1,
            width=640,
            height=360,
            status=AssetStatus.READY,
            license_name="Pixabay Content License",
            source_url=source_url,
        )
        db.add(asset)
        db.commit()
        asset_id = asset.id

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/videos/import",
            headers={"X-User-Id": "another-library-worker"},
            json={
                "download_url": "https://example.com/would-fail-if-downloaded.mp4",
                "source_url": source_url,
                "license_name": "Pixabay Content License",
                "filename": "duplicate.mp4",
            },
        )
    assert response.status_code == 202, response.text
    assert response.json()["video_id"] == str(asset_id)
    with SessionLocal() as db:
        persisted = db.get(Asset, asset_id)
        assert persisted is not None
        db.delete(persisted)
        db.commit()
