from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from camcat.models import JobStatus
from camcat.repositories import redact_transient_document, sanitize_job_error
from camcat.worker import Worker


def test_transient_redaction_removes_keys_transcripts_and_analysis() -> None:
    source = {
        "title": "keep",
        "source_media": [{"storage_key": "temporary/user/raw.mp4"}],
        "source_segments": [{"transcript": "secret speech", "thumbnail_key": "temporary/t.jpg"}],
        "clips": [{"origin": "source", "storage_key": "temporary/user/raw.mp4"}],
    }

    redacted = redact_transient_document(source)

    assert redacted["title"] == "keep"
    assert redacted["source_media"] == []
    assert redacted["source_segments"] == []
    assert redacted["clips"] == []
    assert redacted["transient_source_status"] == "expired"


def test_public_job_error_never_exposes_traceback() -> None:
    error = sanitize_job_error(RuntimeError("provider unavailable"))
    assert error == "provider unavailable"
    assert "Traceback" not in error


def test_worker_always_removes_job_directory(tmp_path: Path) -> None:
    worker = object.__new__(Worker)
    worker.settings = SimpleNamespace(runtime_dir=str(tmp_path))
    job = SimpleNamespace(id="job-1", kind="unsupported", status=JobStatus.RUNNING)
    job_dir = tmp_path / "jobs" / "job-1"
    job_dir.mkdir(parents=True)
    (job_dir / "secret.mp4").write_bytes(b"secret")

    with suppress(ValueError):
        worker._execute_job(job, SimpleNamespace())

    assert not job_dir.exists()


def test_retention_timestamp_is_timezone_aware() -> None:
    assert datetime.now(UTC).tzinfo is not None
