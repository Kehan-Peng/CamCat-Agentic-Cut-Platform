from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class RenderProfile(StrictModel):
    schema_name: Literal["camcat-render-profile/v1"] = Field(
        default="camcat-render-profile/v1", alias="schema"
    )
    width: int = Field(ge=16, le=7680)
    height: int = Field(ge=16, le=7680)
    fps_num: int = Field(default=30, gt=0, le=120)
    fps_den: int = Field(default=1, gt=0, le=1001)
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_sample_rate: int = Field(default=48_000, ge=8_000, le=192_000)
    audio_channels: Literal[1, 2] = 2
    pixel_format: str = "yuv420p"
    crf: int = Field(default=20, ge=0, le=51)
    preset: str = "veryfast"
    burn_subtitles: bool = True
    default_dissolve_duration_ms: int = Field(default=400, ge=1, le=2_000)
    color_contrast: float = Field(default=1.035, ge=0.5, le=2)
    color_saturation: float = Field(default=1.06, ge=0, le=3)
    color_gamma: float = Field(default=1.01, ge=0.1, le=10)
    normalize_loudness: bool = True
    loudness_target_lufs: float = Field(default=-14, ge=-70, le=-5)
    loudness_true_peak_db: float = Field(default=-1.5, ge=-9, le=0)
    loudness_range_lu: float = Field(default=11, ge=1, le=50)
    subtitle_margin_v: int = Field(default=48, ge=0, le=1000)

    @model_validator(mode="after")
    def supported_frame_rate(self) -> RenderProfile:
        if (self.fps_num, self.fps_den) not in {
            (24, 1),
            (25, 1),
            (30, 1),
            (50, 1),
            (60, 1),
            (30_000, 1001),
            (60_000, 1001),
        }:
            raise ValueError("unsupported render frame rate")
        return self


class MediaFingerprint(StrictModel):
    schema_name: Literal["camcat-media-fingerprint/v1"] = Field(
        default="camcat-media-fingerprint/v1", alias="schema"
    )
    media_id: str = Field(min_length=1)
    storage_key: str = Field(min_length=1)
    local_path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    file_size: int = Field(gt=0)
    duration_us: int = Field(gt=0)
    width: int = Field(ge=0)
    height: int = Field(ge=0)
    video_codec: str | None = None
    audio_codec: str | None = None


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


class TransitionSpec(StrictModel):
    type: Literal["cut", "dissolve"] = "cut"
    duration_frames: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def valid_duration(self) -> TransitionSpec:
        if self.type == "cut" and self.duration_frames != 0:
            raise ValueError("cut transition duration must be zero")
        if self.type == "dissolve" and self.duration_frames <= 0:
            raise ValueError("dissolve transition needs positive frame duration")
        return self


class CompiledVideoSegment(StrictModel):
    clip_id: str
    segment_id: str
    origin: str
    source_id: str
    source_sha256: str
    source_start_us: int
    source_duration_us: int
    target_start_frame: int
    target_duration_frames: int
    speed: float = Field(default=1.0, ge=0.1, le=8.0)
    transition_in: TransitionSpec = Field(default_factory=TransitionSpec)
    transition_out: TransitionSpec = Field(default_factory=TransitionSpec)
    protected_ranges: list[ProtectedSourceRange] = Field(default_factory=list)
    reason: str = ""


class CompiledVideoTrack(StrictModel):
    track_id: str = "video-main"
    segments: list[CompiledVideoSegment]


class CompiledSubtitle(StrictModel):
    subtitle_id: str
    text: str = Field(min_length=1)
    target_start_frame: int = Field(ge=0)
    target_end_frame: int = Field(gt=0)
    style: dict[str, Any] | str = "default"


class CompiledAudioCue(StrictModel):
    cue_id: str
    kind: Literal["dialogue", "bgm", "ambient", "sfx"]
    source_id: str
    source_sha256: str
    source_start_us: int = Field(default=0, ge=0)
    target_start_frame: int = Field(ge=0)
    target_duration_frames: int = Field(gt=0)
    volume: float = Field(default=1.0, ge=0, le=4)
    fade_in_frames: int = Field(default=0, ge=0)
    fade_out_frames: int = Field(default=0, ge=0)
    loop: bool = False


class CompiledAudioTrack(StrictModel):
    track_id: str
    kind: Literal["dialogue", "bgm", "ambient", "sfx"]
    cues: list[CompiledAudioCue]


class CompiledTimeline(StrictModel):
    schema_name: Literal["camcat-compiled-timeline/v1"] = Field(
        default="camcat-compiled-timeline/v1", alias="schema"
    )
    session_id: UUID
    state_version: int = Field(ge=1)
    fps_num: int = Field(gt=0)
    fps_den: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_count: int = Field(gt=0)
    duration_us: int = Field(gt=0)
    video_tracks: list[CompiledVideoTrack]
    audio_tracks: list[CompiledAudioTrack] = Field(default_factory=list)
    subtitles: list[CompiledSubtitle] = Field(default_factory=list)
    source_manifest: list[MediaFingerprint]
    source_manifest_hash: str
    state_hash: str
    render_profile_hash: str
    compiled_hash: str
