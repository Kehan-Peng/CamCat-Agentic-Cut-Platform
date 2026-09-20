from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from camcat.domain.project import Canvas, TextStyle, Transform


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class RenderProfile(StrictModel):
    schema_name: Literal["camcat-render-profile/v2"] = Field(
        default="camcat-render-profile/v2", alias="schema"
    )
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_sample_rate: int = Field(default=48_000, ge=8_000, le=192_000)
    audio_channels: Literal[1, 2] = 2
    pixel_format: str = "yuv420p"
    crf: int = Field(default=20, ge=0, le=51)
    preset: str = "veryfast"
    burn_subtitles: bool = True
    color_contrast: float = Field(default=1.035, ge=0.5, le=2)
    color_saturation: float = Field(default=1.06, ge=0, le=3)
    color_gamma: float = Field(default=1.01, ge=0.1, le=10)
    normalize_loudness: bool = True
    loudness_target_lufs: float = Field(default=-14, ge=-70, le=-5)
    loudness_true_peak_db: float = Field(default=-1.5, ge=-9, le=0)
    loudness_range_lu: float = Field(default=11, ge=1, le=50)


class BuildMediaRef(StrictModel):
    schema_name: Literal["camcat-build-media-ref/v2"] = Field(
        default="camcat-build-media-ref/v2", alias="schema"
    )
    media_id: str = Field(min_length=1)
    storage_key: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(gt=0)
    duration_us: int = Field(gt=0)
    width: int = Field(ge=0)
    height: int = Field(ge=0)
    video_codec: str | None = None
    audio_codec: str | None = None
    retention_class: Literal["transient_4h", "library"]


class ProtectedSourceRange(StrictModel):
    start_us: int = Field(ge=0)
    end_us: int = Field(gt=0)
    reason: str = Field(min_length=1)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ordered(self) -> ProtectedSourceRange:
        if self.end_us <= self.start_us:
            raise ValueError("protected range must have positive duration")
        return self


class CompiledVideoSegment(StrictModel):
    track_id: str
    segment_id: str
    source_id: str
    source_sha256: str
    visible_source_start_us: int = Field(ge=0)
    visible_source_duration_us: int = Field(gt=0)
    render_source_start_us: int = Field(ge=0)
    render_source_duration_us: int = Field(gt=0)
    timeline_start_frame: int = Field(ge=0)
    timeline_duration_frames: int = Field(gt=0)
    render_start_frame: int = Field(ge=0)
    render_duration_frames: int = Field(gt=0)
    speed: float = Field(default=1.0, ge=0.1, le=8.0)
    transform: Transform = Field(default_factory=Transform)
    reason: str = ""
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class CompiledVideoTrack(StrictModel):
    track_id: str
    name: str
    segments: list[CompiledVideoSegment]


class CompiledTextSegment(StrictModel):
    segment_id: str
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(gt=0)
    text: str = Field(min_length=1)
    style: TextStyle


class CompiledTextTrack(StrictModel):
    track_id: str
    name: str
    segments: list[CompiledTextSegment]


class CompiledAudioSegment(StrictModel):
    segment_id: str
    source_id: str
    source_sha256: str
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)
    timeline_start_frame: int = Field(ge=0)
    timeline_duration_frames: int = Field(gt=0)
    volume: float = Field(default=1.0, ge=0, le=4)
    fade_in_frames: int = Field(default=0, ge=0)
    fade_out_frames: int = Field(default=0, ge=0)
    loop: bool = False


class CompiledAudioTrack(StrictModel):
    track_id: str
    name: str
    role: Literal["dialogue", "bgm", "ambient", "sfx"]
    segments: list[CompiledAudioSegment]


class CompiledTransitionEdge(StrictModel):
    transition_id: str
    track_id: str
    left_segment_id: str
    right_segment_id: str
    type: Literal["dissolve"]
    duration_frames: int = Field(gt=0)


class CompiledTimelineV2(StrictModel):
    schema_name: Literal["camcat-compiled-timeline/v2"] = Field(
        default="camcat-compiled-timeline/v2", alias="schema"
    )
    session_id: UUID
    state_version: int = Field(ge=1)
    canvas: Canvas
    frame_count: int = Field(gt=0)
    duration_us: int = Field(gt=0)
    video_tracks: list[CompiledVideoTrack]
    audio_tracks: list[CompiledAudioTrack] = Field(default_factory=list)
    text_tracks: list[CompiledTextTrack] = Field(default_factory=list)
    transitions: list[CompiledTransitionEdge] = Field(default_factory=list)
    source_manifest: list[BuildMediaRef]
    source_manifest_hash: str
    state_hash: str
    render_profile_hash: str
    compiled_hash: str
