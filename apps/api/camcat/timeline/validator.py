from __future__ import annotations

import hashlib
import json
from typing import Any

from camcat.timeline.schemas import CompiledTimeline


class TimelineValidationError(ValueError):
    pass


def canonical_json(value: Any) -> bytes:
    value = _json_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def source_manifest_content(timeline_or_manifest: Any) -> list[dict[str, Any]]:
    manifest = getattr(timeline_or_manifest, "source_manifest", timeline_or_manifest)
    result: list[dict[str, Any]] = []
    for item in manifest:
        payload = _json_value(item)
        if not isinstance(payload, dict):
            raise TimelineValidationError("source manifest entry must be an object")
        payload.pop("local_path", None)
        result.append(payload)
    return result


def compiled_content(timeline: CompiledTimeline) -> dict[str, Any]:
    payload = timeline.model_dump(mode="json", by_alias=True)
    payload["compiled_hash"] = ""
    payload["source_manifest"] = source_manifest_content(timeline)
    return payload


def verify_compiled_timeline(timeline: CompiledTimeline) -> None:
    if timeline.schema_name != "camcat-compiled-timeline/v1":
        raise TimelineValidationError("unsupported compiled timeline schema")
    if not timeline.video_tracks or not timeline.video_tracks[0].segments:
        raise TimelineValidationError("compiled timeline requires a main video track")
    segments = timeline.video_tracks[0].segments
    cursor = 0
    for index, segment in enumerate(segments):
        overlap = segment.transition_in.duration_frames
        expected_start = cursor - overlap
        if segment.target_start_frame != expected_start:
            raise TimelineValidationError("video timeline has a gap or undeclared overlap")
        if segment.target_duration_frames <= overlap:
            raise TimelineValidationError("transition consumes an entire video segment")
        if (
            segment.transition_in.duration_frames + segment.transition_out.duration_frames
            >= segment.target_duration_frames
        ):
            raise TimelineValidationError("adjacent transitions consume an entire video segment")
        if index == 0 and segment.transition_in.type != "cut":
            raise TimelineValidationError("first segment cannot have an incoming transition")
        if index:
            previous = segments[index - 1]
            if previous.transition_out != segment.transition_in:
                raise TimelineValidationError("transition contract differs across a cut boundary")
        cursor = segment.target_start_frame + segment.target_duration_frames
    if segments[-1].transition_out.type != "cut":
        raise TimelineValidationError("last segment cannot have an outgoing transition")
    if cursor != timeline.frame_count:
        raise TimelineValidationError("frame count differs from the video timeline")
    expected_duration = round(
        timeline.frame_count * 1_000_000 * timeline.fps_den / timeline.fps_num
    )
    if timeline.duration_us != expected_duration:
        raise TimelineValidationError("duration is not aligned with frame count")
    for subtitle in timeline.subtitles:
        if not 0 <= subtitle.target_start_frame < subtitle.target_end_frame <= cursor:
            raise TimelineValidationError("subtitle bounds are outside the timeline")
    for track in timeline.audio_tracks:
        for cue in track.cues:
            if cue.target_start_frame + cue.target_duration_frames > cursor:
                raise TimelineValidationError("audio cue bounds are outside the timeline")
            if cue.fade_in_frames + cue.fade_out_frames > cue.target_duration_frames:
                raise TimelineValidationError("audio fades exceed cue duration")
    if content_hash(source_manifest_content(timeline)) != timeline.source_manifest_hash:
        raise TimelineValidationError("source manifest hash mismatch")
    if content_hash(compiled_content(timeline)) != timeline.compiled_hash:
        raise TimelineValidationError("compiled hash mismatch")
