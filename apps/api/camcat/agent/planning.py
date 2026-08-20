from __future__ import annotations

import math
from typing import Any


def validate_plan(result: dict[str, Any], candidates: dict[str, Any]) -> None:
    """Reject unsupported selections before creating a timeline or writing state."""
    clips = result.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ValueError("clips must be a nonempty list")
    for index, clip in enumerate(clips):
        if not isinstance(clip, dict):
            raise ValueError("each clip must be an object")
        if "output_start" in clip or "output_end" in clip or "duration_frames" in clip:
            raise ValueError("edit-plan model must not return physical timeline coordinates")
        source = candidates.get(str(clip.get("segment_id", "")))
        if source is None:
            raise ValueError("select segment_id only from the supplied materials")
        try:
            start = float(clip.get("source_start", source["start_time"]))
            end = float(clip.get("source_end", source["end_time"]))
        except (TypeError, ValueError) as exc:
            raise ValueError("source times must be numeric seconds") from exc
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError("source times must be finite")
        if start < source["start_time"] or end > source["end_time"] or end <= start:
            raise ValueError("source range must be positive and within the selected material")
        transition = clip.get("transition", "cut")
        if not isinstance(transition, str) or transition not in {"cut", "dissolve"}:
            raise ValueError("transition intent must be cut or dissolve")
        if index == len(clips) - 1 and transition != "cut":
            raise ValueError("final clip cannot have an outgoing transition")
