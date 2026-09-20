from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

import pytest
from camcat.domain.project import (
    Canvas,
    EditingProjectV2,
    MediaSourceRef,
    TimelineV2,
    VideoSegment,
    VideoTrack,
)
from camcat.rendering.build import (
    BuildVerificationError,
    RenderBuildService,
    verify_materialized_sources,
)
from camcat.rendering.doctor import RendererCapabilityProfile
from camcat.rendering.materialization import MaterializedMedia
from camcat.timeline.compiler import TimelineCompilerV2
from camcat.timeline.schemas import BuildMediaRef, RenderProfile


def _materialized(path: Path) -> MaterializedMedia:
    ref = BuildMediaRef(
        media_id="source",
        storage_key="library/source.mp4",
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        size=path.stat().st_size,
        duration_us=2_000_000,
        width=640,
        height=360,
        video_codec="h264",
        audio_codec="aac",
        retention_class="library",
    )
    return MaterializedMedia(ref=ref, local_path=path)


def _timeline(source: MaterializedMedia, profile: RenderProfile):
    project = EditingProjectV2(
        project_id="p",
        goal="g",
        title="t",
        canvas=Canvas(width=640, height=360, fps_num=30, fps_den=1),
        sources=[
            MediaSourceRef(
                source_id="source",
                origin="licensed_library",
                storage_key="library/source.mp4",
                retention_class="library",
            )
        ],
        timeline=TimelineV2(
            tracks=[
                VideoTrack(
                    track_id="main",
                    name="Main",
                    segments=[
                        VideoSegment(
                            segment_id="v1",
                            source_id="source",
                            timeline_start_us=0,
                            timeline_duration_us=1_000_000,
                            source_start_us=0,
                            source_duration_us=1_000_000,
                        )
                    ],
                )
            ]
        ),
    )
    return TimelineCompilerV2(profile).compile(
        session_id=UUID(int=1), state_version=1, project=project, sources={"source": source}
    )


def _capability(version: str = "v2") -> RendererCapabilityProfile:
    return RendererCapabilityProfile(
        ffmpeg_version="ffmpeg test",
        ffprobe_version="ffprobe test",
        encoders=["libx264", "aac"],
        filters=["ass", "overlay", "xfade", "eq", "loudnorm", "amix"],
        platform="test",
        renderer_implementation_version=version,
        runtime_directory_writable=True,
        object_store_reachable=True,
    )


def test_persistent_build_has_no_local_path_and_digest_is_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "source.mp4"
    path.write_bytes(b"media")
    source = _materialized(path)
    profile = RenderProfile()
    timeline = _timeline(source, profile)
    first = RenderBuildService().create(
        tmp_path / "one", timeline=timeline, profile=profile, capability=_capability()
    )
    second = RenderBuildService().create(
        tmp_path / "two", timeline=timeline, profile=profile, capability=_capability()
    )
    assert "local_path" not in (first.root / "source-manifest.json").read_text()
    assert first.manifest.build_input_digest == second.manifest.build_input_digest
    assert first.manifest.build_instance_hash != second.manifest.build_instance_hash


def test_source_change_fails_and_capability_changes_input_digest(tmp_path: Path) -> None:
    path = tmp_path / "source.mp4"
    path.write_bytes(b"media")
    source = _materialized(path)
    profile = RenderProfile()
    timeline = _timeline(source, profile)
    first = RenderBuildService().create(
        tmp_path / "one", timeline=timeline, profile=profile, capability=_capability()
    )
    second = RenderBuildService().create(
        tmp_path / "two", timeline=timeline, profile=profile, capability=_capability("v3")
    )
    assert first.manifest.build_input_digest != second.manifest.build_input_digest
    path.write_bytes(b"changed")
    with pytest.raises(BuildVerificationError, match="changed"):
        verify_materialized_sources(first, {"source": source})
