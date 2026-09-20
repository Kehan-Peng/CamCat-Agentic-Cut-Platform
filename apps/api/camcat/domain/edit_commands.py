from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CommandConflict(ValueError):
    pass


class EditCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)

    @property
    def rebase_safe(self) -> bool:
        return False


class TrimClip(EditCommand):
    type: Literal["trim_clip"] = "trim_clip"
    clip_id: str
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> TrimClip:
        if self.source_end <= self.source_start:
            raise ValueError("trim range must have positive duration")
        return self

    @property
    def rebase_safe(self) -> bool:
        return True


class MoveClip(EditCommand):
    type: Literal["move_clip"] = "move_clip"
    clip_id: str
    before_clip_id: str | None = None
    after_clip_id: str | None = None

    @model_validator(mode="after")
    def exactly_one_anchor(self) -> MoveClip:
        if (self.before_clip_id is None) == (self.after_clip_id is None):
            raise ValueError("move clip needs exactly one before/after anchor")
        if self.clip_id in {self.before_clip_id, self.after_clip_id}:
            raise ValueError("move clip cannot anchor to itself")
        return self


class RemoveClip(EditCommand):
    type: Literal["remove_clip"] = "remove_clip"
    clip_id: str

    @property
    def rebase_safe(self) -> bool:
        return True


class SplitClip(EditCommand):
    type: Literal["split_clip"] = "split_clip"
    clip_id: str
    at_source: float = Field(gt=0)
    right_clip_id: str = Field(min_length=1)


class SetTransition(EditCommand):
    type: Literal["set_transition"] = "set_transition"
    clip_id: str
    transition_type: Literal["cut", "dissolve"]

    @property
    def rebase_safe(self) -> bool:
        return True


class InsertClip(EditCommand):
    type: Literal["insert_clip"] = "insert_clip"
    clip: dict[str, object]
    before_clip_id: str | None = None
    after_clip_id: str | None = None

    @model_validator(mode="after")
    def insertion_anchor(self) -> InsertClip:
        if self.before_clip_id is not None and self.after_clip_id is not None:
            raise ValueError("insert clip accepts at most one before/after anchor")
        return self


class ReplaceClipMedia(EditCommand):
    type: Literal["replace_clip_media"] = "replace_clip_media"
    clip_id: str
    source_id: str
    storage_key: str
    segment_id: str
    origin: Literal["source", "library"]
    source_start: float = Field(ge=0)
    source_end: float = Field(gt=0)

    @property
    def rebase_safe(self) -> bool:
        return True


class AddSubtitle(EditCommand):
    type: Literal["add_subtitle"] = "add_subtitle"
    subtitle: dict[str, object]


class UpdateSubtitle(EditCommand):
    type: Literal["update_subtitle"] = "update_subtitle"
    subtitle_id: str
    text: str = Field(min_length=1)

    @property
    def rebase_safe(self) -> bool:
        return True


class RemoveSubtitle(EditCommand):
    type: Literal["remove_subtitle"] = "remove_subtitle"
    subtitle_id: str

    @property
    def rebase_safe(self) -> bool:
        return True


class AddAudioCue(EditCommand):
    type: Literal["add_audio_cue"] = "add_audio_cue"
    kind: Literal["bgm", "ambient", "sound_effects"]
    cue: dict[str, object]


class RemoveAudioCue(EditCommand):
    type: Literal["remove_audio_cue"] = "remove_audio_cue"
    cue_id: str

    @property
    def rebase_safe(self) -> bool:
        return True


class ReplaceClipPlan(EditCommand):
    type: Literal["replace_clip_plan"] = "replace_clip_plan"
    clips: list[dict[str, object]] = Field(min_length=1)


class ReplaceSubtitles(EditCommand):
    type: Literal["replace_subtitles"] = "replace_subtitles"
    subtitles: list[dict[str, object]]


class ReplaceAudioPlan(EditCommand):
    type: Literal["replace_audio_plan"] = "replace_audio_plan"
    audio_plan: dict[str, object]


class SetOutputSettings(EditCommand):
    type: Literal["set_output_settings"] = "set_output_settings"
    aspect_ratio: Literal["16:9", "9:16", "3:4", "4:3", "1:1"]
    external_material_ratio_limit: float = Field(ge=0, le=0.75)


class SetSpeechEdit(EditCommand):
    type: Literal["set_speech_edit"] = "set_speech_edit"
    speech_edit: dict[str, object]


class UpdateTitle(EditCommand):
    type: Literal["update_title"] = "update_title"
    title: str = Field(min_length=1)

    @property
    def rebase_safe(self) -> bool:
        return True


