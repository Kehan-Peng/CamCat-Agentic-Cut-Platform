from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Canvas(StrictModel):
    width: int = Field(ge=16, le=7680)
    height: int = Field(ge=16, le=7680)
    fps_num: int = Field(gt=0, le=60_000)
    fps_den: int = Field(gt=0, le=1001)

    @model_validator(mode="after")
    def supported_rate(self) -> Canvas:
        if (self.fps_num, self.fps_den) not in {
            (24, 1),
            (25, 1),
            (30, 1),
            (30_000, 1001),
            (50, 1),
            (60, 1),
            (60_000, 1001),
        }:
            raise ValueError("unsupported timeline frame rate")
        return self


class MediaSourceRef(StrictModel):
    source_id: str = Field(min_length=1)
    origin: Literal["user_upload", "licensed_library"]
    storage_key: str = Field(min_length=1)
    retention_class: Literal["transient_4h", "library"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class Transform(StrictModel):
    x: float = 0.0
    y: float = 0.0
    scale_x: float = Field(default=1.0, gt=0)
    scale_y: float = Field(default=1.0, gt=0)
    rotation: float = 0.0
    opacity: float = Field(default=1.0, ge=0, le=1)


class TextStyle(StrictModel):
    font_family: str | None = None
    local_font_ref: str | None = None
    size: int = Field(default=42, gt=0, le=500)
    x: float = 0.5
    y: float = 0.88
    color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")
    border_color: str = Field(default="#000000", pattern=r"^#[0-9A-Fa-f]{6}$")
    border_width: float = Field(default=2.0, ge=0, le=50)


class EvidenceRef(StrictModel):
    evidence_id: str | None = None
    kind: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoSegment(StrictModel):
    type: Literal["video"] = "video"
    segment_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    timeline_start_us: int = Field(ge=0)
    timeline_duration_us: int = Field(gt=0)
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)
    speed: float = Field(default=1.0, ge=0.1, le=8.0)
    transform: Transform = Field(default_factory=Transform)
    reason: str = ""
    evidence: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def duration_matches_speed(self) -> VideoSegment:
        expected = round(self.source_duration_us / self.speed)
        if abs(expected - self.timeline_duration_us) > 1:
            raise ValueError("video source and timeline durations disagree with speed")
        return self


class TextSegment(StrictModel):
    type: Literal["text"] = "text"
    segment_id: str = Field(min_length=1)
    start_us: int = Field(ge=0)
    duration_us: int = Field(gt=0)
    text: str = Field(min_length=1)
    style: TextStyle = Field(default_factory=TextStyle)


class AudioSegment(StrictModel):
    type: Literal["audio"] = "audio"
    segment_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    timeline_start_us: int = Field(ge=0)
    timeline_duration_us: int = Field(gt=0)
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)
    volume: float = Field(default=1.0, ge=0, le=4)
    fade_in_us: int = Field(default=0, ge=0)
    fade_out_us: int = Field(default=0, ge=0)
    loop: bool = False

    @model_validator(mode="after")
    def valid_fades(self) -> AudioSegment:
        if self.fade_in_us + self.fade_out_us > self.timeline_duration_us:
            raise ValueError("audio fades exceed segment duration")
        if not self.loop and self.source_duration_us < self.timeline_duration_us:
            raise ValueError("non-looping audio source is shorter than its timeline segment")
        return self


TimelineSegment = Annotated[VideoSegment | TextSegment | AudioSegment, Field(discriminator="type")]


class VideoTrack(StrictModel):
    type: Literal["video"] = "video"
    track_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    segments: list[VideoSegment] = Field(default_factory=list)


class TextTrack(StrictModel):
    type: Literal["text"] = "text"
    track_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    segments: list[TextSegment] = Field(default_factory=list)


class AudioTrack(StrictModel):
    type: Literal["audio"] = "audio"
    track_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role: Literal["dialogue", "bgm", "ambient", "sfx"]
    segments: list[AudioSegment] = Field(default_factory=list)


Track = Annotated[VideoTrack | TextTrack | AudioTrack, Field(discriminator="type")]


class TransitionEdge(StrictModel):
    transition_id: str = Field(min_length=1)
    left_segment_id: str = Field(min_length=1)
    right_segment_id: str = Field(min_length=1)
    type: Literal["dissolve"]
    duration_us: int = Field(gt=0)


class TimelineV2(StrictModel):
    tracks: list[Track] = Field(default_factory=list)
    transitions: list[TransitionEdge] = Field(default_factory=list)


