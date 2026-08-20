from __future__ import annotations

from uuid import UUID

import pytest
from camcat.timeline.compiler import TimelineCompiler
from camcat.timeline.mapping import ProjectionPolicy, SourceTimeMapper
from camcat.timeline.schemas import MediaFingerprint, RenderProfile
from camcat.timeline.validator import TimelineValidationError, verify_compiled_timeline

SESSION_ID = UUID("00000000-0000-0000-0000-000000000001")


def fingerprint(source_id: str, *, duration_us: int = 10_000_000) -> MediaFingerprint:
    return MediaFingerprint(
        media_id=source_id,
        storage_key=f"sources/{source_id}.mp4",
        local_path=f"/tmp/{source_id}.mp4",
        sha256="a" * 64,
        file_size=100,
        duration_us=duration_us,
        width=1920,
        height=1080,
        video_codec="h264",
        audio_codec="aac",
    )


def document(*clips: dict[str, object]) -> dict[str, object]:
    return {
        "clips": list(clips),
        "subtitles": [],
        "audio_plan": {"bgm": [], "ambient": [], "sound_effects": []},
    }


def clip(
    clip_id: str,
    source_id: str,
    start: float,
    end: float,
    **extra: object,
) -> dict[str, object]:
    return {
        "clip_id": clip_id,
        "segment_id": f"segment-{clip_id}",
        "origin": "source",
        "media_id": source_id,
        "source_start": start,
        "source_end": end,
        "reason": "test",
        "transition": "cut",
        **extra,
    }


def test_single_and_multi_clip_are_frame_aligned_and_deterministic() -> None:
    profile = RenderProfile(width=1920, height=1080, fps_num=30, fps_den=1)
    state = document(clip("a", "one", 0.0, 1.01), clip("b", "two", 2.0, 3.0))
    compiler = TimelineCompiler(profile)

    first = compiler.compile(
        session_id=SESSION_ID,
        state_version=4,
        document=state,
        sources={"one": fingerprint("one"), "two": fingerprint("two")},
    )
    second = compiler.compile(
        session_id=SESSION_ID,
        state_version=4,
        document=state,
        sources={"one": fingerprint("one"), "two": fingerprint("two")},
    )

    segments = first.video_tracks[0].segments
    assert [(item.target_start_frame, item.target_duration_frames) for item in segments] == [
        (0, 30),
        (30, 30),
    ]
    assert first.frame_count == 60
    assert first.duration_us == 2_000_000
    assert first.compiled_hash == second.compiled_hash
    verify_compiled_timeline(first)


def test_speed_changes_target_frame_duration() -> None:
    timeline = TimelineCompiler(RenderProfile(width=1280, height=720, fps_num=25)).compile(
        session_id=SESSION_ID,
        state_version=1,
        document=document(clip("a", "one", 1.0, 5.0, speed=2.0)),
        sources={"one": fingerprint("one")},
    )
    segment = timeline.video_tracks[0].segments[0]
    assert segment.source_start_us == 1_000_000
    assert segment.source_duration_us == 4_000_000
    assert segment.target_duration_frames == 50
    assert timeline.duration_us == 2_000_000


def test_source_subtitle_and_audio_cue_project_after_trim_and_reorder() -> None:
    state = document(clip("b", "two", 5.0, 7.0), clip("a", "one", 1.0, 3.0))
    state["subtitles"] = [
        {
            "subtitle_id": "s1",
            "text": "mapped",
            "clip_id": "a",
            "source_id": "one",
            "source_start": 1.5,
            "source_end": 2.0,
            "style": "default",
        }
    ]
    state["audio_plan"] = {
        "bgm": [],
        "ambient": [],
        "sound_effects": [
            {
                "cue_id": "fx1",
                "media_id": "fx",
                "source_time": 1.25,
                "timeline_source_id": "one",
                "duration": 0.25,
                "volume": 0.5,
            }
        ],
    }
    timeline = TimelineCompiler(RenderProfile(width=1280, height=720, fps_num=30)).compile(
        session_id=SESSION_ID,
        state_version=1,
        document=state,
        sources={
            "one": fingerprint("one"),
            "two": fingerprint("two"),
            "fx": fingerprint("fx", duration_us=1_000_000),
        },
    )
    assert (timeline.subtitles[0].target_start_frame, timeline.subtitles[0].target_end_frame) == (
        75,
        90,
    )
    cue = next(track.cues[0] for track in timeline.audio_tracks if track.kind == "sfx")
    assert cue.target_start_frame == 68
    assert cue.target_duration_frames == 8