DomainEditCommand = Annotated[
    TrimClip
    | MoveClip
    | RemoveClip
    | SplitClip
    | SetTransition
    | InsertClip
    | ReplaceClipMedia
    | AddSubtitle
    | UpdateSubtitle
    | RemoveSubtitle
    | AddAudioCue
    | RemoveAudioCue
    | ReplaceClipPlan
    | ReplaceSubtitles
    | ReplaceAudioPlan
    | SetOutputSettings
    | SetSpeechEdit
    | UpdateTitle,
    Field(discriminator="type"),
]


def command_to_patch(
    document: dict[str, object], command: DomainEditCommand
) -> list[dict[str, object]]:
    if isinstance(command, ReplaceClipPlan):
        clips = deepcopy(command.clips)
        clip_ids = [str(item.get("clip_id", "")) for item in clips]
        if any(not item for item in clip_ids) or len(clip_ids) != len(set(clip_ids)):
            raise CommandConflict("replacement clip plan requires unique stable clip_id values")
        return [{"op": _root_operation(document, "clips"), "path": "/clips", "value": clips}]
    if isinstance(command, ReplaceSubtitles):
        subtitles = deepcopy(command.subtitles)
        subtitle_ids = [str(item.get("subtitle_id", "")) for item in subtitles]
        if any(not item for item in subtitle_ids) or len(subtitle_ids) != len(set(subtitle_ids)):
            raise CommandConflict("replacement subtitles require unique stable subtitle_id values")
        return [
            {
                "op": _root_operation(document, "subtitles"),
                "path": "/subtitles",
                "value": subtitles,
            }
        ]
    if isinstance(command, ReplaceAudioPlan):
        return [
            {
                "op": _root_operation(document, "audio_plan"),
                "path": "/audio_plan",
                "value": deepcopy(command.audio_plan),
            }
        ]
    if isinstance(command, SetOutputSettings):
        settings = deepcopy(document.get("settings", {}))
        if not isinstance(settings, dict):
            raise CommandConflict("output settings state is invalid")
        settings.update(
            {
                "aspect_ratio": command.aspect_ratio,
                "external_material_ratio_limit": command.external_material_ratio_limit,
            }
        )
        return [
            {
                "op": _root_operation(document, "settings"),
                "path": "/settings",
                "value": settings,
            }
        ]
    if isinstance(command, SetSpeechEdit):
        return [
            {
                "op": _root_operation(document, "speech_edit"),
                "path": "/speech_edit",
                "value": deepcopy(command.speech_edit),
            }
        ]
    if isinstance(command, UpdateTitle):
        return [
            {
                "op": _root_operation(document, "title"),
                "path": "/title",
                "value": command.title.strip(),
            }
        ]
    if isinstance(command, (AddSubtitle, UpdateSubtitle, RemoveSubtitle)):
        return _subtitle_command(document, command)
    if isinstance(command, (AddAudioCue, RemoveAudioCue)):
        return _audio_command(document, command)
    clips_value = document.get("clips", [])
    if not isinstance(clips_value, list):
        raise CommandConflict("clips state is invalid")
    clips = deepcopy(clips_value)
    if isinstance(command, InsertClip):
        inserted = deepcopy(command.clip)
        clip_id = str(inserted.get("clip_id", ""))
        if not clip_id or _clip_index(clips, clip_id) is not None:
            raise CommandConflict("inserted clip requires a new stable clip_id")
        anchor_id = command.before_clip_id or command.after_clip_id
        if anchor_id is None:
            clips.append(inserted)
        else:
            anchor_index = _clip_index(clips, anchor_id)
            if anchor_index is None:
                raise CommandConflict(f"insert anchor clip is missing: {anchor_id}")
            clips.insert(anchor_index + (1 if command.after_clip_id else 0), inserted)
        return [{"op": "replace", "path": "/clips", "value": clips}]
    index = _clip_index(clips, command.clip_id)
    if index is None:
        raise CommandConflict(f"clip is missing: {command.clip_id}")
    if isinstance(command, TrimClip):
        clips[index]["source_start"] = command.source_start
        clips[index]["source_end"] = command.source_end
    elif isinstance(command, MoveClip):
        moving = clips.pop(index)
        anchor_id = command.before_clip_id or command.after_clip_id
        anchor_index = _clip_index(clips, str(anchor_id))
        if anchor_index is None:
            label = "before" if command.before_clip_id else "after"
            raise CommandConflict(f"{label} clip is missing: {anchor_id}")
        clips.insert(anchor_index + (1 if command.after_clip_id else 0), moving)
    elif isinstance(command, RemoveClip):
        if len(clips) == 1:
            raise CommandConflict("cannot remove the final video clip")
        clips.pop(index)
    elif isinstance(command, SplitClip):
        current = clips[index]
        start = float(str(current.get("source_start", 0)))
        end = float(str(current.get("source_end", 0)))
        if not start < command.at_source < end:
            raise CommandConflict("split point must be inside the clip source range")
        if _clip_index(clips, command.right_clip_id) is not None:
            raise CommandConflict(f"split clip id already exists: {command.right_clip_id}")
        right = deepcopy(current)
        current["source_end"] = command.at_source
        right["clip_id"] = command.right_clip_id
        right["source_start"] = command.at_source
        clips.insert(index + 1, right)
    elif isinstance(command, SetTransition):
        clips[index]["transition"] = command.transition_type
    elif isinstance(command, ReplaceClipMedia):
        if command.source_end <= command.source_start:
            raise CommandConflict("replacement source range must have positive duration")
        clips[index].update(
            {
                "media_id": command.source_id,
                "storage_key": command.storage_key,
                "segment_id": command.segment_id,
                "origin": command.origin,
                "source_start": command.source_start,
                "source_end": command.source_end,
            }
        )
    return [{"op": "replace", "path": "/clips", "value": clips}]


