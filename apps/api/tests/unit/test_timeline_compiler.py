from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from camcat.domain.project import (
    AudioSegment,
    AudioTrack,
    Canvas,
    EditingProjectV2,
    MediaSourceRef,
    TextSegment,
    TextTrack,
    TimelineV2,
    Transform,
    TransitionEdge,
    VideoSegment,
    VideoTrack,
)
from camcat.rendering.materialization import MaterializedMedia
from camcat.timeline.compiler import TimelineCompilerV2
from camcat.timeline.mapping import SourceTimeMapper
from camcat.timeline.schemas import BuildMediaRef, RenderProfile
from camcat.timeline.validator import TimelineValidationError

SESSION = UUID("00000000-0000-0000-0000-000000000001")


def media(source_id: str, *, duration_us: int = 10_000_000, audio: bool = True):
    return MaterializedMedia(
        ref=BuildMediaRef(
            media_id=source_id,
            storage_key=f"library/{source_id}",
            sha256=(source_id[0] if source_id[0] in "abcdef" else "a") * 64,
            size=100,
            duration_us=duration_us,
            width=640,
            height=360,
            video_codec="h264" if source_id != "music" else None,
            audio_codec="aac" if audio else None,
            retention_class="library",
        ),
        local_path=Path(f"/tmp/{source_id}"),
    )


def project(*, fps_num: int = 30, fps_den: int = 1, transition: bool = False):
    edges = (
        [
            TransitionEdge(
                transition_id="edge",
                left_segment_id="v1",
                right_segment_id="v2",
                type="dissolve",
                duration_us=400_000,
            )
        ]
        if transition
        else []
    )
    return EditingProjectV2(
        project_id="p",
        goal="g",
        title="t",
        canvas=Canvas(width=640, height=360, fps_num=fps_num, fps_den=fps_den),
        sources=[
            MediaSourceRef(
                source_id="first",
                origin="licensed_library",
                storage_key="library/first",
                retention_class="library",
            ),
            MediaSourceRef(
                source_id="second",
                origin="licensed_library",
                storage_key="library/second",
                retention_class="library",
            ),
            MediaSourceRef(
                source_id="music",
                origin="licensed_library",
                storage_key="library/music",
                retention_class="library",
            ),
        ],
        timeline=TimelineV2(
            tracks=[
                VideoTrack(
                    track_id="main",
                    name="Main",
                    segments=[
                        VideoSegment(
                            segment_id="v1",
                            source_id="first",
                            timeline_start_us=0,
                            timeline_duration_us=2_000_000,
                            source_start_us=1_000_000,
                            source_duration_us=2_000_000,
                        ),
                        VideoSegment(
                            segment_id="v2",
                            source_id="second",
                            timeline_start_us=2_000_000,
                            timeline_duration_us=2_000_000,
                            source_start_us=1_000_000,
                            source_duration_us=2_000_000,
                        ),
                    ],
                ),
                VideoTrack(
                    track_id="overlay",
                    name="Overlay",
                    segments=[
                        VideoSegment(
                            segment_id="ov1",
                            source_id="second",
                            timeline_start_us=1_000_000,
                            timeline_duration_us=1_000_000,
                            source_start_us=4_000_000,
                            source_duration_us=1_000_000,
                            transform=Transform(
                                x=0.2, y=-0.1, scale_x=0.4, scale_y=0.4, opacity=0.8
                            ),
                        )
                    ],
                ),
                TextTrack(
                    track_id="text",
                    name="Text",
                    segments=[
                        TextSegment(
                            segment_id="t1", start_us=500_000, duration_us=1_000_000, text="hello"
                        )
                    ],
                ),
                AudioTrack(
                    track_id="bgm",
                    name="BGM",
                    role="bgm",
                    segments=[
                        AudioSegment(
                            segment_id="a1",
                            source_id="music",
                            timeline_start_us=0,
                            timeline_duration_us=4_000_000,
                            source_start_us=0,
                            source_duration_us=4_000_000,
                            volume=0.1,
                        )
                    ],
                ),
            ],
            transitions=edges,
        ),
    )


