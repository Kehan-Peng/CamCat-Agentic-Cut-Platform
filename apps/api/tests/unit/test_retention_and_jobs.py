from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from camcat.models import JobKind, JobStatus
from camcat.repositories import JobRepository, redact_transient_document, sanitize_job_error
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


def test_expired_exhausted_leases_are_committed_as_dead_letters() -> None:
    now = datetime.now(UTC)
    job = SimpleNamespace(
        status=JobStatus.RUNNING,
        attempts=3,
        max_attempts=3,
        worker_id="dead-worker",
        lease_expires_at=now,
        finished_at=None,
        checkpoint={},
    )
    db = Mock()
    db.scalars.return_value.all.return_value = [job]

    expired = JobRepository(db).expire_exhausted_leases(now=now)

    assert expired == [job]
    assert job.status == JobStatus.DEAD_LETTER
    assert job.worker_id is None
    assert job.lease_expires_at is None
    assert job.finished_at == now
    db.commit.assert_called_once_with()
    db.rollback.assert_not_called()


def test_ingest_compensation_attempts_every_store_when_one_cleanup_fails() -> None:
    worker = object.__new__(Worker)
    worker.milvus = Mock()
    worker.milvus.delete_asset.side_effect = RuntimeError("milvus unavailable")
    worker.object_store = Mock()
    db = Mock()

    failures = worker._compensate_failed_ingest("asset-1", db)

    worker.object_store.delete_prefix.assert_any_call("segments/asset-1/")
    worker.object_store.delete_prefix.assert_any_call("thumbnails/asset-1/")
    db.execute.assert_called_once()
    assert failures == ["milvus: milvus unavailable"]


def test_pending_dead_letter_query_is_limited_to_ingestion_jobs() -> None:
    job = SimpleNamespace(kind=JobKind.INGEST_MEDIA, status=JobStatus.DEAD_LETTER)
    db = Mock()
    db.scalars.return_value.all.return_value = [job]

    pending = JobRepository(db).pending_ingest_compensations()

    assert pending == [job]
