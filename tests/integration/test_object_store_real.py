from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from camcat.config import get_settings
from camcat.services.object_store import ObjectStore

pytestmark = pytest.mark.integration


def test_real_s3_upload_download_and_signed_url(tmp_path: Path) -> None:
    settings = get_settings()
    store = ObjectStore(settings)
    store.ensure_bucket()
    lifecycle = store._client.get_bucket_lifecycle_configuration(Bucket=store.bucket)
    rule = next(item for item in lifecycle["Rules"] if item["ID"] == "expire-transient-user-media")
    assert rule["Status"] == "Enabled"
    assert rule["Filter"]["Prefix"] == "temporary/"
    source = tmp_path / "artifact.txt"
    source.write_text("camcat-real-object-store", encoding="utf-8")
    key = f"integration/{uuid4()}.txt"
    store.upload_file(source, key, "text/plain")
    downloaded = tmp_path / "downloaded.txt"
    store.download_file(key, downloaded)
    assert downloaded.read_text(encoding="utf-8") == "camcat-real-object-store"
    assert "X-Amz-Signature" in store.signed_url(key)