def compile(value: EditingProjectV2):
    return TimelineCompilerV2(RenderProfile()).compile(
        session_id=SESSION,
        state_version=2,
        project=value,
        sources={"first": media("first"), "second": media("second"), "music": media("music")},
    )


@pytest.mark.parametrize(
    "fps_num,fps_den", [(24, 1), (25, 1), (30, 1), (30_000, 1001), (50, 1), (60, 1), (60_000, 1001)]
)
def test_frame_quantization_is_central_and_deterministic(fps_num: int, fps_den: int) -> None:
    first = compile(project(fps_num=fps_num, fps_den=fps_den))
    second = compile(project(fps_num=fps_num, fps_den=fps_den))
    assert first.frame_count == round(4 * fps_num / fps_den)
    assert first.compiled_hash == second.compiled_hash


def test_compiler_emits_multi_video_overlay_audio_and_text_tracks() -> None:
    timeline = compile(project())
    assert len(timeline.video_tracks) == 2
    assert timeline.video_tracks[1].segments[0].transform.opacity == 0.8
    assert timeline.audio_tracks[0].role == "bgm"
    assert timeline.text_tracks[0].segments[0].text == "hello"
    assert timeline.schema_name == "camcat-compiled-timeline/v2"


def test_speed_and_occurrence_bound_source_mapping() -> None:
    value = project()
    payload = value.model_dump(mode="json", by_alias=True)
    payload["timeline"]["tracks"][0]["segments"][0].update(
        timeline_duration_us=1_000_000, source_duration_us=2_000_000, speed=2
    )
    payload["timeline"]["tracks"][0]["segments"][1]["timeline_start_us"] = 1_000_000
    payload["timeline"]["tracks"][3]["segments"][0]["timeline_duration_us"] = 3_000_000
    payload["timeline"]["tracks"][3]["segments"][0]["source_duration_us"] = 3_000_000
    value = EditingProjectV2.model_validate(payload)
    timeline = compile(value)
    mapper = SourceTimeMapper.from_segments(
        [item for track in timeline.video_tracks for item in track.segments],
        fps_num=30,
        fps_den=1,
    )
    assert (
        mapper.project(
            track_id="main", segment_id="v1", source_id="first", source_time_us=2_000_000
        )
        == 15
    )
    assert (
        mapper.project(
            track_id="main",
            segment_id="v2",
            source_id="second",
            source_time_us=2_000_000,
        )
        == 60
    )
    assert (
        mapper.project(
            track_id="overlay",
            segment_id="ov1",
            source_id="second",
            source_time_us=4_500_000,
        )
        == 45
    )
    with pytest.raises(TimelineValidationError, match="exact"):
        mapper.project(
            track_id="main", segment_id="missing", source_id="first", source_time_us=2_000_000
        )


def test_dissolve_uses_render_handles_without_shortening_semantic_duration() -> None:
    timeline = compile(project(transition=True))
    left, right = timeline.video_tracks[0].segments
    assert timeline.frame_count == 120
    assert left.visible_source_duration_us == 2_000_000
    assert left.render_source_duration_us > left.visible_source_duration_us
    assert right.render_source_start_us < right.visible_source_start_us
    assert right.timeline_start_frame == 60
    assert timeline.transitions[0].duration_frames == 12


def test_insufficient_dissolve_handle_fails_closed() -> None:
    value = project(transition=True)
    payload = value.model_dump(mode="json", by_alias=True)
    payload["timeline"]["tracks"][0]["segments"][0]["source_start_us"] = 0
    payload["timeline"]["tracks"][0]["segments"][1]["source_start_us"] = 0
    with pytest.raises(TimelineValidationError, match="handles"):
        compile(EditingProjectV2.model_validate(payload))