class SpeechEvidence(StrictModel):
    evidence_id: str = Field(min_length=1)
    decision: Literal["KEEP", "DELETE", "CHECK"]
    segment_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_start_us: int = Field(ge=0)
    source_end_us: int = Field(gt=0)
    text: str = ""
    reason: str = ""

    @model_validator(mode="after")
    def ordered(self) -> SpeechEvidence:
        if self.source_end_us <= self.source_start_us:
            raise ValueError("speech evidence range must be positive")
        return self


class SpeechReview(StrictModel):
    workflow: str = ""
    items: list[SpeechEvidence] = Field(default_factory=list)


class EditingProjectV2(StrictModel):
    schema_name: Literal["camcat-editing-project/v2"] = Field(
        default="camcat-editing-project/v2", alias="schema"
    )
    project_id: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    title: str = Field(min_length=1)
    canvas: Canvas
    sources: list[MediaSourceRef] = Field(default_factory=list)
    timeline: TimelineV2 = Field(default_factory=TimelineV2)
    speech_review: SpeechReview = Field(default_factory=SpeechReview)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_project(self) -> EditingProjectV2:
        source_ids = [item.source_id for item in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source_id must be globally unique")
        track_ids = [item.track_id for item in self.timeline.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("track_id must be globally unique")
        segments = [segment for track in self.timeline.tracks for segment in track.segments]
        segment_ids = [item.segment_id for item in segments]
        if len(segment_ids) != len(set(segment_ids)):
            raise ValueError("segment_id must be globally unique")
        source_set = set(source_ids)
        for segment in segments:
            if (
                isinstance(segment, (VideoSegment, AudioSegment))
                and segment.source_id not in source_set
            ):
                raise ValueError(f"segment source_id does not exist: {segment.source_id}")
        for track_index, track in enumerate(self.timeline.tracks):
            ordered = sorted(track.segments, key=_segment_start)
            if list(track.segments) != ordered:
                raise ValueError(f"track segments must be ordered: {track.track_id}")
            previous_end = 0
            for timeline_segment in track.segments:
                start = _segment_start(timeline_segment)
                if start < previous_end:
                    raise ValueError(f"unsupported overlap on track: {track.track_id}")
                if (
                    isinstance(track, VideoTrack)
                    and track_index == _first_video_index(self.timeline.tracks)
                    and start != previous_end
                ):
                    raise ValueError("primary video track must be continuous from zero")
                previous_end = start + _segment_duration(timeline_segment)
        by_segment = {item.segment_id: item for item in segments}
        transition_ids = [item.transition_id for item in self.timeline.transitions]
        if len(transition_ids) != len(set(transition_ids)):
            raise ValueError("transition_id must be unique")
        for edge in self.timeline.transitions:
            left = by_segment.get(edge.left_segment_id)
            right = by_segment.get(edge.right_segment_id)
            if not isinstance(left, VideoSegment) or not isinstance(right, VideoSegment):
                raise ValueError("transition must reference video segments")
            owner = next((track for track in self.timeline.tracks if left in track.segments), None)
            if not isinstance(owner, VideoTrack):
                raise ValueError("transition segment has no video track")
            left_index = owner.segments.index(left)
            if left_index + 1 >= len(owner.segments) or owner.segments[left_index + 1] != right:
                raise ValueError("transition must reference adjacent video segments")
            if edge.duration_us >= min(left.timeline_duration_us, right.timeline_duration_us):
                raise ValueError("transition duration exceeds adjacent segment")
        for item in self.speech_review.items:
            speech_segment = by_segment.get(item.segment_id)
            if (
                not isinstance(speech_segment, VideoSegment)
                or speech_segment.source_id != item.source_id
            ):
                raise ValueError("speech evidence must bind to its video segment and source")
            if not (
                speech_segment.source_start_us
                <= item.source_start_us
                < item.source_end_us
                <= speech_segment.source_start_us + speech_segment.source_duration_us
            ):
                raise ValueError("speech evidence range lies outside its segment")
        return self


def _segment_start(segment: TimelineSegment) -> int:
    return segment.start_us if isinstance(segment, TextSegment) else segment.timeline_start_us


def _segment_duration(segment: TimelineSegment) -> int:
    return segment.duration_us if isinstance(segment, TextSegment) else segment.timeline_duration_us


def _first_video_index(tracks: list[Track]) -> int:
    return next((index for index, item in enumerate(tracks) if isinstance(item, VideoTrack)), -1)
