from typing import Any

from backend.app.domain.models import MediaSegment


def segment_matches_filters(segment: MediaSegment, filters: dict[str, Any]) -> bool:
    if not filters:
        return True

    video_id = filters.get("video_id")
    if video_id and segment.video_id != video_id:
        return False

    tags = filters.get("tags")
    if tags:
        required_tags = {str(tag) for tag in _as_list(tags)}
        if not required_tags.issubset(set(segment.tags)):
            return False

    min_highlight_score = filters.get("min_highlight_score")
    if min_highlight_score is not None and segment.highlight_score < float(min_highlight_score):
        return False

    min_motion_score = filters.get("min_motion_score")
    if min_motion_score is not None and segment.motion_score < float(min_motion_score):
        return False

    return True


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple | set):
        return list(value)
    return [value]
