from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import UUID

import pytest
from camcat.api import app
from camcat.database import SessionLocal
from camcat.models import Asset, Job, JobKind
from fastapi.testclient import TestClient
from sqlalchemy import func, select

pytestmark = pytest.mark.integration


def test_user_source_upload_creates_analysis_job_but_no_library_asset(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=320x180:d=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    with SessionLocal() as db:
        assets_before = int(db.scalar(select(func.count(Asset.id))) or 0)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/source-media",
            headers={"X-User-Id": "transient-contract"},
            files=[
                ("files", ("raw-one.mp4", source.read_bytes(), "video/mp4")),
                ("files", ("raw-two.mp4", source.read_bytes(), "video/mp4")),
            ],
        )
    assert response.status_code == 202, response.text
    payload = response.json()
    assert len(payload["media"]) == 2
    assert all(item["storage_key"].startswith("temporary/") for item in payload["media"])

    with SessionLocal() as db:
        assets_after = int(db.scalar(select(func.count(Asset.id))) or 0)
        job = db.get(Job, UUID(payload["job_id"]))
        assert job is not None
        assert job.kind == JobKind.ANALYZE_SOURCE
    assert assets_after == assets_before
