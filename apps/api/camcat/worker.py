from __future__ import annotations

import json
import shutil
import signal
import time
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from types import FrameType
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import delete, select, text

from camcat.config import get_settings
from camcat.database import SessionLocal
from camcat.domain.project import EditingProjectV2
from camcat.media.ffmpeg import (
    detect_scene_cuts,
    extract_audio,
    extract_clip,
    extract_thumbnail,
    measure_visual_quality,
    probe,
    shot_signature,
)
from camcat.media.segmentation import build_segments
from camcat.models import (
    Asset,
    AssetStatus,
    EditingSession,
    Job,
    JobKind,
    JobStatus,
    Segment,
    StateVersion,
    utcnow,
)
from camcat.rendering.build import (
    BuildVerificationError,
    RenderBuildService,
    verify_render_build,
)
from camcat.rendering.doctor import RendererCapabilityProfile, inspect_capabilities
from camcat.rendering.ffmpeg_renderer import FFmpegRenderer, FFmpegRenderError
from camcat.rendering.fingerprint import MediaFingerprintError, fingerprint_media
from camcat.rendering.materialization import MaterializedSources
from camcat.rendering.verification import OutputVerificationError, verify_output
from camcat.repositories import JobRepository, sanitize_job_error
from camcat.retrieval.milvus_store import MilvusSegmentStore
from camcat.services.object_store import ObjectStore
from camcat.services.providers import (
    QwenAsrClient,
    QwenChatClient,
    QwenEmbeddingClient,
    QwenVisualAnalysisClient,
)
from camcat.timeline.compiler import TimelineCompilerV2
from camcat.timeline.schemas import RenderProfile
from camcat.timeline.validator import (
    TimelineValidationError,
    content_hash,
    verify_compiled_timeline,
)


