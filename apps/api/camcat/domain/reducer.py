from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, cast, overload

import jsonpatch

from camcat.domain.commands import (
    AddAudioSegment,
    AddTrack,
    DomainEditCommand,
    InitializeEditingProject,
    InsertSegment,
    MoveSegment,
    RegisterSource,
    RemoveAudioSegment,
    RemoveSegment,
    RemoveTrack,
    RemoveTransition,
    RenameTrack,
    ReplaceSegmentMedia,
    SetSegmentTransform,
    SetTransition,
    SplitSegment,
    TrimSegment,
    UpdateAudioSegment,
    UpdateCanvas,
    UpdateGoal,
    UpdateTextSegment,
    UpdateTitle,
)
from camcat.domain.project import (
    EditingProjectV2,
    Transform,
    TransitionEdge,
)


class CommandConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReductionResult:
    project: EditingProjectV2
    operations: list[dict[str, Any]]


def reduce_commands(
    current: EditingProjectV2 | None, commands: list[DomainEditCommand]
) -> ReductionResult:
    if not commands:
        raise CommandConflict("at least one domain edit command is required")
    if current is None:
        if len(commands) != 1 or not isinstance(commands[0], InitializeEditingProject):
            raise CommandConflict("an uninitialized project requires InitializeEditingProject")
        project = commands[0].project
        return ReductionResult(
            project=project, operations=[{"op": "add", "path": "", "value": _dump(project)}]
        )
    if any(isinstance(item, InitializeEditingProject) for item in commands):
        raise CommandConflict("InitializeEditingProject is only valid once")
    before = _dump(current)
    working = deepcopy(before)
    for command in commands:
        _apply(working, command)
        working = _dump(EditingProjectV2.model_validate(working))
    project = EditingProjectV2.model_validate(working)
    operations = cast(list[dict[str, Any]], jsonpatch.JsonPatch.from_diff(before, working).patch)
    if not operations:
        raise CommandConflict("commands did not change the project")
    return ReductionResult(project=project, operations=operations)


