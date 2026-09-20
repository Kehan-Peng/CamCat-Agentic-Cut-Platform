from __future__ import annotations

import hashlib
import json
from typing import Any

from camcat.timeline.frames import frame_to_us
from camcat.timeline.schemas import CompiledTimelineV2


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
        if "local_path" in payload:
            raise TimelineValidationError("persistent source manifest cannot contain local_path")
        result.append(payload)
    return result


def compiled_content(timeline: CompiledTimelineV2) -> dict[str, Any]:
    payload = timeline.model_dump(mode="json", by_alias=True)
    payload["compiled_hash"] = ""
    return payload


def verify_compiled_timeline(timeline: CompiledTimelineV2) -> None:
    if timeline.schema_name != "camcat-compiled-timeline/v2":
        raise TimelineValidationError("unsupported compiled timeline schema")
    if not timeline.video_tracks or not timeline.video_tracks[0].segments:
        raise TimelineValidationError("compiled timeline requires a primary video track")
    primary = timeline.video_tracks[0]
    cursor = 0
    for segment in primary.segments:
        if segment.timeline_start_frame != cursor:
            raise TimelineValidationError("primary video track must be continuous")
        cursor += segment.timeline_duration_frames
    if cursor != timeline.frame_count:
        raise TimelineValidationError("semantic frame count differs from primary video track")
    by_track = {track.track_id: track for track in timeline.video_tracks}
    for edge in timeline.transitions:
        track = by_track.get(edge.track_id)
        if track is None:
            raise TimelineValidationError("transition references a missing track")
        ids = [item.segment_id for item in track.segments]
        try:
            left_index = ids.index(edge.left_segment_id)
        except ValueError as exc:
            raise TimelineValidationError("transition references a missing segment") from exc
        if left_index + 1 >= len(ids) or ids[left_index + 1] != edge.right_segment_id:
            raise TimelineValidationError("transition references nonadjacent segments")
        left, right = track.segments[left_index : left_index + 2]
        if edge.duration_frames >= min(
            left.timeline_duration_frames, right.timeline_duration_frames
        ):
            raise TimelineValidationError("transition consumes an adjacent segment")
        if right.timeline_start_frame != left.timeline_start_frame + left.timeline_duration_frames:
            raise TimelineValidationError("transition cannot bridge a semantic gap")
    expected_duration = frame_to_us(
        timeline.frame_count, timeline.canvas.fps_num, timeline.canvas.fps_den
    )
    if timeline.duration_us != expected_duration:
        raise TimelineValidationError("duration is not aligned with frame count")
    for video_track in timeline.video_tracks:
        previous_end = 0
        for segment in video_track.segments:
            if segment.timeline_start_frame < previous_end:
                raise TimelineValidationError("video track contains semantic overlap")
            if segment.render_start_frame < 0:
                raise TimelineValidationError("video render range begins before frame zero")
            previous_end = segment.timeline_start_frame + segment.timeline_duration_frames
    for text_track in timeline.text_tracks:
        for text_segment in text_track.segments:
            if text_segment.start_frame + text_segment.duration_frames > timeline.frame_count:
                raise TimelineValidationError("text segment exceeds timeline")
    for audio_track in timeline.audio_tracks:
        for audio_segment in audio_track.segments:
            if (
                audio_segment.timeline_start_frame + audio_segment.timeline_duration_frames
                > timeline.frame_count
            ):
                raise TimelineValidationError("audio segment exceeds timeline")
            if (
                audio_segment.fade_in_frames + audio_segment.fade_out_frames
                > audio_segment.timeline_duration_frames
            ):
                raise TimelineValidationError("audio fades exceed segment duration")
    if content_hash(source_manifest_content(timeline)) != timeline.source_manifest_hash:
        raise TimelineValidationError("source manifest hash mismatch")
    if content_hash(compiled_content(timeline)) != timeline.compiled_hash:
        raise TimelineValidationError("compiled hash mismatch")