class Worker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.object_store = ObjectStore(self.settings)
        self.embedding = QwenEmbeddingClient(self.settings)
        self.chat = QwenChatClient(self.settings)
        self.visual_analysis = QwenVisualAnalysisClient(self.settings)
        self.asr = QwenAsrClient(self.settings)
        self.milvus = MilvusSegmentStore(self.settings)
        self.capabilities: RendererCapabilityProfile | None = None
        self.running = True
        self._last_maintenance = 0.0

    def bootstrap(self) -> None:
        Path(self.settings.runtime_dir).mkdir(parents=True, exist_ok=True)
        self.object_store.ensure_bucket()
        self.milvus.ensure_collection()
        self.capabilities = inspect_capabilities(
            Path(self.settings.runtime_dir),
            object_store_healthcheck=self.object_store.ensure_bucket,
        )

    def run(self) -> None:
        self.bootstrap()
        while self.running:
            with SessionLocal() as db:
                repository = JobRepository(db)
                if time.monotonic() - self._last_maintenance >= 60:
                    self._run_maintenance(repository)
                    self._last_maintenance = time.monotonic()
                job = repository.claim_next(
                    worker_id=self.settings.worker_id,
                    lease_seconds=self.settings.job_lease_seconds,
                )
                if job is None:
                    time.sleep(self.settings.worker_poll_seconds)
                    continue
                try:
                    result = self._execute_job(job, repository)
                    repository.succeed(job, result)
                    if job.kind == JobKind.RENDER:
                        self._remove_job_runtime(job)
                except Exception as exc:
                    db.rollback()
                    error = sanitize_job_error(exc)
                    category = _failure_category(exc)
                    repository.fail(
                        job,
                        error,
                        retryable=category == FailureCategory.RETRYABLE_INFRASTRUCTURE,
                        category=category.value,
                    )
                    if job.kind == JobKind.INGEST_MEDIA and job.status in {
                        JobStatus.FAILED,
                        JobStatus.DEAD_LETTER,
                    }:
                        self._finalize_failed_ingest(job, db, error)
                    if job.kind == JobKind.RENDER and job.status in {
                        JobStatus.FAILED,
                        JobStatus.CANCELLED,
                        JobStatus.DEAD_LETTER,
                    }:
                        self._freeze_render_failure(job, error)

    def _run_maintenance(self, repository: JobRepository) -> None:
        lock_key = 7_823_441_901
        acquired = bool(
            repository.db.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key})
        )
        if not acquired:
            return
        try:
            cutoff = utcnow()
            repository.expire_exhausted_leases(now=cutoff)
            for dead_job in repository.pending_ingest_compensations():
                self._finalize_failed_ingest(
                    dead_job,
                    repository.db,
                    dead_job.error or "worker lease expired after maximum attempts",
                )
            expired_jobs = repository.db.scalars(
                select(Job).where(Job.expires_at <= cutoff, Job.redacted_at.is_(None))
            ).all()
            for expired_job in expired_jobs:
                for storage_key in _temporary_keys(
                    {"payload": expired_job.payload, "result": expired_job.result}
                ):
                    self.object_store.delete_key(storage_key)
            repository.redact_expired(now=cutoff)
            expired_evidence = repository.db.scalars(
                select(Job).where(
                    Job.kind == JobKind.RENDER,
                    Job.status.in_([JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.DEAD_LETTER]),
                    Job.finished_at < cutoff - timedelta(hours=24),
                )
            ).all()
            for render_job in expired_evidence:
                self._remove_job_runtime(render_job)
        finally:
            repository.db.scalar(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key})

    def _remove_job_runtime(self, job: Job) -> None:
        job_dir = Path(self.settings.runtime_dir) / "jobs" / str(job.id)
        shutil.rmtree(job_dir, ignore_errors=True)

    def _freeze_render_failure(self, job: Job, error: str) -> None:
        job_dir = Path(self.settings.runtime_dir) / "jobs" / str(job.id)
        job_dir.mkdir(parents=True, exist_ok=True)
        evidence = {
            "schema": "camcat-render-failure/v1",
            "job_id": str(job.id),
            "status": job.status.value,
            "category": (job.checkpoint or {}).get("failure_category"),
            "error": error,
            "failed_at": utcnow().isoformat(),
            "retention_hours": 24,
        }
        (job_dir / "failure.json").write_text(
            json.dumps(evidence, ensure_ascii=False, sort_keys=True), encoding="utf-8"
        )

    def _finalize_failed_ingest(self, job: Job, db: Any, error: str) -> None:
        try:
            asset_id = UUID(str(job.payload["asset_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            checkpoint = dict(job.checkpoint or {})
            checkpoint.update(
                {
                    "stage": "compensation_failed",
                    "updated_at": utcnow().isoformat(),
                    "failures": [f"payload: {sanitize_job_error(exc)}"],
                }
            )
            job.checkpoint = checkpoint
            db.commit()
            return
        failures = self._compensate_failed_ingest(asset_id, db)
        failed_asset = db.get(Asset, asset_id)
        if failed_asset is not None:
            failed_asset.status = AssetStatus.FAILED
            failed_asset.error = error
        checkpoint = dict(job.checkpoint or {})
        checkpoint.update(
            {
                "stage": "compensation_pending" if failures else "compensated",
                "updated_at": utcnow().isoformat(),
                "failures": failures,
            }
        )
        job.checkpoint = checkpoint
        db.commit()

    def _compensate_failed_ingest(self, asset_id: UUID | str, db: Any) -> list[str]:
        failures: list[str] = []
        external_steps = (
            ("milvus", lambda: self.milvus.delete_asset(str(asset_id))),
            ("segments", lambda: self.object_store.delete_prefix(f"segments/{asset_id}/")),
            (
                "thumbnails",
                lambda: self.object_store.delete_prefix(f"thumbnails/{asset_id}/"),
            ),
        )
        for name, cleanup in external_steps:
            try:
                cleanup()
            except Exception as exc:
                failures.append(f"{name}: {sanitize_job_error(exc)}")
        try:
            db.execute(delete(Segment).where(Segment.asset_id == asset_id))
        except Exception as exc:
            db.rollback()
            failures.append(f"postgres: {sanitize_job_error(exc)}")
        return failures

    def _execute_job(self, job: Job, repository: JobRepository) -> dict[str, Any]:
        job_dir = Path(self.settings.runtime_dir) / "jobs" / str(job.id)
        try:
            if job.kind == JobKind.INGEST_MEDIA:
                return self.ingest(job, repository)
            if job.kind == JobKind.ANALYZE_SOURCE:
                return self.analyze_source(job, repository)
            if job.kind == JobKind.RENDER:
                return self.render(job, repository)
            raise ValueError(f"unsupported job kind: {job.kind}")
        finally:
            if job.kind != JobKind.RENDER:
                shutil.rmtree(job_dir, ignore_errors=True)

    def analyze_source(self, job: Job, jobs: JobRepository) -> dict[str, Any]:
        """Analyze user originals without inserting Asset/Segment or Milvus entities."""
        source_media = list(job.payload.get("source_media", []))
        if not source_media:
            raise ValueError("source analysis job contains no media")
        analysis_mode = str(job.payload.get("analysis_mode", "keyframes"))
        job_dir = Path(self.settings.runtime_dir) / "jobs" / str(job.id)
        analyzed_media: list[dict[str, Any]] = []
        analyzed_segments: list[dict[str, Any]] = []
        estimated_segments = 0

        for item in source_media:
            source = job_dir / "sources" / f"{item['media_id']}.mp4"
            self.object_store.download_file(str(item["storage_key"]), source)
            metadata = probe(source)
            cuts = detect_scene_cuts(source)
            boundaries = build_segments(
                duration=metadata.duration,
                fixed_window=(
                    1.0 if analysis_mode == "per-second" else self.settings.segment_window_seconds
                ),
                scene_cuts=cuts,
                minimum_duration=(
                    0.5 if analysis_mode == "per-second" else self.settings.segment_minimum_seconds
                ),
                event_times=[] if analysis_mode == "per-second" else cuts,
            )
            estimated_segments += len(boundaries)
            enriched = {
                **item,
                "duration_seconds": metadata.duration,
                "width": metadata.width,
                "height": metadata.height,
                "has_audio": metadata.has_audio,
            }
            analyzed_media.append(enriched)

            for boundary_index, boundary in enumerate(boundaries):
                source_segment_id = f"source:{item['media_id']}:{boundary_index + 1}"
                clip = job_dir / "analysis" / f"{item['media_id']}-{boundary_index}.mp4"
                thumbnail = job_dir / "thumbnails" / f"{item['media_id']}-{boundary_index}.jpg"
                extract_clip(source, clip, start=boundary.start, end=boundary.end)
                extract_thumbnail(clip, thumbnail, at=max(0.0, (boundary.end - boundary.start) / 2))
                transcript = ""
                transcript_cues: list[dict[str, Any]] = []
                if metadata.has_audio:
                    audio = job_dir / "audio" / f"{item['media_id']}-{boundary_index}.mp3"
                    extract_audio(clip, audio)
                    transcription = self.asr.transcribe(audio)
                    transcript = str(transcription.get("text") or "").strip()
                    transcript_cues = _transcription_cues(transcription)
                quality = measure_visual_quality(clip)
                signature = shot_signature(thumbnail)
                thumbnail_key = (
                    f"temporary/{job.owner_id}/{job.payload['batch_id']}/analysis/"
                    f"{item['media_id']}-{boundary_index}.jpg"
                )
                self.object_store.upload_file(
                    thumbnail,
                    thumbnail_key,
                    "image/jpeg",
                    metadata={
                        "expires-at": str(job.payload["expires_at"]),
                        "kind": "source-analysis",
                    },
                )
                description = (
                    transcript or f"用户原片 {item['filename']} 的第 {boundary_index + 1} 个镜头"
                )
                analyzed_segments.append(
                    {
                        "segment_id": source_segment_id,
                        "origin": "source",
                        "media_id": item["media_id"],
                        "filename": item["filename"],
                        "storage_key": item["storage_key"],
                        "thumbnail_key": thumbnail_key,
                        "start_time": boundary.start,
                        "end_time": boundary.end,
                        "description_text": description,
                        "transcript": transcript,
                        "transcript_cues": transcript_cues,
                        "quality_score": quality,
                        "shot_signature": signature,
                        "trigger_type": boundary.trigger_type,
                    }
                )
                processed = len(analyzed_segments)
                jobs.update_progress(
                    job,
                    min(0.95, 0.05 + 0.9 * processed / max(1, estimated_segments)),
                )

        return {
            "batch_id": str(job.payload["batch_id"]),
            "expires_at": str(job.payload["expires_at"]),
            "source_media": analyzed_media,
            "source_segments": analyzed_segments,
            "media_count": len(analyzed_media),
            "segment_count": len(analyzed_segments),
            "storage_policy": "transient-4h-no-asset-no-milvus",
        }

    def ingest(self, job: Job, jobs: JobRepository) -> dict[str, Any]:
        asset_id = UUID(str(job.payload["asset_id"]))
        db = jobs.db
        asset = db.get(Asset, asset_id)
        if asset is None:
            raise LookupError("asset no longer exists")
        asset.status = AssetStatus.PROCESSING
        db.commit()

        job_dir = Path(self.settings.runtime_dir) / "jobs" / str(job.id)
        source = job_dir / "source.mp4"
        self.object_store.download_file(asset.storage_key, source)
        metadata = probe(source)
        asset.duration_seconds = metadata.duration
        asset.width = metadata.width
        asset.height = metadata.height
        jobs.update_progress(job, 0.08)
        jobs.checkpoint(job, "source_probed", {"duration_seconds": metadata.duration})

        cuts = detect_scene_cuts(source)
        analysis_mode = str(job.payload.get("analysis_mode", "keyframes"))
        boundaries = build_segments(
            duration=metadata.duration,
            fixed_window=(
                1.0 if analysis_mode == "per-second" else self.settings.segment_window_seconds
            ),
            scene_cuts=cuts,
            minimum_duration=(
                0.5 if analysis_mode == "per-second" else self.settings.segment_minimum_seconds
            ),
            event_times=[] if analysis_mode == "per-second" else cuts,
        )
        current_segment_ids: set[UUID] = set()
        milvus_rows: list[dict[str, Any]] = []
        for index, boundary in enumerate(boundaries):
            segment_id = uuid5(
                NAMESPACE_URL,
                (
                    f"camcat-segment:{asset.source_url}:{asset.license_name}:"
                    f"{boundary.start:.6f}:{boundary.end:.6f}"
                ),
            )
            current_segment_ids.add(segment_id)
            segment = db.get(Segment, segment_id)
            if segment is None:
                segment = Segment(
                    id=segment_id,
                    asset_id=asset.id,
                    start_time=boundary.start,
                    end_time=boundary.end,
                    trigger_type=boundary.trigger_type,
                    storage_key="pending",
                    description_text="",
                    tags=[],
                    semantic_metadata={},
                    embedding_model=self.settings.embedding_model,
                    embedding_dimension=self.settings.embedding_dimension,
                )
                db.add(segment)
                db.flush()
            clip = job_dir / "segments" / f"{segment.id}.mp4"
            thumbnail = job_dir / "thumbnails" / f"{segment.id}.jpg"
            extract_clip(source, clip, start=boundary.start, end=boundary.end)
            extract_thumbnail(clip, thumbnail, at=max(0.0, (boundary.end - boundary.start) / 2))

            transcript = ""
            if metadata.has_audio:
                audio = job_dir / "audio" / f"{segment.id}.mp3"
                extract_audio(clip, audio)
                transcription = self.asr.transcribe(audio)
                transcript = str(transcription.get("text") or "").strip()
            semantics = self.visual_analysis.analyze_video(clip, transcript=transcript)
            jobs.checkpoint(
                job,
                "visual_semantics_ready",
                {"completed": index, "total": len(boundaries)},
            )
            caption_parts = [
                semantics.description,
                f"场景：{semantics.scene}",
                f"构图：{semantics.composition}",
            ]
            if semantics.actions:
                caption_parts.append(f"动作：{' / '.join(semantics.actions)}")
            if transcript:
                caption_parts.append(f"语音转写：{transcript}")
            caption = "\n".join(caption_parts)
            tags = list(dict.fromkeys([*semantics.tags, "有声" if transcript else "无声"]))
            event_type = semantics.event_type
            risk_score = semantics.risk_score
            vector = self.embedding.embed_video(clip, text=caption)

            clip_key = f"segments/{asset.id}/{segment.id}.mp4"
            thumbnail_key = f"thumbnails/{asset.id}/{segment.id}.jpg"
            self.object_store.upload_file(clip, clip_key, "video/mp4")
            self.object_store.upload_file(thumbnail, thumbnail_key, "image/jpeg")
            segment.storage_key = clip_key
            segment.thumbnail_key = thumbnail_key
            segment.description_text = caption
            segment.tags = tags
            segment.event_type = str(event_type)[:128] if event_type else None
            segment.risk_score = risk_score
            segment.semantic_metadata = semantics.model_dump(mode="json")
            db.commit()

            milvus_rows.append(
                {
                    "segment_id": str(segment.id),
                    "asset_id": str(asset.id),
                    "storage_key": segment.storage_key,
                    "multimodal_embedding": vector,
                    "description_text": caption,
                    "start_time": float(segment.start_time),
                    "end_time": float(segment.end_time),
                    "duration": float(segment.end_time - segment.start_time),
                    "risk_score": risk_score,
                    "created_at_epoch": int(segment.created_at.timestamp()),
                    "trigger_type": segment.trigger_type,
                    "event_type": segment.event_type or "",
                    "tags": tags,
                    "semantic_metadata": segment.semantic_metadata,
                    "license_name": asset.license_name,
                    "source_url": asset.source_url,
                    "embedding_model": self.settings.embedding_model,
                    "embedding_dimension": self.settings.embedding_dimension,
                }
            )
            jobs.update_progress(job, 0.1 + 0.85 * ((index + 1) / len(boundaries)))
            jobs.checkpoint(
                job,
                "segments_analyzed",
                {"completed": index + 1, "total": len(boundaries)},
            )

        stale_segments = db.scalars(
            select(Segment).where(
                Segment.asset_id == asset.id,
                Segment.id.not_in(current_segment_ids),
            )
        ).all()
        for stale in stale_segments:
            self.object_store.delete_key(stale.storage_key)
            if stale.thumbnail_key:
                self.object_store.delete_key(stale.thumbnail_key)
            db.delete(stale)
        db.commit()
        self.milvus.delete_asset(str(asset.id))
        for row in milvus_rows:
            self.milvus.upsert(row)
        jobs.checkpoint(job, "index_committed", {"segment_count": len(milvus_rows)})

        asset.status = AssetStatus.READY
        asset.error = None
        db.commit()
        return {
            "asset_id": str(asset.id),
            "segment_count": len(boundaries),
            "duration_seconds": metadata.duration,
        }

    def render(self, job: Job, jobs: JobRepository) -> dict[str, Any]:
        db = jobs.db
        session_id = UUID(str(job.payload["session_id"]))
        version_number = int(job.payload["version"])
        if db.get(EditingSession, session_id) is None:
            raise LookupError("editing session no longer exists")
        version = db.scalar(
            select(StateVersion).where(
                StateVersion.session_id == session_id, StateVersion.version == version_number
            )
        )
        if version is None:
            raise LookupError("state version no longer exists")
        jobs.checkpoint(
            job,
            "state_loaded",
            {"session_id": str(session_id), "state_version": version_number},
        )
        profile_payload = dict(job.payload.get("render_profile") or {})
        profile = RenderProfile(**profile_payload)
        job_dir = Path(self.settings.runtime_dir) / "jobs" / str(job.id)
        source_dir = job_dir / "sources"
        sources: MaterializedSources = {}
        project = EditingProjectV2.model_validate(version.document)
        used_ids = {
            segment.source_id
            for track in project.timeline.tracks
            for segment in track.segments
            if hasattr(segment, "source_id")
        }
        source_registry = {item.source_id: item for item in project.sources}
        for index, source_id in enumerate(sorted(used_ids)):
            try:
                source_ref = source_registry[source_id]
            except KeyError as exc:
                raise LookupError(f"timeline source is not registered: {source_id}") from exc
            storage_key = source_ref.storage_key
            source = source_dir / f"{_safe_runtime_name(source_id)}.media"
            if not source.exists():
                self._download_render_source(storage_key, source)
            sources[source_id] = fingerprint_media(
                source,
                media_id=source_id,
                storage_key=storage_key,
                retention_class=source_ref.retention_class,
            )
            jobs.update_progress(job, 0.08 + 0.17 * ((index + 1) / max(1, len(used_ids))))
        jobs.checkpoint(job, "sources_fingerprinted", {"source_count": len(sources)})

        timeline = TimelineCompilerV2(profile).compile(
            session_id=session_id,
            state_version=version_number,
            project=project,
            sources=sources,
        )
        jobs.checkpoint(
            job,
            "timeline_compiled",
            {"compiled_hash": timeline.compiled_hash, "frame_count": timeline.frame_count},
        )
        verify_compiled_timeline(timeline)
        jobs.checkpoint(job, "compiled_verified")

        build_root = job_dir / "build"
        if build_root.exists():
            build = verify_render_build(build_root)
            if build.timeline.compiled_hash != timeline.compiled_hash:
                raise BuildVerificationError(
                    "existing render build belongs to different compiled input"
                )
            if self.capabilities is None:
                raise RuntimeError("renderer capability profile is unavailable")
            if build.manifest.renderer_capability_hash != content_hash(self.capabilities):
                raise BuildVerificationError(
                    "existing render build belongs to a different renderer capability profile"
                )
        else:
            if self.capabilities is None:
                raise RuntimeError("renderer capability profile is unavailable")
            build = RenderBuildService().create(
                build_root, timeline=timeline, profile=profile, capability=self.capabilities
            )
        jobs.checkpoint(job, "build_created", {"build_hash": build.manifest.build_instance_hash})
        build = verify_render_build(build.root)
        jobs.checkpoint(job, "build_verified", {"build_hash": build.manifest.build_instance_hash})

        output = job_dir / "camcat-render.mp4"
        jobs.checkpoint(job, "render_started")
        FFmpegRenderer().render(build, sources, output)
        jobs.checkpoint(job, "encoded", {"output_bytes": output.stat().st_size})
        try:
            verification = verify_output(build, output)
        except Exception as exc:
            (job_dir / "verification-result.json").write_text(
                json.dumps(
                    {"status": "failed", "error": sanitize_job_error(exc)},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            raise
        (job_dir / "verification-result.json").write_text(
            verification.model_dump_json(indent=2), encoding="utf-8"
        )
        jobs.checkpoint(
            job,
            "decode_verified",
            {
                "expected_frames": verification.expected_frames,
                "actual_frames": verification.actual_frames,
                "frame_delta": verification.frame_delta,
                "duration_delta_seconds": verification.duration_delta_seconds,
            },
        )
        output_key = f"renders/{session_id}/v{version_number}/{job.id}.mp4"
        self.object_store.upload_file(output, output_key, "video/mp4")
        subtitle_key = None
        subtitles_path = build.root / "captions.ass"
        if subtitles_path.is_file():
            subtitle_key = f"renders/{session_id}/v{version_number}/{job.id}.ass"
            self.object_store.upload_file(subtitles_path, subtitle_key, "text/x-ssa")
        build_prefix = f"renders/{session_id}/v{version_number}/{job.id}/build"
        build_keys: dict[str, str] = {}
        for filename, content_type in (
            ("compiled-timeline.json", "application/json"),
            ("source-manifest.json", "application/json"),
            ("render-profile.json", "application/json"),
            ("renderer-capability.json", "application/json"),
            ("build-manifest.json", "application/json"),
            ("captions.ass", "text/x-ssa"),
        ):
            if not (build.root / filename).is_file():
                continue
            key = f"{build_prefix}/{filename}"
            self.object_store.upload_file(build.root / filename, key, content_type)
            build_keys[filename] = key
        jobs.checkpoint(job, "artifact_uploaded", {"output_key": output_key})
        return {
            "session_id": str(session_id),
            "state_version": version_number,
            "state_hash": timeline.state_hash,
            "compiled_timeline_hash": timeline.compiled_hash,
            "render_build_input_digest": build.manifest.build_input_digest,
            "render_build_hash": build.manifest.build_instance_hash,
            "output_key": output_key,
            "subtitle_key": subtitle_key,
            "build_keys": build_keys,
            "duration_seconds": verification.duration_seconds,
            "width": verification.width,
            "height": verification.height,
            "file_size": verification.output_bytes,
            "output_sha256": verification.output_sha256,
            "verification_status": verification.status.value,
            "expected_frames": verification.expected_frames,
            "actual_frames": verification.actual_frames,
            "frame_delta": verification.frame_delta,
            "duration_delta_seconds": verification.duration_delta_seconds,
            "full_decode_succeeds": verification.full_decode_succeeds,
        }

    def _download_render_source(self, storage_key: str, target: Path) -> None:
        temporary = target.with_name(f"{target.name}.download")
        temporary.unlink(missing_ok=True)
        try:
            self.object_store.download_file(storage_key, temporary)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def stop(self, _signum: int, _frame: FrameType | None) -> None:
        self.running = False


def _transcription_cues(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = payload.get("segments") or payload.get("words") or []
    cues: list[dict[str, Any]] = []
    if not isinstance(raw_items, list):
        return cues
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        text_value = str(item.get("text") or item.get("word") or "").strip()
        try:
            start = float(item["start"])
            end = float(item["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if text_value and start >= 0 and end > start:
            cues.append({"text": text_value, "start": start, "end": end})
    return cues


def _temporary_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"storage_key", "thumbnail_key"} and isinstance(child, str):
                if child.startswith("temporary/"):
                    keys.add(child)
            else:
                keys.update(_temporary_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_temporary_keys(child))
    return keys


def _safe_runtime_name(value: str) -> str:
    return uuid5(NAMESPACE_URL, value).hex


class FailureCategory(StrEnum):
    RETRYABLE_INFRASTRUCTURE = "retryable_infrastructure_failure"
    DETERMINISTIC_VALIDATION = "deterministic_validation_failure"
    UNSUPPORTED_FEATURE = "unsupported_feature"
    ARTIFACT_DRIFT = "artifact_drift"
    OUTPUT_VERIFICATION = "output_verification_failure"


def _failure_category(error: Exception) -> FailureCategory:
    if isinstance(error, MediaFingerprintError):
        return FailureCategory.ARTIFACT_DRIFT
    if isinstance(error, OutputVerificationError):
        return FailureCategory.OUTPUT_VERIFICATION
    if isinstance(error, FFmpegRenderError):
        return FailureCategory.UNSUPPORTED_FEATURE
    if isinstance(
        error, (BuildVerificationError, TimelineValidationError, LookupError, ValueError)
    ):
        return FailureCategory.DETERMINISTIC_VALIDATION
    return FailureCategory.RETRYABLE_INFRASTRUCTURE


def main() -> None:
    worker = Worker()
    signal.signal(signal.SIGTERM, worker.stop)
    signal.signal(signal.SIGINT, worker.stop)
    worker.run()


if __name__ == "__main__":
    main()
