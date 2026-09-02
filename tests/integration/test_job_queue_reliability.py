from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from camcat.database import SessionLocal
from camcat.models import Job, JobKind, JobStatus, utcnow
from camcat.repositories import JobRepository

pytestmark = pytest.mark.integration


def test_job_idempotency_expired_lease_retry_and_dead_letter() -> None:
    owner = f"queue-{uuid4()}"
    key = f"ingest-{uuid4()}"
    with SessionLocal() as db:
        repository = JobRepository(db)
        first = repository.enqueue(
            owner_id=owner,
            kind=JobKind.INGEST_MEDIA,
            payload={"asset_id": str(uuid4())},
            idempotency_key=key,
            max_attempts=2,
        )
        duplicate = repository.enqueue(
            owner_id=owner,
            kind=JobKind.INGEST_MEDIA,
            payload={"asset_id": str(uuid4())},
            idempotency_key=key,
            max_attempts=2,
        )
        assert duplicate.id == first.id
        claimed = repository.claim_next(worker_id="worker-a", lease_seconds=60)
        assert claimed is not None
        assert claimed.id == first.id
        assert claimed.attempts == 1
        claimed.lease_expires_at = utcnow() - timedelta(seconds=1)
        db.commit()

    with SessionLocal() as db:
        repository = JobRepository(db)
        reclaimed = repository.claim_next(worker_id="worker-b", lease_seconds=60)
        assert reclaimed is not None
        assert reclaimed.id == first.id
        assert reclaimed.attempts == 2
        repository.fail(reclaimed, "provider unavailable")
        assert reclaimed.status == JobStatus.DEAD_LETTER
        db.delete(reclaimed)
        db.commit()


def test_queued_job_can_be_cancelled_and_explicitly_retried() -> None:
    with SessionLocal() as db:
        repository = JobRepository(db)
        job = repository.enqueue(owner_id=f"cancel-{uuid4()}", kind=JobKind.RENDER, payload={})
        repository.cancel(job)
        assert job.status == JobStatus.CANCELLED
        repository.retry(job)
        assert job.status == JobStatus.QUEUED
        db.delete(db.get(Job, job.id))
        db.commit()
