from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from camcat.models import JobKind, JobStatus
from camcat.rendering.fingerprint import MediaFingerprintError
from camcat.rendering.verification import OutputVerificationError
from camcat.repositories import (
    JobRepository,
    _redact_patch_operation,
    redact_transient_document,
    sanitize_job_error,
)
from camcat.worker import FailureCategory, Worker, _failure_category


def test_transient_redaction_removes_keys_transcripts_and_analysis() -> None:
    source = {
        "schema": "camcat-editing-project/v2",
        "project_id": "p",
        "goal": "g",
        "title": "keep",
        "canvas": {"width": 640, "height": 360, "fps_num": 30, "fps_den": 1},
        "sources": [
            {
                "source_id": "user",
                "origin": "user_upload",
                "storage_key": "temporary/user/raw.mp4",
                "retention_class": "transient_4h",
                "metadata": {},
            }
        ],
        "timeline": {
            "tracks": [
                {
                    "type": "video",
                    "track_id": "main",
                    "name": "Main",
                    "segments": [
                        {
                            "type": "video",
                            "segment_id": "seg",
                            "source_id": "user",
                            "timeline_start_us": 0,
                            "timeline_duration_us": 1000000,
                            "source_start_us": 0,
                            "source_duration_us": 1000000,
                            "speed": 1,
                            "transform": {},
                            "reason": "",
                            "evidence": [],
                        }
                    ],
                }
            ],
            "transitions": [],
        },
        "speech_review": {"workflow": "", "items": []},
        "metadata": {
            "source_media": [{"storage_key": "temporary/user/raw.mp4"}],
            "source_segments": [{"transcript": "secret speech"}],
        },
    }

    redacted = redact_transient_document(source)

    assert redacted["title"] == "keep"
    assert redacted["sources"] == []
    assert redacted["timeline"]["tracks"][0]["segments"] == []
    assert redacted["metadata"]["source_media"] == []
    assert redacted["metadata"]["source_segments"] == []
    assert redacted["metadata"]["transient_source_status"] == "expired"


def test_public_job_error_never_exposes_traceback() -> None:
    error = sanitize_job_error(RuntimeError("provider unavailable"))
    assert error == "provider unavailable"
    assert "Traceback" not in error


def test_expired_audit_patch_does_not_retain_transient_storage_keys() -> None:
    operation = {
        "op": "add",
        "path": "/sources/0",
        "value": {"storage_key": "temporary/user/raw.mp4"},
    }

    assert _redact_patch_operation(operation) == {
        "op": "add",
        "path": "/sources/0",
        "redacted": True,
    }


def test_failed_job_runtime_is_not_removed_before_ttl_cleanup(tmp_path: Path) -> None:
    worker = object.__new__(Worker)
    worker.settings = SimpleNamespace(runtime_dir=str(tmp_path))
    job = SimpleNamespace(id="job-1", kind=JobKind.RENDER, status=JobStatus.RUNNING)
    worker.render = Mock(side_effect=ValueError("render failed"))
    job_dir = tmp_path / "jobs" / "job-1"
    job_dir.mkdir(parents=True)
    (job_dir / "secret.mp4").write_bytes(b"secret")

    with suppress(ValueError):
        worker._execute_job(job, SimpleNamespace())

    assert job_dir.exists()


def test_render_failure_freezes_existing_evidence(tmp_path: Path) -> None:
    worker = object.__new__(Worker)
    worker.settings = SimpleNamespace(runtime_dir=str(tmp_path))
    job = SimpleNamespace(
        id="job-2",
        status=JobStatus.FAILED,
        checkpoint={"failure_category": "deterministic"},
    )
    job_dir = tmp_path / "jobs" / "job-2"
    job_dir.mkdir(parents=True)
    (job_dir / "renderer-command.json").write_text("[]")
    (job_dir / "renderer-stderr.log").write_text("failure")

    worker._freeze_render_failure(job, "render failed")

    assert (job_dir / "failure.json").is_file()
    assert (job_dir / "renderer-command.json").is_file()
    assert (job_dir / "renderer-stderr.log").is_file()


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


def test_deterministic_failure_is_terminal_without_automatic_retry() -> None:
    job = SimpleNamespace(
        status=JobStatus.RUNNING,
        attempts=1,
        max_attempts=3,
        worker_id="worker",
        lease_expires_at=datetime.now(UTC),
        cancel_requested_at=None,
        finished_at=None,
        error=None,
        checkpoint={},
    )
    db = Mock()

    JobRepository(db).fail(
        job,
        "compiled timeline is invalid",
        retryable=False,
        category=FailureCategory.DETERMINISTIC_VALIDATION.value,
    )

    assert job.status == JobStatus.FAILED
    assert job.finished_at is not None
    assert job.worker_id is None
    assert job.checkpoint["failure_category"] == "deterministic_validation_failure"
    db.commit.assert_called_once_with()


def test_render_failure_categories_control_retry_semantics() -> None:
    assert _failure_category(MediaFingerprintError("changed")) == FailureCategory.ARTIFACT_DRIFT
    assert _failure_category(OutputVerificationError("bad frames")) == (
        FailureCategory.OUTPUT_VERIFICATION
    )
    assert _failure_category(ConnectionError("object store unavailable")) == (
        FailureCategory.RETRYABLE_INFRASTRUCTURE
    )


def test_render_source_download_is_published_atomically(tmp_path: Path) -> None:
    worker = object.__new__(Worker)
    worker.object_store = Mock()

    def write_download(_storage_key: str, destination: Path) -> None:
        destination.write_bytes(b"complete-media")

    worker.object_store.download_file.side_effect = write_download
    target = tmp_path / "source.mp4"

    worker._download_render_source("temporary/source.mp4", target)

    assert target.read_bytes() == b"complete-media"
    assert not (tmp_path / "source.mp4.download").exists()


def test_failed_render_source_download_removes_partial_file(tmp_path: Path) -> None:
    worker = object.__new__(Worker)
    worker.object_store = Mock()

    def fail_download(_storage_key: str, destination: Path) -> None:
        destination.write_bytes(b"partial")
        raise ConnectionError("object store interrupted")

    worker.object_store.download_file.side_effect = fail_download
    target = tmp_path / "source.mp4"

    with suppress(ConnectionError):
        worker._download_render_source("temporary/source.mp4", target)

    assert not target.exists()
    assert not (tmp_path / "source.mp4.download").exists()
