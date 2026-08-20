from __future__ import annotations

from pathlib import Path
from uuid import UUID

import camcat.rendering.fingerprint as fingerprint_module
import pytest
from camcat.rendering.build import BuildVerificationError, RenderBuildService, verify_render_build
from camcat.timeline.compiler import TimelineCompiler
from camcat.timeline.schemas import MediaFingerprint, RenderProfile


def source(path: Path, *, sha256: str, media_id: str = "source") -> MediaFingerprint:
    return MediaFingerprint(
        media_id=media_id,
        storage_key=f"temporary/{media_id}.mp4",
        local_path=str(path),
        sha256=sha256,
        file_size=path.stat().st_size,
        duration_us=2_000_000,
        width=640,
        height=360,
        video_codec="h264",
        audio_codec=None,
    )


@pytest.fixture(autouse=True)
def fake_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fingerprint_module,
        "probe_json",
        lambda _path: {"format": {"duration": "2.0"}},
    )


def make_timeline(path: Path, sha256: str):
    profile = RenderProfile(width=640, height=360, fps_num=30)
    fingerprint = source(path, sha256=sha256)
    timeline = TimelineCompiler(profile).compile(
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        state_version=3,
        document={
            "clips": [
                {
                    "clip_id": "clip-1",
                    "segment_id": "segment-1",
                    "origin": "source",
                    "media_id": "source",
                    "source_start": 0,
                    "source_end": 1,
                    "transition": "cut",
                }
            ],
            "subtitles": [
                {
                    "subtitle_id": "s1",
                    "text": "hello",
                    "clip_id": "clip-1",
                    "source_id": "source",
                    "source_start": 0,
                    "source_end": 1,
                }
            ],
            "audio_plan": {"bgm": [], "ambient": [], "sound_effects": []},
        },
        sources={"source": fingerprint},
    )
    return profile, timeline


def test_render_build_is_content_bound_and_verifiable(tmp_path: Path) -> None:
    media = tmp_path / "source.mp4"
    media.write_bytes(b"unchanged-media")
    import hashlib

    profile, timeline = make_timeline(media, hashlib.sha256(media.read_bytes()).hexdigest())
    build = RenderBuildService(renderer_version="test-renderer/v1").create(
        tmp_path / "build", timeline=timeline, profile=profile
    )

    verified = verify_render_build(build.root)
    assert verified.manifest.compiled_timeline_hash == timeline.compiled_hash
    assert verified.manifest.state_version == 3
    assert (build.root / "compiled-timeline.json").is_file()
    assert (build.root / "source-manifest.json").is_file()
    assert (build.root / "render-profile.json").is_file()
    assert (build.root / "subtitles.srt").is_file()


def test_modified_source_fails_build_verification(tmp_path: Path) -> None:
    media = tmp_path / "source.mp4"
    media.write_bytes(b"before")
    import hashlib

    profile, timeline = make_timeline(media, hashlib.sha256(media.read_bytes()).hexdigest())
    build = RenderBuildService(renderer_version="test-renderer/v1").create(
        tmp_path / "build", timeline=timeline, profile=profile
    )
    media.write_bytes(b"after")

    with pytest.raises(BuildVerificationError, match="source fingerprint"):
        verify_render_build(build.root)


def test_modified_compiled_timeline_fails_manifest_verification(tmp_path: Path) -> None:
    media = tmp_path / "source.mp4"
    media.write_bytes(b"source")
    import hashlib

    profile, timeline = make_timeline(media, hashlib.sha256(media.read_bytes()).hexdigest())
    build = RenderBuildService(renderer_version="test-renderer/v1").create(
        tmp_path / "build", timeline=timeline, profile=profile
    )
    compiled = build.root / "compiled-timeline.json"
    compiled.write_text(compiled.read_text().replace("hello", "tampered"), encoding="utf-8")

    with pytest.raises(BuildVerificationError, match="build file manifest"):
        verify_render_build(build.root)
