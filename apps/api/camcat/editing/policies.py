from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

SUPPORTED_RATIOS = ("16:9", "9:16", "3:4", "4:3", "1:1")
RATIO_RESOLUTIONS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "3:4": (1080, 1440),
    "4:3": (1440, 1080),
    "1:1": (1080, 1080),
}


def expiry_for_upload(created_at: datetime) -> datetime:
    return created_at + timedelta(hours=4)


def choose_aspect_ratio(instruction: str, width: int, height: int) -> str:
    normalized = instruction.lower().replace("：", ":")
    for ratio in SUPPORTED_RATIOS:
        if ratio in normalized:
            return ratio
    if re.search(r"tiktok|抖音|reels?|shorts?|竖屏|手机全屏", normalized):
        return "9:16"
    if re.search(r"小红书|rednote", normalized):
        return "3:4"
    if re.search(r"方形|square", normalized):
        return "1:1"
    if width <= 0 or height <= 0:
        return "16:9"
    source = width / height
    return min(
        SUPPORTED_RATIOS,
        key=lambda value: abs(source - _ratio_value(value)),
    )


def resolution_for_ratio(ratio: str) -> tuple[int, int]:
    try:
        return RATIO_RESOLUTIONS[ratio]
    except KeyError as exc:
        raise ValueError(f"unsupported aspect ratio: {ratio}") from exc


def prepare_source_candidates(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the strongest representative of repeated shots without reshuffling the story."""
    items = [dict(item) for item in candidates]
    best_for_signature: dict[str, int] = {}
    for index, item in enumerate(items):
        signature = str(item.get("shot_signature") or item.get("segment_id") or index)
        incumbent_index = best_for_signature.get(signature)
        if incumbent_index is None or float(item.get("quality_score", 0)) > float(
            items[incumbent_index].get("quality_score", 0)
        ):
            best_for_signature[signature] = index
    selected = set(best_for_signature.values())
    return [item for index, item in enumerate(items) if index in selected]


def enforce_timeline_policy(
    proposed: Iterable[dict[str, Any]], *, external_ratio_limit: float = 0.25
) -> list[dict[str, Any]]:
    """Make user footage primary and deterministically bound supplemental library footage."""
    limit = min(0.75, max(0.0, float(external_ratio_limit)))
    raw = [dict(item) for item in proposed]
    source = [item for item in raw if item.get("origin", "source") == "source"]
    library = [item for item in raw if item.get("origin") == "library"]
    if not source:
        raise ValueError("editing plan must contain user source footage")

    source_duration = sum(_duration(item) for item in source)
    # external / (source + external) <= limit
    budget = source_duration * limit / (1.0 - limit) if limit < 1 else source_duration
    accepted_library: list[dict[str, Any]] = []
    remaining = budget
    for item in library:
        duration = _duration(item)
        if remaining <= 0:
            break
        if duration > remaining:
            item["source_end"] = float(item["source_start"]) + remaining
            duration = remaining
        if duration > 0.1:
            accepted_library.append(item)
            remaining -= duration

    # Preserve proposed relative order, but never open on stock when source footage exists.
    library_keys = {
        (
            str(item.get("segment_id")),
            float(item.get("source_start", 0)),
            float(item.get("source_end", 0)),
        )
        for item in accepted_library
    }
    ordered = []
    first_source = source[0]
    ordered.append(first_source)
    for item in raw:
        if item is first_source:
            continue
        if (
            item.get("origin", "source") == "source"
            or (
                str(item.get("segment_id")),
                float(item.get("source_start", 0)),
                float(item.get("source_end", 0)),
            )
            in library_keys
        ):
            ordered.append(item)

    cursor = 0.0
    result: list[dict[str, Any]] = []
    for index, item in enumerate(ordered):
        duration = _duration(item)
        if duration <= 0:
            continue
        item["clip_id"] = str(item.get("clip_id") or f"clip-{index + 1}")
        item["output_start"] = cursor
        item["output_end"] = cursor + duration
        cursor += duration
        result.append(item)
    return result


def explicit_external_ratio(instruction: str) -> float:
    normalized = instruction.lower()
    match = re.search(r"(?:外部|素材库|stock)[^%]{0,12}(\d{1,2})\s*%", normalized)
    if match:
        return min(0.75, max(0.0, int(match.group(1)) / 100))
    if re.search(r"全部使用外部|主要使用素材库|stock[- ]?only", normalized):
        return 0.75
    return 0.25


def _duration(item: dict[str, Any]) -> float:
    return max(0.0, float(item.get("source_end", 0)) - float(item.get("source_start", 0)))


def _ratio_value(ratio: str) -> float:
    left, right = ratio.split(":", 1)
    return int(left) / int(right)