def test_projection_rejects_deleted_source_range_unless_snap_is_explicit() -> None:
    mapper = SourceTimeMapper.from_segments(
        TimelineCompiler(RenderProfile(width=640, height=360, fps_num=30))
        .compile(
            session_id=SESSION_ID,
            state_version=1,
            document=document(clip("a", "one", 2.0, 4.0)),
            sources={"one": fingerprint("one")},
        )
        .video_tracks[0]
        .segments,
        fps_num=30,
        fps_den=1,
    )
    with pytest.raises(TimelineValidationError, match="deleted source range"):
        mapper.project("one", 1_000_000)
    assert mapper.project("one", 1_000_000, ProjectionPolicy.SNAP_NEXT) == 0


def test_protected_range_cannot_be_removed_by_frame_alignment() -> None:
    state = document(
        clip(
            "a",
            "one",
            0.0,
            0.051,
            protected_ranges=[
                {
                    "start_us": 0,
                    "end_us": 51_000,
                    "reason": "protected_speech",
                    "evidence": {"text": "word", "asr_confidence": 0.9},
                }
            ],
        )
    )
    with pytest.raises(TimelineValidationError, match="protected"):
        TimelineCompiler(RenderProfile(width=640, height=360, fps_num=30)).compile(
            session_id=SESSION_ID,
            state_version=1,
            document=state,
            sources={"one": fingerprint("one")},
        )


def test_dissolve_creates_real_overlap_and_reduces_final_duration() -> None:
    state = document(
        clip(
            "a",
            "one",
            1.0,
            3.0,
            transition="dissolve",
        ),
        clip("b", "two", 1.0, 3.0),
    )
    timeline = TimelineCompiler(
        RenderProfile(width=1280, height=720, fps_num=30, default_dissolve_duration_ms=400)
    ).compile(
        session_id=SESSION_ID,
        state_version=1,
        document=state,
        sources={"one": fingerprint("one"), "two": fingerprint("two")},
    )
    first, second = timeline.video_tracks[0].segments
    assert first.transition_out.duration_frames == 12
    assert second.transition_in.duration_frames == 12
    assert second.target_start_frame == 48
    assert timeline.frame_count == 108


def test_dissolve_rejects_missing_source_handles() -> None:
    state = document(
        clip(
            "a",
            "one",
            0.0,
            2.0,
            transition="dissolve",
        ),
        clip("b", "two", 0.0, 2.0),
    )
    with pytest.raises(TimelineValidationError, match="handle"):
        TimelineCompiler(
            RenderProfile(width=1280, height=720, fps_num=30, default_dissolve_duration_ms=400)
        ).compile(
            session_id=SESSION_ID,
            state_version=1,
            document=state,
            sources={"one": fingerprint("one"), "two": fingerprint("two")},
        )


def test_source_range_out_of_bounds_is_rejected() -> None:
    with pytest.raises(TimelineValidationError, match="source range"):
        TimelineCompiler(RenderProfile(width=640, height=360, fps_num=60)).compile(
            session_id=SESSION_ID,
            state_version=1,
            document=document(clip("a", "one", 9.0, 11.0)),
            sources={"one": fingerprint("one")},
        )


def test_subtitle_requires_source_binding_instead_of_target_timestamps() -> None:
    state = document(clip("a", "one", 0.0, 2.0))
    state["subtitles"] = [
        {"subtitle_id": "legacy", "text": "target-bound", "start": 0.1, "end": 0.5}
    ]

    with pytest.raises(TimelineValidationError, match="source-bound"):
        TimelineCompiler(RenderProfile(width=640, height=360, fps_num=30)).compile(
            session_id=SESSION_ID,
            state_version=1,
            document=state,
            sources={"one": fingerprint("one")},
        )


def test_compiled_hash_does_not_depend_on_job_local_source_path() -> None:
    profile = RenderProfile(width=640, height=360, fps_num=30)
    state = document(clip("a", "one", 0.0, 2.0))
    first_source = fingerprint("one").model_copy(update={"local_path": "/runtime/jobs/a/source"})
    second_source = first_source.model_copy(update={"local_path": "/runtime/jobs/b/source"})

    first = TimelineCompiler(profile).compile(
        session_id=SESSION_ID,
        state_version=1,
        document=state,
        sources={"one": first_source},
    )
    second = TimelineCompiler(profile).compile(
        session_id=SESSION_ID,
        state_version=1,
        document=state,
        sources={"one": second_source},
    )

    assert first.source_manifest_hash == second.source_manifest_hash
    assert first.compiled_hash == second.compiled_hash
