from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

import camcat.rendering.fingerprint as fingerprint_module
import pytest
from camcat.rendering.build import RenderBuildService
from camcat.rendering.jianying_adapter import (
    JianyingAdapterError,
    JianyingAudioTrack,
    JianyingRendererAdapter,
    JianyingTextTrack,
)
from camcat.timeline.compiler import TimelineCompiler
from camcat.timeline.schemas import MediaFingerprint, RenderProfile


def _source(
    path: Path,
    source_id: str,
    *,
    duration_us: int,
    video_codec: str | None,
    audio_codec: str | None,
) -> MediaFingerprint:
    return MediaFingerprint(
        media_id=source_id,
        storage_key=f"test/{path.name}",
        local_path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        file_size=path.stat().st_size,
        duration_us=duration_us,
        width=640 if video_codec else 0,
        height=360 if video_codec else 0,
        video_codec=video_codec,
        audio_codec=audio_codec,
    )


def _build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, fps: int = 30, dissolve_ms: int = 400
):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    music = tmp_path / "music.m4a"
    first.write_bytes(b"first-video")
    second.write_bytes(b"second-video")
    music.write_bytes(b"music")
    durations = {first.resolve(): 10.0, second.resolve(): 10.0, music.resolve(): 1.0}
    monkeypatch.setattr(
        fingerprint_module,
        "probe_json",
        lambda path: {"format": {"duration": str(durations[Path(path).resolve()])}},
    )
    sources = {
        "first": _source(
            first, "first", duration_us=10_000_000, video_codec="h264", audio_codec="aac"
        ),
        "second": _source(
            second,
            "second",
            duration_us=10_000_000,
            video_codec="h264",
            audio_codec="aac",
        ),
        "music": _source(
            music, "music", duration_us=1_000_000, video_codec=None, audio_codec="aac"
        ),
    }
    profile = RenderProfile(
        width=640,
        height=360,
        fps_num=fps,
        default_dissolve_duration_ms=dissolve_ms,
    )
    timeline = TimelineCompiler(profile).compile(
        session_id=UUID("00000000-0000-0000-0000-000000000001"),
        state_version=2,
        document={
            "clips": [
                {
                    "clip_id": "first-clip",
                    "segment_id": "first-segment",
                    "origin": "source",
                    "media_id": "first",
                    "source_start": 1,
                    "source_end": 3,
                    "transition": "dissolve",
                },
                {
                    "clip_id": "second-clip",
                    "segment_id": "second-segment",
                    "origin": "source",
                    "media_id": "second",
                    "source_start": 1,
                    "source_end": 3,
                    "transition": "cut",
                },
            ],
            "subtitles": [
                {
                    "subtitle_id": "subtitle",
                    "text": "editable",
                    "clip_id": "first-clip",
                    "source_id": "first",
                    "source_start": 1.2,
                    "source_end": 1.8,
                }
            ],
            "audio_plan": {
                "bgm": [
                    {
                        "cue_id": "music-cue",
                        "media_id": "music",
                        "target_start": 0,
                        "target_duration": 3.6,
                        "volume": 0.2,
                        "fade_in_frames": 6,
                        "fade_out_frames": 6,
                        "loop": True,
                    }
                ],
                "ambient": [],
                "sound_effects": [],
            },
        },
        sources=sources,
    )
    return RenderBuildService(renderer_version="test/v1").create(
        tmp_path / "build", timeline=timeline, profile=profile
    )


def test_adapter_maps_compiled_overlap_subtitles_and_looped_audio_to_editable_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = _build(tmp_path, monkeypatch)

    plan = JianyingRendererAdapter(("native-draft-tool",)).compile_plan(
        build, name="CamCat Editable"
    )

    main = plan.tracks[0]
    assert main.segments[0].duration_us == 2_000_000
    assert main.segments[0].transition_out is not None
    assert main.segments[0].transition_out.duration_us == 400_000
    assert main.segments[1].start_us == 2_000_000
    assert main.segments[1].duration_us == 1_600_000
    assert main.segments[1].source_start_us == 1_400_000
    assert any(isinstance(track, JianyingTextTrack) for track in plan.tracks)
    audio = next(track for track in plan.tracks if isinstance(track, JianyingAudioTrack))
    assert len(audio.segments) == 4
    assert audio.segments[0].keyframes is not None
    assert audio.segments[-1].keyframes is not None
    assert sum(item.duration_us for item in audio.segments) == 3_600_000


def test_adapter_fails_closed_for_native_incompatible_odd_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    build = _build(tmp_path, monkeypatch, fps=25, dissolve_ms=200)

    with pytest.raises(JianyingAdapterError, match="even number"):
        JianyingRendererAdapter(("native-draft-tool",)).compile_plan(build, name="Odd transition")