def _clip_index(clips: list[dict[str, object]], clip_id: str) -> int | None:
    matches = [index for index, item in enumerate(clips) if item.get("clip_id") == clip_id]
    if len(matches) > 1:
        raise CommandConflict(f"clip id is not unique: {clip_id}")
    return matches[0] if matches else None


def _subtitle_command(
    document: dict[str, object], command: AddSubtitle | UpdateSubtitle | RemoveSubtitle
) -> list[dict[str, object]]:
    raw = document.get("subtitles", [])
    if not isinstance(raw, list):
        raise CommandConflict("subtitle state is invalid")
    subtitles = deepcopy(raw)
    if isinstance(command, AddSubtitle):
        subtitle = deepcopy(command.subtitle)
        subtitle_id = str(subtitle.get("subtitle_id", ""))
        if not subtitle_id or any(item.get("subtitle_id") == subtitle_id for item in subtitles):
            raise CommandConflict("subtitle requires a new stable subtitle_id")
        subtitles.append(subtitle)
    else:
        matches = [
            index
            for index, item in enumerate(subtitles)
            if item.get("subtitle_id") == command.subtitle_id
        ]
        if len(matches) != 1:
            raise CommandConflict(f"subtitle is missing or ambiguous: {command.subtitle_id}")
        if isinstance(command, UpdateSubtitle):
            subtitles[matches[0]]["text"] = command.text
        else:
            subtitles.pop(matches[0])
    return [{"op": "replace", "path": "/subtitles", "value": subtitles}]


def _audio_command(
    document: dict[str, object], command: AddAudioCue | RemoveAudioCue
) -> list[dict[str, object]]:
    raw = document.get("audio_plan", {})
    if not isinstance(raw, dict):
        raise CommandConflict("audio plan state is invalid")
    audio_plan = deepcopy(raw)
    keys = ("bgm", "ambient", "sound_effects")
    if isinstance(command, AddAudioCue):
        cue = deepcopy(command.cue)
        cue_id = str(cue.get("cue_id", ""))
        existing = [
            item for key in keys for item in audio_plan.get(key, []) if item.get("cue_id") == cue_id
        ]
        if not cue_id or existing:
            raise CommandConflict("audio cue requires a new stable cue_id")
        audio_plan.setdefault(command.kind, []).append(cue)
    else:
        matches = [
            (key, index)
            for key in keys
            for index, item in enumerate(audio_plan.get(key, []))
            if item.get("cue_id") == command.cue_id
        ]
        if len(matches) != 1:
            raise CommandConflict(f"audio cue is missing or ambiguous: {command.cue_id}")
        key, index = matches[0]
        audio_plan[key].pop(index)
    return [{"op": "replace", "path": "/audio_plan", "value": audio_plan}]


def commands_to_patch(
    document: dict[str, object], commands: list[DomainEditCommand]
) -> list[dict[str, object]]:
    if not commands:
        raise CommandConflict("at least one domain edit command is required")
    working = deepcopy(document)
    final_by_path: dict[str, dict[str, object]] = {}
    path_order: list[str] = []
    for command in commands:
        for operation in command_to_patch(working, command):
            path = str(operation["path"])
            root = path.removeprefix("/")
            if "/" in root or operation["op"] == "remove":
                raise CommandConflict("domain command reducer only emits root state patches")
            working[root] = deepcopy(operation.get("value"))
            if path not in final_by_path:
                path_order.append(path)
            final_by_path[path] = {
                "op": _root_operation(document, root),
                "path": path,
                "value": deepcopy(operation.get("value")),
            }
    return [final_by_path[path] for path in path_order]


def _root_operation(document: dict[str, object], key: str) -> Literal["add", "replace"]:
    return "replace" if key in document else "add"
