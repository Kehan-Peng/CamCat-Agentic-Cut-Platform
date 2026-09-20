from __future__ import annotations

from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from camcat.domain.project import (
    AudioSegment,
    Canvas,
    EditingProjectV2,
    MediaSourceRef,
    TimelineSegment,
    Track,
)


class EditCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    command_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)


class InitializeEditingProject(EditCommand):
    type: Literal["initialize_editing_project"] = "initialize_editing_project"
    project: EditingProjectV2


class RegisterSource(EditCommand):
    type: Literal["register_source"] = "register_source"
    source: MediaSourceRef


class UpdateCanvas(EditCommand):
    type: Literal["update_canvas"] = "update_canvas"
    canvas: Canvas


class AddTrack(EditCommand):
    type: Literal["add_track"] = "add_track"
    track: Track
    before_track_id: str | None = None
    after_track_id: str | None = None

    @model_validator(mode="after")
    def one_anchor(self) -> AddTrack:
        if self.before_track_id is not None and self.after_track_id is not None:
            raise ValueError("add track accepts at most one stable anchor")
        return self


class RemoveTrack(EditCommand):
    type: Literal["remove_track"] = "remove_track"
    track_id: str


class RenameTrack(EditCommand):
    type: Literal["rename_track"] = "rename_track"
    track_id: str
    name: str = Field(min_length=1)


class InsertSegment(EditCommand):
    type: Literal["insert_segment"] = "insert_segment"
    track_id: str
    segment: TimelineSegment
    before_segment_id: str | None = None
    after_segment_id: str | None = None

    @model_validator(mode="after")
    def one_anchor(self) -> InsertSegment:
        if self.before_segment_id is not None and self.after_segment_id is not None:
            raise ValueError("insert segment accepts at most one stable anchor")
        return self


class RemoveSegment(EditCommand):
    type: Literal["remove_segment"] = "remove_segment"
    track_id: str
    segment_id: str


class MoveSegment(EditCommand):
    type: Literal["move_segment"] = "move_segment"
    track_id: str
    segment_id: str
    before_segment_id: str | None = None
    after_segment_id: str | None = None

    @model_validator(mode="after")
    def exactly_one_anchor(self) -> MoveSegment:
        if (self.before_segment_id is None) == (self.after_segment_id is None):
            raise ValueError("move segment needs exactly one stable anchor")
        if self.segment_id in {self.before_segment_id, self.after_segment_id}:
            raise ValueError("move segment cannot anchor to itself")
        return self


class TrimSegment(EditCommand):
    type: Literal["trim_segment"] = "trim_segment"
    segment_id: str
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)


class SplitSegment(EditCommand):
    type: Literal["split_segment"] = "split_segment"
    segment_id: str
    at_source_us: int = Field(gt=0)
    right_segment_id: str = Field(min_length=1)


class ReplaceSegmentMedia(EditCommand):
    type: Literal["replace_segment_media"] = "replace_segment_media"
    segment_id: str
    source_id: str
    source_start_us: int = Field(ge=0)
    source_duration_us: int = Field(gt=0)


class SetSegmentTransform(EditCommand):
    type: Literal["set_segment_transform"] = "set_segment_transform"
    segment_id: str
    x: float
    y: float
    scale_x: float = Field(gt=0)
    scale_y: float = Field(gt=0)
    rotation: float = 0
    opacity: float = Field(default=1, ge=0, le=1)


class UpdateTextSegment(EditCommand):
    type: Literal["update_text_segment"] = "update_text_segment"
    segment_id: str
    text: str | None = Field(default=None, min_length=1)
    start_us: int | None = Field(default=None, ge=0)
    duration_us: int | None = Field(default=None, gt=0)
    font_family: str | None = None
    local_font_ref: str | None = None
    size: int | None = Field(default=None, gt=0, le=500)
    x: float | None = None
    y: float | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    border_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    border_width: float | None = Field(default=None, ge=0, le=50)


class AddAudioSegment(EditCommand):
    type: Literal["add_audio_segment"] = "add_audio_segment"
    track_id: str
    segment: AudioSegment


class UpdateAudioSegment(EditCommand):
    type: Literal["update_audio_segment"] = "update_audio_segment"
    segment_id: str
    timeline_start_us: int | None = Field(default=None, ge=0)
    timeline_duration_us: int | None = Field(default=None, gt=0)
    source_start_us: int | None = Field(default=None, ge=0)
    source_duration_us: int | None = Field(default=None, gt=0)
    volume: float | None = Field(default=None, ge=0, le=4)
    fade_in_us: int | None = Field(default=None, ge=0)
    fade_out_us: int | None = Field(default=None, ge=0)
    loop: bool | None = None


class RemoveAudioSegment(EditCommand):
    type: Literal["remove_audio_segment"] = "remove_audio_segment"
    track_id: str
    segment_id: str


class SetTransition(EditCommand):
    type: Literal["set_transition"] = "set_transition"
    transition_id: str
    left_segment_id: str
    right_segment_id: str
    transition_type: Literal["dissolve"]
    duration_us: int = Field(gt=0)


class RemoveTransition(EditCommand):
    type: Literal["remove_transition"] = "remove_transition"
    transition_id: str


class UpdateTitle(EditCommand):
    type: Literal["update_title"] = "update_title"
    title: str = Field(min_length=1)


class UpdateGoal(EditCommand):
    type: Literal["update_goal"] = "update_goal"
    goal: str = Field(min_length=1)


DomainEditCommand = Annotated[
    InitializeEditingProject
    | RegisterSource
    | UpdateCanvas
    | AddTrack
    | RemoveTrack
    | RenameTrack
    | InsertSegment
    | RemoveSegment
    | MoveSegment
    | TrimSegment
    | SplitSegment
    | ReplaceSegmentMedia
    | SetSegmentTransform
    | UpdateTextSegment
    | AddAudioSegment
    | UpdateAudioSegment
    | RemoveAudioSegment
    | SetTransition
    | RemoveTransition
    | UpdateTitle
    | UpdateGoal,
    Field(discriminator="type"),
]


class EditCommandBatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    base_version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=1000)
    commands: list[DomainEditCommand] = Field(min_length=1, max_length=100)