def _apply(document: dict[str, Any], command: DomainEditCommand) -> None:
    tracks = cast(list[dict[str, Any]], document["timeline"]["tracks"])
    transitions = cast(list[dict[str, Any]], document["timeline"]["transitions"])
    if isinstance(command, UpdateTitle):
        document["title"] = command.title.strip()
        return
    if isinstance(command, UpdateGoal):
        document["goal"] = command.goal.strip()
        return
    if isinstance(command, RegisterSource):
        sources = cast(list[dict[str, Any]], document["sources"])
        payload = command.source.model_dump(mode="json")
        existing = [item for item in sources if item["source_id"] == command.source.source_id]
        if existing:
            if existing[0] != payload:
                raise CommandConflict(
                    f"source identity already has different metadata: {command.source.source_id}"
                )
            return
        sources.append(payload)
        sources.sort(key=lambda item: item["source_id"])
        return
    if isinstance(command, UpdateCanvas):
        document["canvas"] = command.canvas.model_dump(mode="json")
        return
    if isinstance(command, AddTrack):
        if _track(tracks, command.track.track_id, required=False) is not None:
            raise CommandConflict(f"track already exists: {command.track.track_id}")
        index = _anchor_index(
            tracks,
            key="track_id",
            before=command.before_track_id,
            after=command.after_track_id,
        )
        tracks.insert(index, command.track.model_dump(mode="json"))
        return
    if isinstance(command, RemoveTrack):
        track = _track(tracks, command.track_id)
        ids = {item["segment_id"] for item in track["segments"]}
        if any(
            edge["left_segment_id"] in ids or edge["right_segment_id"] in ids
            for edge in transitions
        ):
            raise CommandConflict("remove transition edges before removing their track")
        tracks.remove(track)
        return
    if isinstance(command, RenameTrack):
        _track(tracks, command.track_id)["name"] = command.name.strip()
        return
    if isinstance(command, SetTransition):
        if any(item["transition_id"] == command.transition_id for item in transitions):
            transitions[:] = [
                item for item in transitions if item["transition_id"] != command.transition_id
            ]
        transitions.append(
            TransitionEdge(
                transition_id=command.transition_id,
                left_segment_id=command.left_segment_id,
                right_segment_id=command.right_segment_id,
                type=command.transition_type,
                duration_us=command.duration_us,
            ).model_dump(mode="json")
        )
        return
    if isinstance(command, RemoveTransition):
        matched = [item for item in transitions if item["transition_id"] == command.transition_id]
        if len(matched) != 1:
            raise CommandConflict(f"transition is missing or ambiguous: {command.transition_id}")
        transitions.remove(matched[0])
        return
    if isinstance(command, AddAudioSegment):
        track = _track(tracks, command.track_id)
        if track["type"] != "audio":
            raise CommandConflict("AddAudioSegment requires an audio track")
        _ensure_new_segment(tracks, command.segment.segment_id)
        track["segments"].append(command.segment.model_dump(mode="json"))
        track["segments"].sort(key=lambda item: item["timeline_start_us"])
        return
    if isinstance(command, RemoveAudioSegment):
        track = _track(tracks, command.track_id)
        if track["type"] != "audio":
            raise CommandConflict("RemoveAudioSegment requires an audio track")
        segment = _segment_in_track(track, command.segment_id)
        track["segments"].remove(segment)
        return
    if isinstance(command, InsertSegment):
        track = _track(tracks, command.track_id)
        if track["type"] != command.segment.type:
            raise CommandConflict("segment type must match its track")
        _ensure_new_segment(tracks, command.segment.segment_id)
        index = _anchor_index(
            track["segments"],
            key="segment_id",
            before=command.before_segment_id,
            after=command.after_segment_id,
        )
        track["segments"].insert(index, command.segment.model_dump(mode="json"))
        _reflow_primary_video(tracks, track)
        return
    if isinstance(command, MoveSegment):
        track = _track(tracks, command.track_id)
        segment = _segment_in_track(track, command.segment_id)
        track["segments"].remove(segment)
        index = _anchor_index(
            track["segments"],
            key="segment_id",
            before=command.before_segment_id,
            after=command.after_segment_id,
        )
        track["segments"].insert(index, segment)
        _reflow_primary_video(tracks, track)
        return
    if isinstance(command, RemoveSegment):
        track = _track(tracks, command.track_id)
        segment = _segment_in_track(track, command.segment_id)
        _require_no_transition(transitions, command.segment_id)
        track["segments"].remove(segment)
        _reflow_primary_video(tracks, track)
        return

    if isinstance(command, InitializeEditingProject):
        raise CommandConflict("InitializeEditingProject is only valid once")
    track, segment = _segment(tracks, command.segment_id)
    if isinstance(command, TrimSegment):
        if segment["type"] not in {"video", "audio"}:
            raise CommandConflict("only media segments can be trimmed")
        segment["source_start_us"] = command.source_start_us
        segment["source_duration_us"] = command.source_duration_us
        if segment["type"] == "video":
            segment["timeline_duration_us"] = round(command.source_duration_us / segment["speed"])
        elif not segment["loop"]:
            segment["timeline_duration_us"] = min(
                segment["timeline_duration_us"], command.source_duration_us
            )
        _reflow_primary_video(tracks, track)
    elif isinstance(command, SplitSegment):
        if segment["type"] != "video":
            raise CommandConflict("SplitSegment currently supports video segments")
        _require_no_transition(transitions, command.segment_id)
        if any(
            item["segment_id"] == command.segment_id
            for item in document.get("speech_review", {}).get("items", [])
        ):
            raise CommandConflict("split with speech evidence requires explicit evidence remapping")
        start = int(segment["source_start_us"])
        end = start + int(segment["source_duration_us"])
        if not start < command.at_source_us < end:
            raise CommandConflict("split point must be inside the source range")
        _ensure_new_segment(tracks, command.right_segment_id)
        right = deepcopy(segment)
        right["segment_id"] = command.right_segment_id
        left_source_duration = command.at_source_us - start
        right_source_duration = end - command.at_source_us
        segment["source_duration_us"] = left_source_duration
        segment["timeline_duration_us"] = round(left_source_duration / segment["speed"])
        right["source_start_us"] = command.at_source_us
        right["source_duration_us"] = right_source_duration
        right["timeline_duration_us"] = round(right_source_duration / right["speed"])
        index = track["segments"].index(segment)
        track["segments"].insert(index + 1, right)
        _reflow_primary_video(tracks, track)
    elif isinstance(command, ReplaceSegmentMedia):
        if segment["type"] not in {"video", "audio"}:
            raise CommandConflict("text segments have no media source")
        segment.update(
            source_id=command.source_id,
            source_start_us=command.source_start_us,
            source_duration_us=command.source_duration_us,
        )
        if segment["type"] == "video":
            segment["timeline_duration_us"] = round(command.source_duration_us / segment["speed"])
            _reflow_primary_video(tracks, track)
    elif isinstance(command, SetSegmentTransform):
        if segment["type"] != "video":
            raise CommandConflict("only video segments have transforms")
        segment["transform"] = Transform(
            x=command.x,
            y=command.y,
            scale_x=command.scale_x,
            scale_y=command.scale_y,
            rotation=command.rotation,
            opacity=command.opacity,
        ).model_dump(mode="json")
    elif isinstance(command, UpdateTextSegment):
        if segment["type"] != "text":
            raise CommandConflict("UpdateTextSegment requires a text segment")
        for field in ("text", "start_us", "duration_us"):
            value = getattr(command, field)
            if value is not None:
                segment[field] = value
        style = dict(segment["style"])
        for field in (
            "font_family",
            "local_font_ref",
            "size",
            "x",
            "y",
            "color",
            "border_color",
            "border_width",
        ):
            value = getattr(command, field)
            if value is not None:
                style[field] = value
        segment["style"] = style
        track["segments"].sort(key=lambda item: item["start_us"])
    elif isinstance(command, UpdateAudioSegment):
        if segment["type"] != "audio":
            raise CommandConflict("UpdateAudioSegment requires an audio segment")
        for field in (
            "timeline_start_us",
            "timeline_duration_us",
            "source_start_us",
            "source_duration_us",
            "volume",
            "fade_in_us",
            "fade_out_us",
            "loop",
        ):
            value = getattr(command, field)
            if value is not None:
                segment[field] = value
        track["segments"].sort(key=lambda item: item["timeline_start_us"])
    else:
        raise CommandConflict(f"unsupported domain command: {command.type}")


