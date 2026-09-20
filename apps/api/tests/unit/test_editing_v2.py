from __future__ import annotations

from copy import deepcopy

import pytest
from camcat.domain.commands import (
    AddAudioSegment,
    AddTrack,
    InitializeEditingProject,
    InsertSegment,
    MoveSegment,
    RemoveAudioSegment,
    RemoveSegment,
    RemoveTrack,
    ReplaceSegmentMedia,
    SetSegmentTransform,
    SetTransition,
    SplitSegment,
    TrimSegment,
    UpdateTextSegment,
)
from camcat.domain.project import (
    AudioSegment,
    AudioTrack,
    Canvas,
    EditingProjectV2,
    MediaSourceRef,
    TextSegment,
    TextTrack,
    TimelineV2,
    VideoSegment,
    VideoTrack,
)
from camcat.domain.reducer import CommandConflict, reduce_commands
from camcat.domain.state_patch import (
    PatchConflict,
    VersionedState,
    apply_versioned_patch,
    build_rollback_patch,
)
from pydantic import TypeAdapter, ValidationError


def project() -> EditingProjectV2:
    return EditingProjectV2(
        project_id="project-1",
        goal="make a short film",
        title="Draft",
        canvas=Canvas(width=1280, height=720, fps_num=30, fps_den=1),
        sources=[
            MediaSourceRef(
                source_id="source-video",
                origin="user_upload",
                storage_key="temporary/video.mp4",
                retention_class="transient_4h",
            ),
            MediaSourceRef(
                source_id="source-replacement",
                origin="licensed_library",
                storage_key="library/replacement.mp4",
                retention_class="library",
            ),
            MediaSourceRef(
                source_id="source-audio",
                origin="licensed_library",
                storage_key="library/audio.m4a",
                retention_class="library",
            ),
        ],
        timeline=TimelineV2(
            tracks=[
                VideoTrack(
                    track_id="video-main",
                    name="Main",
                    segments=[
                        VideoSegment(
                            segment_id="v1",
                            source_id="source-video",
                            timeline_start_us=0,
                            timeline_duration_us=2_000_000,
                            source_start_us=1_000_000,
                            source_duration_us=2_000_000,
                            reason="opening",
                        ),
                        VideoSegment(
                            segment_id="v2",
                            source_id="source-video",
                            timeline_start_us=2_000_000,
                            timeline_duration_us=2_000_000,
                            source_start_us=4_000_000,
                            source_duration_us=2_000_000,
                            reason="ending",
                        ),
                    ],
                ),
                TextTrack(
                    track_id="text-main",
                    name="Captions",
                    segments=[
                        TextSegment(
                            segment_id="t1",
                            start_us=0,
                            duration_us=1_000_000,
                            text="hello",
                        )
                    ],
                ),
                AudioTrack(track_id="audio-bgm", name="Music", role="bgm", segments=[]),
            ]
        ),
    )


def apply(*commands):
    return reduce_commands(project(), list(commands)).project


def test_initialize_add_remove_track() -> None:
    initialized = reduce_commands(None, [InitializeEditingProject(project=project())]).project
    assert initialized.schema_name == "camcat-editing-project/v2"
    added = reduce_commands(
        initialized,
        [AddTrack(track=AudioTrack(track_id="audio-sfx", name="SFX", role="sfx"))],
    ).project
    assert [track.track_id for track in added.timeline.tracks][-1] == "audio-sfx"
    removed = reduce_commands(added, [RemoveTrack(track_id="audio-sfx")]).project
    assert all(track.track_id != "audio-sfx" for track in removed.timeline.tracks)


def test_insert_move_remove_segment_use_stable_anchors() -> None:
    inserted = apply(
        InsertSegment(
            track_id="video-main",
            before_segment_id="v2",
            segment=VideoSegment(
                segment_id="inserted",
                source_id="source-video",
                timeline_start_us=2_000_000,
                timeline_duration_us=500_000,
                source_start_us=3_000_000,
                source_duration_us=500_000,
            ),
        )
    )
    assert [s.segment_id for s in inserted.timeline.tracks[0].segments] == ["v1", "inserted", "v2"]
    moved = reduce_commands(
        inserted,
        [MoveSegment(track_id="video-main", segment_id="v2", before_segment_id="v1")],
    ).project
    assert [s.segment_id for s in moved.timeline.tracks[0].segments] == ["v2", "v1", "inserted"]
    removed = reduce_commands(
        moved,
        [RemoveSegment(track_id="video-main", segment_id="inserted")],
    ).project
    assert [s.segment_id for s in removed.timeline.tracks[0].segments] == ["v2", "v1"]