def _dump(project: EditingProjectV2) -> dict[str, Any]:
    return project.model_dump(mode="json", by_alias=True)


@overload
def _track(
    tracks: list[dict[str, Any]], track_id: str, *, required: Literal[True] = True
) -> dict[str, Any]: ...


@overload
def _track(
    tracks: list[dict[str, Any]], track_id: str, *, required: Literal[False]
) -> dict[str, Any] | None: ...


def _track(
    tracks: list[dict[str, Any]], track_id: str, *, required: bool = True
) -> dict[str, Any] | None:
    matches = [item for item in tracks if item["track_id"] == track_id]
    if len(matches) != 1:
        if not required and not matches:
            return None
        raise CommandConflict(f"track is missing or ambiguous: {track_id}")
    return matches[0]


def _segment(
    tracks: list[dict[str, Any]], segment_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    matches = [
        (track, item)
        for track in tracks
        for item in track["segments"]
        if item["segment_id"] == segment_id
    ]
    if len(matches) != 1:
        raise CommandConflict(f"segment is missing or ambiguous: {segment_id}")
    return matches[0]


def _segment_in_track(track: dict[str, Any], segment_id: str) -> dict[str, Any]:
    matches = [item for item in track["segments"] if item["segment_id"] == segment_id]
    if len(matches) != 1:
        raise CommandConflict(f"segment is missing or ambiguous on track: {segment_id}")
    return cast(dict[str, Any], matches[0])


def _ensure_new_segment(tracks: list[dict[str, Any]], segment_id: str) -> None:
    if any(item["segment_id"] == segment_id for track in tracks for item in track["segments"]):
        raise CommandConflict(f"segment already exists: {segment_id}")


def _anchor_index(
    items: list[dict[str, Any]],
    *,
    key: str,
    before: str | None,
    after: str | None,
) -> int:
    anchor = before or after
    if anchor is None:
        return len(items)
    matches = [index for index, item in enumerate(items) if item[key] == anchor]
    if len(matches) != 1:
        raise CommandConflict(f"stable anchor is missing or ambiguous: {anchor}")
    return matches[0] + (1 if after is not None else 0)


def _require_no_transition(transitions: list[dict[str, Any]], segment_id: str) -> None:
    if any(
        item["left_segment_id"] == segment_id or item["right_segment_id"] == segment_id
        for item in transitions
    ):
        raise CommandConflict("segment has a transition; remove it before this mutation")


def _reflow_primary_video(tracks: list[dict[str, Any]], track: dict[str, Any]) -> None:
    first_video = next((item for item in tracks if item["type"] == "video"), None)
    if track is not first_video:
        return
    cursor = 0
    for segment in track["segments"]:
        segment["timeline_start_us"] = cursor
        cursor += int(segment["timeline_duration_us"])