def test_trim_split_replace_transform_transition_and_text() -> None:
    result = apply(
        TrimSegment(segment_id="v1", source_start_us=1_250_000, source_duration_us=1_500_000),
        SplitSegment(segment_id="v2", at_source_us=5_000_000, right_segment_id="v2-right"),
        ReplaceSegmentMedia(
            segment_id="v2-right",
            source_id="source-replacement",
            source_start_us=0,
            source_duration_us=1_000_000,
        ),
        SetSegmentTransform(segment_id="v1", x=0.2, y=-0.1, scale_x=0.5, scale_y=0.5),
        UpdateTextSegment(segment_id="t1", text="updated", size=44),
        SetTransition(
            transition_id="transition-1",
            left_segment_id="v1",
            right_segment_id="v2",
            transition_type="dissolve",
            duration_us=400_000,
        ),
    )
    video = result.timeline.tracks[0]
    assert [(s.segment_id, s.timeline_duration_us) for s in video.segments] == [
        ("v1", 1_500_000),
        ("v2", 1_000_000),
        ("v2-right", 1_000_000),
    ]
    assert video.segments[2].source_id == "source-replacement"
    assert video.segments[0].transform.scale_x == 0.5
    assert result.timeline.tracks[1].segments[0].style.size == 44
    assert result.timeline.transitions[0].left_segment_id == "v1"


def test_add_and_remove_audio_segment() -> None:
    cue = AudioSegment(
        segment_id="a1",
        source_id="source-audio",
        timeline_start_us=0,
        timeline_duration_us=2_000_000,
        source_start_us=0,
        source_duration_us=2_000_000,
    )
    added = apply(AddAudioSegment(track_id="audio-bgm", segment=cue))
    assert added.timeline.tracks[2].segments[0].segment_id == "a1"
    removed = reduce_commands(
        added, [RemoveAudioSegment(track_id="audio-bgm", segment_id="a1")]
    ).project
    assert removed.timeline.tracks[2].segments == []


def test_split_rejects_unsafe_transition_inheritance() -> None:
    with_transition = apply(
        SetTransition(
            transition_id="transition-1",
            left_segment_id="v1",
            right_segment_id="v2",
            transition_type="dissolve",
            duration_us=400_000,
        )
    )
    with pytest.raises(CommandConflict, match="transition"):
        reduce_commands(
            with_transition,
            [SplitSegment(segment_id="v1", at_source_us=2_000_000, right_segment_id="new")],
        )


def test_project_invariants_are_strict_and_microseconds_only() -> None:
    payload = project().model_dump(mode="json", by_alias=True)
    payload["timeline"]["tracks"][1]["segments"][0]["segment_id"] = "v1"
    with pytest.raises(ValidationError, match="segment_id"):
        EditingProjectV2.model_validate(payload)

    payload = project().model_dump(mode="json", by_alias=True)
    payload["timeline"]["tracks"][0]["segments"][0]["source_id"] = "missing"
    with pytest.raises(ValidationError, match="source_id"):
        EditingProjectV2.model_validate(payload)

    payload = project().model_dump(mode="json", by_alias=True)
    payload["timeline"]["tracks"][0]["segments"][0]["timeline_start_us"] = -1
    with pytest.raises(ValidationError):
        EditingProjectV2.model_validate(payload)

    encoded = str(project().model_dump(mode="json"))
    assert "target_start" not in encoded
    assert "source_start':" not in encoded


def test_commands_are_typed_discriminated_models() -> None:
    from camcat.domain.commands import DomainEditCommand

    command = TypeAdapter(DomainEditCommand).validate_python(
        {
            "type": "trim_segment",
            "segment_id": "v1",
            "source_start_us": 10,
            "source_duration_us": 20,
        }
    )
    assert isinstance(command, TrimSegment)
    with pytest.raises(ValidationError):
        TypeAdapter(DomainEditCommand).validate_python(
            {"type": "insert_segment", "track_id": "video-main", "segment": {"anything": 1}}
        )


def test_reducer_is_immutable_and_derives_deterministic_internal_patch() -> None:
    before = project()
    snapshot = deepcopy(before.model_dump(mode="json"))
    first = reduce_commands(
        before,
        [TrimSegment(segment_id="v1", source_start_us=1_100_000, source_duration_us=1_000_000)],
    )
    second = reduce_commands(
        before,
        [TrimSegment(segment_id="v1", source_start_us=1_100_000, source_duration_us=1_000_000)],
    )
    assert before.model_dump(mode="json") == snapshot
    assert first.operations == second.operations
    assert all(operation["path"].startswith("/timeline/") for operation in first.operations)


def test_stale_version_is_rejected_and_rollback_is_compensating() -> None:
    original = project().model_dump(mode="json", by_alias=True)
    reduction = reduce_commands(
        project(),
        [TrimSegment(segment_id="v1", source_start_us=1_100_000, source_duration_us=1_000_000)],
    )
    version_two, _ = apply_versioned_patch(
        VersionedState("session", 1, original),
        base_version=1,
        operations=reduction.operations,
        actor="tester",
        reason="trim",
    )
    with pytest.raises(PatchConflict):
        apply_versioned_patch(
            version_two,
            base_version=1,
            operations=reduction.operations,
            actor="tester",
            reason="stale",
        )
    rollback = build_rollback_patch(version_two.document, original)
    version_three, _ = apply_versioned_patch(
        version_two,
        base_version=2,
        operations=rollback,
        actor="tester",
        reason="rollback",
    )
    assert version_three.version == 3
    assert version_three.document == original
